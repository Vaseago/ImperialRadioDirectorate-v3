"""Whether this process may safely self-restart, and how to do it — the
gate + mechanism an app-update pull uses before exiting.

Clean-room re-derivation of IID v3's own `web/supervised_restart.py` (hand
-matched, not copied) — that mechanism is real, live-verified on IID's own
Pi deployment (2026-08-29: a real update self-restarted correctly with no
SSH needed). IRD v3 has no other poller needing this yet (no SDE to
rotate), so `web.routers.app_update` is this module's only caller here.
"""

from __future__ import annotations

import asyncio
import os
import signal
from collections.abc import Callable

__all__ = ["SUPERVISED_RESTART_OK", "trigger_self_restart"]

# Set ONLY by _supervisor/supervisor.py's own _start(), on every child it
# spawns — nowhere else in this codebase ever sets it. The single
# condition gating a real self-restart: present only for a
# supervisor-managed process, the only deployment with an existing
# auto-restart-on-exit safety net (supervisor.py's own poll loop that
# relaunches any child whose process has exited). A process supervisor.py
# never spawned (ird-v3-test, a bare `python ird_v3_web_main.py` run, a
# future desktop/frozen build) has nothing bringing it back up, so
# self-restarting there would just kill it for good — this gate is what
# makes self-exit safe to even consider. Computed once at import time —
# the env var can't change during this process's own lifetime.
SUPERVISED_RESTART_OK = os.environ.get("SUPERVISED_RESTART_OK") == "1"

# Breathing room for a just-sent response/broadcast to actually flush
# before the process starts tearing down — matches IID v3's own value.
_RESTART_GRACE_SECONDS = 1.0


def _real_restart() -> None:
    os.kill(os.getpid(), signal.SIGTERM)


async def trigger_self_restart(*, restart_fn: Callable[[], None] | None = None) -> None:
    """A real SIGTERM (not `os._exit()`) after a short grace period — so
    uvicorn's own already-correct graceful-shutdown path runs (drains
    in-flight requests, runs ASGI lifespan shutdown — this app's own
    `app_update_poller` task cancellation included), the same path an
    operator's Ctrl+C already takes today. `supervisor.py`'s
    restart-on-exit poll loop then relaunches this process fresh,
    typically within a couple seconds.

    `restart_fn`, if given, replaces the real `os.kill` call — a test
    must never send a real SIGTERM to the test process itself."""
    await asyncio.sleep(_RESTART_GRACE_SECONDS)
    (restart_fn or _real_restart)()
