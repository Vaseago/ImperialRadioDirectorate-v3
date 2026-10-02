"""Background pollers for IRD v3 — one, for now: the app-update checker.
Re-exports the package's public names."""

from __future__ import annotations

from .app_update_poll import AppUpdatePollCycleResult, AppUpdatePoller

__all__ = ["AppUpdatePollCycleResult", "AppUpdatePoller"]
