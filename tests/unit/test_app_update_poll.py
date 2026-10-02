"""Unit tests for `web.poller.app_update_poll` — the app-update background
poller. `check_for_update` (imported into this module's namespace) is
monkeypatched throughout — no test here ever invokes a real `git`
command."""

from __future__ import annotations

import asyncio

import pytest

from web.poller import app_update_poll
from web.poller.app_update_poll import AppUpdatePollCycleResult, AppUpdatePoller

_PENDING = {"current_commit": "aaaaaaaa", "latest_commit": "bbbbbbbb", "commits_behind": 1, "log": "bbbbbbb x"}


def _poller(*, initial_pending=None, interval_seconds=1000.0) -> tuple[AppUpdatePoller, dict]:
    """Returns (poller, state) — `state["pending"]` is the fake
    `app.state.pending_app_update` slot the get/set closures read/write,
    mirroring exactly how `web.app`'s real closures work."""
    state = {"pending": initial_pending}
    poller = AppUpdatePoller(
        repo_root=object(),  # never touched — check_for_update itself is monkeypatched
        get_pending=lambda: state["pending"],
        set_pending=lambda p: state.__setitem__("pending", p),
        interval_seconds=interval_seconds,
    )
    return poller, state


# --------------------------------------------------------------------- #
# run_once
# --------------------------------------------------------------------- #


def test_run_once_with_nothing_pending_and_none_before_is_a_clean_noop(monkeypatch):
    monkeypatch.setattr(app_update_poll, "check_for_update", lambda repo_root: None)
    poller, state = _poller()

    result = asyncio.run(poller.run_once())

    assert result == AppUpdatePollCycleResult(pending=None, changed=False)
    assert state["pending"] is None


def test_run_once_finds_a_new_pending_update(monkeypatch):
    monkeypatch.setattr(app_update_poll, "check_for_update", lambda repo_root: _PENDING)
    poller, state = _poller()

    result = asyncio.run(poller.run_once())

    assert result == AppUpdatePollCycleResult(pending=_PENDING, changed=True)
    assert state["pending"] == _PENDING


def test_run_once_with_the_same_pending_state_as_before_reports_unchanged(monkeypatch):
    monkeypatch.setattr(app_update_poll, "check_for_update", lambda repo_root: _PENDING)
    poller, state = _poller(initial_pending=_PENDING)

    result = asyncio.run(poller.run_once())

    assert result == AppUpdatePollCycleResult(pending=_PENDING, changed=False)
    assert state["pending"] == _PENDING


def test_run_once_detects_a_manual_pull_clearing_pending_state(monkeypatch):
    """The poller must also notice when a manual /pull already cleared
    pending state between cycles — not just when a NEW update appears."""
    monkeypatch.setattr(app_update_poll, "check_for_update", lambda repo_root: None)
    poller, state = _poller(initial_pending=_PENDING)

    result = asyncio.run(poller.run_once())

    assert result == AppUpdatePollCycleResult(pending=None, changed=True)
    assert state["pending"] is None


def test_run_once_never_pulls(monkeypatch):
    """This poller must physically be incapable of installing anything —
    pull_update is never even imported into this module."""
    assert not hasattr(app_update_poll, "pull_update")


# --------------------------------------------------------------------- #
# run_forever — lifecycle
# --------------------------------------------------------------------- #


async def _wait_until(predicate, *, timeout=2.0, step=0.01):
    waited = 0.0
    while not predicate():
        if waited >= timeout:
            raise AssertionError(f"condition not met within {timeout}s")
        await asyncio.sleep(step)
        waited += step


def test_run_forever_keeps_ticking_and_never_raises_out(monkeypatch):
    monkeypatch.setattr(app_update_poll, "check_for_update", lambda repo_root: None)
    poller, _ = _poller(interval_seconds=1000)

    async def run():
        task = asyncio.create_task(poller.run_forever())
        await _wait_until(lambda: poller.last_result is not None)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run())
    assert poller.last_error is None
    assert poller.last_result is not None


def test_run_forever_records_a_raising_check_without_dying(monkeypatch):
    def boom(repo_root):
        raise RuntimeError("totally unexpected")

    monkeypatch.setattr(app_update_poll, "check_for_update", boom)
    poller, _ = _poller(interval_seconds=1000)

    async def run():
        task = asyncio.create_task(poller.run_forever())
        await _wait_until(lambda: poller.last_error is not None)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run())
    assert isinstance(poller.last_error, RuntimeError)
