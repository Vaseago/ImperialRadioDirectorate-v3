"""Persistence for `PlaybackResumeState`, plus the throttled-checkpoint
policy on top of it.

Two pieces, same file (Phase 4's own scope): `PlaybackResumeStateStore`
(a thin typed wrapper over `storage.JsonStore` — the Manager Isolation
Law's "real persisted-document Store", never imported directly by a
future `web/routers/` module once Phase 5 lands) and
`ResumeCheckpointManager` (the thing a router *would* pull off
`app.state` instead — owns the throttling policy: write at most once per
`min_interval_seconds` unless `force=True`, "as close as possible," not
continuous, the owner's own words).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from primitives import StoryPartNumber, StorySeriesId
from schema import PLAYBACK_RESUME_STATE_SCHEMA_VERSION, PlaybackResumeState
from storage import JsonStore

__all__ = ["PlaybackResumeStateStore", "ResumeCheckpointManager"]

DEFAULT_CHECKPOINT_INTERVAL_SECONDS = 15.0


@dataclass(frozen=True, slots=True)
class PlaybackResumeStateStore:
    """Typed persistence for the one `PlaybackResumeState` singleton."""

    path: Path

    def load(self) -> PlaybackResumeState:
        store = JsonStore(self.path, schema_version=PLAYBACK_RESUME_STATE_SCHEMA_VERSION)
        return PlaybackResumeState.from_dict(store.read_or({}))

    def save(self, state: PlaybackResumeState) -> None:
        store = JsonStore(self.path, schema_version=PLAYBACK_RESUME_STATE_SCHEMA_VERSION)
        store.write(state.to_dict())


@dataclass(slots=True)
class ResumeCheckpointManager:
    """Owns when a checkpoint write actually happens. Not frozen — it
    tracks mutable `_last_write_monotonic` state between calls, same
    reasoning a sibling app's own `*Manager` classes carry mutable
    runtime state while the documents they persist stay frozen."""

    store: PlaybackResumeStateStore
    min_interval_seconds: float = DEFAULT_CHECKPOINT_INTERVAL_SECONDS
    _last_write_monotonic: float | None = field(default=None, init=False, repr=False)

    def load(self) -> PlaybackResumeState:
        return self.store.load()

    def checkpoint(
        self,
        *,
        series_id: StorySeriesId,
        part_number: StoryPartNumber,
        elapsed_seconds: float,
        force: bool = False,
    ) -> bool:
        """Write a checkpoint if `force` is set or enough time has passed
        since the last real write. Returns whether a write actually
        happened — useful for tests, not required by callers."""
        now = time.monotonic()
        due = (
            force
            or self._last_write_monotonic is None
            or (now - self._last_write_monotonic) >= self.min_interval_seconds
        )
        if not due:
            return False
        state = PlaybackResumeState(
            series_id=series_id.value,
            part_number=part_number.value,
            elapsed_seconds=elapsed_seconds,
            last_updated=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        self.store.save(state)
        self._last_write_monotonic = now
        return True
