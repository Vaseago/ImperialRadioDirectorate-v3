"""`GET /api/app-update/status`, `POST /api/app-update/check`, `POST
/api/app-update/pull` — git-pull-based self-update for this app's own
source. Same two-step "check and ask" flow every other mutating surface
in this app uses: checking never pulls anything on its own, a separate
explicit action does.

Self-restart after pulling is conditional on `web.supervised_restart.
SUPERVISED_RESTART_OK` — on a supervisor-managed process (spawned by
`_supervisor/supervisor.py`, the only deployment with an existing
auto-restart-on-exit safety net), a pull is followed by a real, graceful
self-exit and supervisor.py's own restart-on-exit poll loop relaunches
this app fresh from the now-updated code within a couple seconds.
Everywhere else (`ird-v3-test`, a bare `python ird_v3_web_main.py` run,
any future desktop/frozen build): nothing about this changes — backend
(`.py`) changes still need a real restart to load, and there's no safety
net to catch a self-exit, so the response just reports a restart is
recommended and leaves it to the operator. No broadcast in that case
either (IRD v3 has no WebSocket hub at all) — only the one client that
clicked "pull" needs to know, via the HTTP response itself.

Available only in a real git checkout — `check`/`pull` 404 in a
(currently hypothetical) frozen build. This router needs no `Config` at
all (git operations don't touch it), so it's always included in
`create_app`, gated per-route instead of by omission. No per-route CSRF
dependency either — `require_same_origin_header` only guards
`/api/stories/checkpoint` today, but a future app-wide same-origin
middleware (if ever added) would cover this too; for now `/pull` is a
state-changing action gated behind the two-step check-then-pull flow,
same posture IID v3 took before it had app-wide middleware.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from web.app_update import check_for_update, pull_update
from web.supervised_restart import SUPERVISED_RESTART_OK, trigger_self_restart

__all__ = ["router"]

router = APIRouter(prefix="/api/app-update", tags=["app_update"])

# check_for_update()/pull_update() both run `git` against the real
# checkout — meaningless in a (currently hypothetical) packaged build,
# where there is no "origin" remote to pull from. Computed once — the
# frozen-ness of a running process can't change at runtime.
_AVAILABLE = not getattr(sys, "frozen", False)

# This file lives at <repo>/src/web/routers/app_update.py — three parents
# up is <repo> itself. Any directory inside the working tree works
# identically for git (see web.app_update's own docstring); this is just
# a concrete, always-correct anchor that doesn't depend on `Config`.
_REPO_ROOT = Path(__file__).resolve().parents[3]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@router.get("/status")
async def get_status(request: Request) -> dict:
    """Lets a freshly (re)loaded page find out immediately whether an
    update is already pending, without re-running the check. `available`
    lets the frontend hide the whole control for a build that can never
    use it, rather than showing a button that can only ever fail."""
    return {"pending": request.app.state.pending_app_update, "available": _AVAILABLE}


@router.post("/check")
async def check(request: Request) -> dict:
    if not _AVAILABLE:
        raise HTTPException(404, "App update via git pull is not available in a packaged build.")
    try:
        pending = await asyncio.to_thread(check_for_update, _REPO_ROOT)
    except Exception as exc:
        raise HTTPException(502, f"Update check failed: {exc}") from exc
    request.app.state.pending_app_update = pending
    return {"pending": pending}


@router.post("/pull")
async def pull(request: Request, background_tasks: BackgroundTasks) -> dict:
    """Only allowed once a check has actually flagged something pending —
    never a standalone "just pull whatever's newest" action."""
    if not _AVAILABLE:
        raise HTTPException(404, "App update via git pull is not available in a packaged build.")
    if request.app.state.pending_app_update is None:
        raise HTTPException(400, "No pending update — check first.")

    try:
        result = await asyncio.to_thread(pull_update, _REPO_ROOT)
    except Exception as exc:
        raise HTTPException(502, f"Update failed: {exc}") from exc
    request.app.state.pending_app_update = None

    if SUPERVISED_RESTART_OK:
        # BackgroundTasks (not asyncio.create_task) is deliberate — it
        # only runs AFTER the response has been handed to the ASGI
        # transport, guaranteeing the client already has its response
        # before this process starts exiting.
        background_tasks.add_task(trigger_self_restart)

    return {"ok": True, "restart_required": True, "self_restarting": SUPERVISED_RESTART_OK, **result}
