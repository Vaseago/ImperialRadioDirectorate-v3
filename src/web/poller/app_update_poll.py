"""The app-update background poller — periodically checks for a pending
`release`-tag update and keeps `app.state.pending_app_update` in sync, but
NEVER pulls. Mirrors IID v3's own `AppUpdatePoller` shape (`run_once()`/
`run_forever()`, never dies) with the same deliberate restriction: this
poller only ever calls `check_for_update`, never `pull_update`.

**Deliberately the opposite automation posture an auto-install poller
would have** — app (git) updates never auto-pull, ever, no matter how
small the change looks (`../GIT_WORKFLOW.md`'s release-tag policy exists
precisely so a live user's install is never moved without the owner's
explicit sign-off). This poller's entire job is making "an update is
ready" visible (`GET /api/app-update/status`) without waiting for someone
to remember to click "Check for Update" — pulling stays a deliberate,
separate, manual action.

**No WebSocket broadcast** — unlike IID v3's own poller (which has a
`ConnectionHub` for other reasons and piggybacks on it here), IRD v3 has
no WebSocket infrastructure at all and nothing else that would justify
building one just for this. The frontend simply polls `GET
/api/app-update/status` on load; `get_pending`/`set_pending` are still
injected callables (reading/writing `app.state.pending_app_update`)
rather than a hard `app.state` reference, so this stays testable without
constructing a real FastAPI app, and so the poller and the manual
`/api/app-update/check` route can never drift out of sync about what
"pending" means.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from web.app_update import check_for_update

__all__ = ["AppUpdatePollCycleResult", "AppUpdatePoller"]

# A `git fetch` is cheap, but there is still no reason to hammer origin —
# this repo doesn't get updated more than a handful of times a day at
# most. Matches IID v3's own default.
_DEFAULT_CHECK_INTERVAL_SECONDS = 24 * 60 * 60


@dataclass(frozen=True, slots=True)
class AppUpdatePollCycleResult:
    pending: dict | None
    changed: bool


class AppUpdatePoller:
    """Owns the timer. `run_once()` is one full cycle (also callable
    directly); `run_forever()` is the `asyncio.create_task`-able loop
    `web.app`'s lifespan starts/cancels."""

    def __init__(
        self,
        *,
        repo_root: Path,
        get_pending: Callable[[], dict | None],
        set_pending: Callable[[dict | None], None],
        interval_seconds: float = _DEFAULT_CHECK_INTERVAL_SECONDS,
    ) -> None:
        self._repo_root = repo_root
        self._get_pending = get_pending
        self._set_pending = set_pending
        self._interval_seconds = interval_seconds
        self.last_error: Exception | None = None
        self.last_result: AppUpdatePollCycleResult | None = None

    async def run_once(self) -> AppUpdatePollCycleResult:
        pending = await asyncio.to_thread(check_for_update, self._repo_root)
        previous = self._get_pending()
        changed = pending != previous
        if changed:
            self._set_pending(pending)
        result = AppUpdatePollCycleResult(pending=pending, changed=changed)
        self.last_result = result
        return result

    async def run_forever(self) -> None:
        """Never lets an exception escape — one bad cycle is recorded
        (`last_error`) and the loop ticks again next interval, the same
        contract every background poller in this codebase follows."""
        while True:
            try:
                self.last_error = None
                await self.run_once()
            except Exception as exc:  # noqa: BLE001 - a background loop must never die
                self.last_error = exc
            await asyncio.sleep(self._interval_seconds)
