"""Unit tests for `web.routers.app_update` — the git-pull self-update REST
surface, via `TestClient`. `check_for_update`/`pull_update` are
monkeypatched (no real git); `web.supervised_restart`'s real `SIGTERM` and
grace-sleep are monkeypatched too — no test here ever sends a real signal
to itself or waits a real second."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from web import supervised_restart
from web.app import create_app
from web.routers import app_update as app_update_router

_PENDING = {"current_commit": "aaaaaaaa", "latest_commit": "bbbbbbbb", "commits_behind": 1, "log": "bbbbbbb x"}

restart_calls: list = []


async def _immediate():
    return None


@pytest.fixture(autouse=True)
def _no_real_restart(monkeypatch):
    """Applies to every test in this file — a real SIGTERM or a real 1s
    sleep must never happen just because a router test exercised the
    supervised branch."""
    monkeypatch.setattr(supervised_restart.asyncio, "sleep", lambda *_a, **_k: _immediate())
    monkeypatch.setattr(supervised_restart, "_real_restart", lambda: restart_calls.append(1))


@pytest.fixture(autouse=True)
def _reset_restart_calls():
    restart_calls.clear()
    yield
    restart_calls.clear()


# --------------------------------------------------------------------- #
# /status
# --------------------------------------------------------------------- #


def test_status_starts_with_nothing_pending(make_config):
    app = create_app(make_config())
    client = TestClient(app)
    r = client.get("/api/app-update/status")
    assert r.status_code == 200
    assert r.json() == {"pending": None, "available": True}


# --------------------------------------------------------------------- #
# /check
# --------------------------------------------------------------------- #


def test_check_with_no_update_available_reports_nothing_pending(make_config, monkeypatch):
    app = create_app(make_config())
    client = TestClient(app)
    monkeypatch.setattr(app_update_router, "check_for_update", lambda repo_root: None)
    r = client.post("/api/app-update/check")
    assert r.status_code == 200
    assert r.json() == {"pending": None}


def test_check_with_an_update_available_sets_pending_state(make_config, monkeypatch):
    app = create_app(make_config())
    client = TestClient(app)
    monkeypatch.setattr(app_update_router, "check_for_update", lambda repo_root: _PENDING)
    r = client.post("/api/app-update/check")
    assert r.status_code == 200
    assert r.json() == {"pending": _PENDING}

    status = client.get("/api/app-update/status").json()
    assert status["pending"] == _PENDING


def test_check_failure_is_a_typed_502_not_a_500(make_config, monkeypatch):
    app = create_app(make_config())
    client = TestClient(app)

    def boom(repo_root):
        raise RuntimeError("fatal: unable to access origin")

    monkeypatch.setattr(app_update_router, "check_for_update", boom)
    r = client.post("/api/app-update/check")
    assert r.status_code == 502
    assert "unable to access origin" in r.json()["detail"]


# --------------------------------------------------------------------- #
# /pull
# --------------------------------------------------------------------- #


def test_pull_without_a_prior_check_is_a_typed_400(make_config):
    app = create_app(make_config())
    client = TestClient(app)
    r = client.post("/api/app-update/pull")
    assert r.status_code == 400
    assert "check first" in r.json()["detail"]


def test_pull_unsupervised_installs_but_never_restarts(make_config, monkeypatch):
    app = create_app(make_config())
    client = TestClient(app)
    monkeypatch.setattr(app_update_router, "check_for_update", lambda repo_root: _PENDING)
    monkeypatch.setattr(
        app_update_router, "pull_update", lambda repo_root: {"output": "Fast-forward", "new_commit": "cccccccc"},
    )
    monkeypatch.setattr(app_update_router, "SUPERVISED_RESTART_OK", False)
    client.post("/api/app-update/check")

    r = client.post("/api/app-update/pull")
    assert r.status_code == 200
    assert r.json() == {
        "ok": True, "restart_required": True, "self_restarting": False,
        "output": "Fast-forward", "new_commit": "cccccccc",
    }
    assert restart_calls == [], "must never trigger a real restart when unsupervised"

    # pending state was cleared by the pull regardless of supervision
    status = client.get("/api/app-update/status").json()
    assert status["pending"] is None


def test_pull_supervised_triggers_restart(make_config, monkeypatch):
    app = create_app(make_config())
    client = TestClient(app)
    monkeypatch.setattr(app_update_router, "check_for_update", lambda repo_root: _PENDING)
    monkeypatch.setattr(
        app_update_router, "pull_update", lambda repo_root: {"output": "Fast-forward", "new_commit": "cccccccc"},
    )
    monkeypatch.setattr(app_update_router, "SUPERVISED_RESTART_OK", True)
    client.post("/api/app-update/check")

    r = client.post("/api/app-update/pull")
    assert r.status_code == 200
    body = r.json()
    assert body["self_restarting"] is True
    assert body["new_commit"] == "cccccccc"
    assert restart_calls == [1], "the restart trigger must actually fire when supervised"


def test_pull_failure_is_a_typed_502_and_leaves_pending_state_intact(make_config, monkeypatch):
    app = create_app(make_config())
    client = TestClient(app)
    monkeypatch.setattr(app_update_router, "check_for_update", lambda repo_root: _PENDING)

    def boom(repo_root):
        raise RuntimeError("fatal: Not possible to fast-forward, aborting.")

    monkeypatch.setattr(app_update_router, "pull_update", boom)
    client.post("/api/app-update/check")

    r = client.post("/api/app-update/pull")
    assert r.status_code == 502
    assert "fast-forward" in r.json()["detail"].lower()

    # the failed pull must NOT have cleared pending state
    status = client.get("/api/app-update/status").json()
    assert status["pending"] == _PENDING
    assert restart_calls == []
