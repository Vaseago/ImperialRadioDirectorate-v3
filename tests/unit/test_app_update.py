"""Unit tests for `web.app_update` — the git-pull self-update logic.
`subprocess.run` is monkeypatched throughout; no test here ever invokes a
real `git` command against the real repo (the repo this file itself lives
in)."""

from __future__ import annotations

import pytest

from web import app_update


class _FakeCompletedProcess:
    def __init__(self, *, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _fake_run(table: dict):
    """`table` maps a git subcommand tuple (e.g. `("fetch", "origin")`) to
    a `_FakeCompletedProcess` or an `Exception` to raise. `calls` records
    every invocation for assertion."""
    calls: list[tuple[str, ...]] = []

    def _run(cmd, cwd=None, capture_output=None, text=None, timeout=None):
        args = tuple(cmd[1:])  # drop the leading "git"
        calls.append(args)
        result = table.get(args)
        if result is None:
            raise AssertionError(f"unexpected git invocation: {args!r}")
        if isinstance(result, Exception):
            raise result
        return result

    _run.calls = calls
    return _run


def test_check_for_update_returns_none_when_already_up_to_date(tmp_path, monkeypatch):
    monkeypatch.setattr(app_update.subprocess, "run", _fake_run({
        ("fetch", "origin", "--tags", "--force"): _FakeCompletedProcess(),
        ("rev-parse", "refs/tags/release^{commit}"): _FakeCompletedProcess(stdout="abc123\n"),
        ("rev-parse", "HEAD"): _FakeCompletedProcess(stdout="abc123\n"),
    }))
    assert app_update.check_for_update(tmp_path) is None


def test_check_for_update_returns_none_when_the_release_tag_does_not_exist_yet(tmp_path, monkeypatch):
    """Nothing has ever been marked ready — a real, expected state, not an
    error. `rev-parse HEAD` is never even called in this path."""
    fake = _fake_run({
        ("fetch", "origin", "--tags", "--force"): _FakeCompletedProcess(),
        ("rev-parse", "refs/tags/release^{commit}"): _FakeCompletedProcess(
            returncode=1, stderr="fatal: ambiguous argument 'refs/tags/release': unknown revision",
        ),
    })
    monkeypatch.setattr(app_update.subprocess, "run", fake)
    assert app_update.check_for_update(tmp_path) is None
    assert ("rev-parse", "HEAD") not in fake.calls


def test_check_for_update_reports_pending_commits(tmp_path, monkeypatch):
    monkeypatch.setattr(app_update.subprocess, "run", _fake_run({
        ("fetch", "origin", "--tags", "--force"): _FakeCompletedProcess(),
        ("rev-parse", "refs/tags/release^{commit}"): _FakeCompletedProcess(stdout="bbbbbbbb2222\n"),
        ("rev-parse", "HEAD"): _FakeCompletedProcess(stdout="aaaaaaaa1111\n"),
        ("rev-list", "--count", "aaaaaaaa1111..bbbbbbbb2222"): _FakeCompletedProcess(stdout="3\n"),
        ("log", "--oneline", "aaaaaaaa1111..bbbbbbbb2222"): _FakeCompletedProcess(stdout="bbbbbbb two\naaaaaaa one"),
    }))
    result = app_update.check_for_update(tmp_path)
    assert result == {
        "current_commit": "aaaaaaaa",
        "latest_commit": "bbbbbbbb",
        "commits_behind": 3,
        "log": "bbbbbbb two\naaaaaaa one",
    }


def test_check_for_update_never_makes_local_changes_only_fetches(tmp_path, monkeypatch):
    """Confirms the sequence is fetch -> resolve tag -> compare, never a
    pull/merge."""
    fake = _fake_run({
        ("fetch", "origin", "--tags", "--force"): _FakeCompletedProcess(),
        ("rev-parse", "refs/tags/release^{commit}"): _FakeCompletedProcess(stdout="x\n"),
        ("rev-parse", "HEAD"): _FakeCompletedProcess(stdout="x\n"),
    })
    monkeypatch.setattr(app_update.subprocess, "run", fake)
    app_update.check_for_update(tmp_path)
    assert fake.calls == [
        ("fetch", "origin", "--tags", "--force"), ("rev-parse", "refs/tags/release^{commit}"), ("rev-parse", "HEAD"),
    ]


def test_check_for_update_fetch_forces_the_tag_update(tmp_path, monkeypatch):
    """`release` is a MOVING tag by design — a force-pushed tag move on
    origin is refused by a plain `git fetch --tags` on a client with a
    stale local copy ("would clobber existing tag"), the exact real
    failure IID v3 hit the first time its own `release` tag ever moved.
    `--force` on the tag fetch is the fix — this test locks it in so it
    can never silently regress back to a plain fetch."""
    fake = _fake_run({
        ("fetch", "origin", "--tags", "--force"): _FakeCompletedProcess(),
        ("rev-parse", "refs/tags/release^{commit}"): _FakeCompletedProcess(stdout="x\n"),
        ("rev-parse", "HEAD"): _FakeCompletedProcess(stdout="x\n"),
    })
    monkeypatch.setattr(app_update.subprocess, "run", fake)
    app_update.check_for_update(tmp_path)
    assert fake.calls[0] == ("fetch", "origin", "--tags", "--force")


def test_check_for_update_raises_with_stderr_on_a_real_git_failure(tmp_path, monkeypatch):
    """A failure on the FETCH itself (network/auth) still raises — only a
    missing release tag is swallowed as "nothing pending"."""
    monkeypatch.setattr(app_update.subprocess, "run", _fake_run({
        ("fetch", "origin", "--tags", "--force"):
            _FakeCompletedProcess(returncode=1, stderr="fatal: unable to access origin"),
    }))
    with pytest.raises(RuntimeError, match="unable to access origin"):
        app_update.check_for_update(tmp_path)


def test_pull_update_returns_output_and_new_commit(tmp_path, monkeypatch):
    monkeypatch.setattr(app_update.subprocess, "run", _fake_run({
        ("fetch", "origin", "--tags", "--force"): _FakeCompletedProcess(),
        ("merge", "--ff-only", "refs/tags/release"): _FakeCompletedProcess(stdout="Fast-forward\n a.py | 1 +"),
        ("rev-parse", "HEAD"): _FakeCompletedProcess(stdout="deadbeef0000\n"),
    }))
    result = app_update.pull_update(tmp_path)
    assert result == {"output": "Fast-forward\n a.py | 1 +", "new_commit": "deadbeef"}


def test_pull_update_uses_fast_forward_only_against_the_release_tag(tmp_path, monkeypatch):
    fake = _fake_run({
        ("fetch", "origin", "--tags", "--force"): _FakeCompletedProcess(),
        ("merge", "--ff-only", "refs/tags/release"): _FakeCompletedProcess(stdout="ok"),
        ("rev-parse", "HEAD"): _FakeCompletedProcess(stdout="x\n"),
    })
    monkeypatch.setattr(app_update.subprocess, "run", fake)
    app_update.pull_update(tmp_path)
    assert fake.calls[1] == ("merge", "--ff-only", "refs/tags/release")


def test_pull_update_raises_rather_than_merge_on_diverged_history(tmp_path, monkeypatch):
    monkeypatch.setattr(app_update.subprocess, "run", _fake_run({
        ("fetch", "origin", "--tags", "--force"): _FakeCompletedProcess(),
        ("merge", "--ff-only", "refs/tags/release"): _FakeCompletedProcess(
            returncode=1, stderr="fatal: Not possible to fast-forward, aborting.",
        ),
    }))
    with pytest.raises(RuntimeError, match="fast-forward"):
        app_update.pull_update(tmp_path)


def test_run_git_uses_the_given_repo_root_as_cwd(tmp_path, monkeypatch):
    seen_cwd = []

    def _run(cmd, cwd=None, **kw):
        seen_cwd.append(cwd)
        return _FakeCompletedProcess(stdout="ok\n")

    monkeypatch.setattr(app_update.subprocess, "run", _run)
    app_update._run_git(tmp_path, "status")
    assert seen_cwd == [tmp_path]


def test_run_git_raises_with_a_message_even_when_stderr_is_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(app_update.subprocess, "run", lambda *a, **k: _FakeCompletedProcess(returncode=1))
    with pytest.raises(RuntimeError, match="git status failed"):
        app_update._run_git(tmp_path, "status")


# --------------------------------------------------------------------- #
# Real git, no mocking — locks in the annotated-tag peeling fix. A
# monkeypatched `subprocess.run` can't catch this class of bug at all:
# every test above hands back whatever fake hash it's told to, so it
# can't expose real git ref-resolution semantics going wrong. Found live
# 2026-10-02 against this app's own real `release` tag: an ANNOTATED tag
# is a distinct object, so `rev-parse refs/tags/release` (no peeling)
# returns the TAG's own hash, which can never equal a commit hash —
# `check_for_update` would report "pending" forever, even the instant
# after a real pull lands exactly on the tagged commit.
# --------------------------------------------------------------------- #


def _init_repo_with_one_commit(repo_root) -> str:
    import subprocess as sp

    sp.run(["git", "init", "-q"], cwd=repo_root, check=True)
    sp.run(["git", "config", "user.email", "test@example.com"], cwd=repo_root, check=True)
    sp.run(["git", "config", "user.name", "Test"], cwd=repo_root, check=True)
    (repo_root / "a.txt").write_text("hello")
    sp.run(["git", "add", "a.txt"], cwd=repo_root, check=True)
    sp.run(["git", "commit", "-q", "-m", "initial"], cwd=repo_root, check=True)
    return app_update._run_git(repo_root, "rev-parse", "HEAD")


def test_resolve_release_tag_peels_a_real_annotated_tag_to_its_commit(tmp_path):
    commit = _init_repo_with_one_commit(tmp_path)
    import subprocess as sp

    sp.run(["git", "tag", "-a", "release", "-m", "mark it ready"], cwd=tmp_path, check=True)

    resolved = app_update._resolve_release_tag(tmp_path)

    assert resolved == commit
    # Confirms the bug would have been real: the bare (unpeeled) ref
    # resolves to a DIFFERENT hash (the tag object itself), not the commit.
    unpeeled = app_update._run_git(tmp_path, "rev-parse", "refs/tags/release")
    assert unpeeled != commit


def test_resolve_release_tag_also_works_for_a_real_lightweight_tag(tmp_path):
    """`^{commit}` must stay a safe no-op for a lightweight tag (no
    separate tag object to peel through) — this is the other half of the
    claim in `_resolve_release_tag`'s own docstring."""
    commit = _init_repo_with_one_commit(tmp_path)
    import subprocess as sp

    sp.run(["git", "tag", "release"], cwd=tmp_path, check=True)  # no -a: lightweight

    assert app_update._resolve_release_tag(tmp_path) == commit


def test_check_for_update_with_a_real_annotated_release_tag_reports_up_to_date(tmp_path):
    """End-to-end confirmation (still no real network — `fetch origin` is
    swapped for a local-only no-op) that a real annotated `release` tag
    pointing at the real current HEAD reads as "nothing pending," not a
    permanent false positive."""
    import subprocess as sp

    from web import app_update as app_update_module

    _init_repo_with_one_commit(tmp_path)
    sp.run(["git", "tag", "-a", "release", "-m", "mark it ready"], cwd=tmp_path, check=True)

    original_run_git = app_update_module._run_git

    def _skip_fetch(repo_root, *args):
        if args and args[0] == "fetch":
            return ""
        return original_run_git(repo_root, *args)

    import unittest.mock

    with unittest.mock.patch.object(app_update_module, "_run_git", side_effect=_skip_fetch):
        assert app_update_module.check_for_update(tmp_path) is None
