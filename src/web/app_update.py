"""Git-pull-based self-update — this app runs from a live git checkout,
not a packaged installer, so "update" means pulling the latest commits
from GitHub. Same "check and ask" two-step flow as every other mutating
surface in this app: checking never pulls anything on its own.

Clean-room re-derivation of IID v3's own `web/app_update.py` (same proven
shape — hand-matched, not copied) — see `../GIT_WORKFLOW.md` at the
Imperial Apps root, which applies to this app automatically. Takes an
explicit `repo_root` parameter rather than a module-level config
constant, so it's testable without monkeypatching module globals.

**`GIT_WORKFLOW.md` release-tag policy**: compares against the `release`
tag, never `master`'s raw tip. `master` gets pushed to freely, often
mid-task, purely as a backup — that's not the same thing as "safe for a
live user to install." The `release` tag marks the one commit the owner
has explicitly confirmed ready; it moves only on the owner's explicit
sign-off, never automatically. If the `release` tag doesn't exist on
origin yet, `check_for_update` reads that the same as "already up to
date" — a real git failure elsewhere (network, auth) still raises
normally, only a missing tag ref is treated as "nothing pending."

Backend (`.py`) changes need a process restart to actually take effect
after pulling (frontend HTML/JS/CSS already applies on the next request,
no restart needed) — this module itself never restarts anything, stays a
pure git-pull function with no process-lifecycle knowledge. Whether a
restart happens automatically after a pull is entirely the CALLER's
decision (`web.routers.app_update`), not this module's.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

__all__ = ["check_for_update", "pull_update"]

_GIT_TIMEOUT_SECONDS = 30
_RELEASE_TAG_REF = "refs/tags/release"


def _run_git(repo_root: Path, *args: str) -> str:
    """Runs from `repo_root` — any directory inside the working tree
    works identically, since `git` discovers the real `.git` root by
    walking up parent directories on its own."""
    result = subprocess.run(
        ["git", *args], cwd=repo_root, capture_output=True, text=True, timeout=_GIT_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def _resolve_release_tag(repo_root: Path) -> str | None:
    """The commit the `release` tag points at on origin, or `None` if that
    tag doesn't exist there yet — a real, expected state (nothing has ever
    been marked ready), not an error.

    **`^{commit}` peeling is load-bearing, not decoration** — found live
    2026-10-02 testing this against this app's own real `release` tag: an
    ANNOTATED tag (`git tag -a`, the normal `-m`-message form) is itself a
    distinct object, so a bare `rev-parse refs/tags/release` returns that
    TAG object's own hash, never the commit it points to. Without
    peeling, `check_for_update` would compare HEAD against the tag
    object's hash — which can never be equal to a commit hash — so it
    would report "an update is pending" forever, even the instant after a
    real pull lands exactly on the tagged commit. `^{commit}` (equivalent
    to `^{}`) dereferences through any number of tag layers down to the
    real commit; it's a no-op and still correct for a lightweight tag,
    which has no separate object to peel through."""
    try:
        return _run_git(repo_root, "rev-parse", f"{_RELEASE_TAG_REF}^{{commit}}")
    except RuntimeError:
        return None


def check_for_update(repo_root: Path) -> dict | None:
    """Fetches from origin including tags (makes no local changes) and
    compares HEAD against the `release` tag. Returns `None` if already up
    to date (or the tag doesn't exist yet), otherwise a dict describing
    what's pending.

    **`--force` on the tag fetch is deliberate, not a shortcut** — `release`
    is a MOVING tag by design (`../GIT_WORKFLOW.md` — re-point it and
    force-push whenever a new commit is confirmed ready). A plain `git
    fetch --tags` refuses to update a client's stale local copy of a tag
    that's been force-pushed on the remote ("would clobber existing
    tag") — a real failure IID v3 hit the first time its own `release` tag
    ever moved (2026-09-20). Forcing here is safe: `origin` is this app's
    own single trusted GitHub remote, and `release` is the only tag this
    app manages at all."""
    _run_git(repo_root, "fetch", "origin", "--tags", "--force")
    remote = _resolve_release_tag(repo_root)
    if remote is None:
        return None
    local = _run_git(repo_root, "rev-parse", "HEAD")
    if local == remote:
        return None
    commits_behind = int(_run_git(repo_root, "rev-list", "--count", f"{local}..{remote}"))
    log = _run_git(repo_root, "log", "--oneline", f"{local}..{remote}")
    return {
        "current_commit": local[:8],
        "latest_commit": remote[:8],
        "commits_behind": commits_behind,
        "log": log,
    }


def pull_update(repo_root: Path) -> dict:
    """Fast-forward-only merge to the `release` tag — refuses (raises)
    rather than creating a merge commit if local history has diverged.
    That shouldn't happen in normal use (nothing here ever commits
    locally on its own), but a hard stop is safer than an automatic merge
    on someone's real working directory.

    Same `--force` tag-fetch reasoning as `check_for_update` above — a
    caller could reach `pull_update` directly (skipping `check_for_update`
    first) and hit the identical stale-local-tag failure otherwise."""
    _run_git(repo_root, "fetch", "origin", "--tags", "--force")
    output = _run_git(repo_root, "merge", "--ff-only", _RELEASE_TAG_REF)
    new_commit = _run_git(repo_root, "rev-parse", "HEAD")
    return {"output": output, "new_commit": new_commit[:8]}
