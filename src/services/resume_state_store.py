"""Persistence for `PlaybackResumeState`, plus the throttled-checkpoint
policy on top of it.

Two pieces, same file: `PlaybackResumeStateStore` (a thin typed wrapper
over `storage.JsonStore` — the Manager Isolation Law's "real
persisted-document Store," never imported directly by a `web/routers/`
module) and `ResumeCheckpointManager` (the thing a router actually pulls
off `app.state` instead).

Each story series' periodic position checkpoint is throttled
independently (write at most once per `min_interval_seconds` unless
`force=True`) — tuning between two different stories within one story's
throttle window must not block the *other* story's own write. Marking a
series `listened` (`mark_listened`) always writes immediately, bypassing
the throttle entirely: finishing a series is a discrete milestone, not a
periodic tick, and losing it to a crash before the next throttled write
would wrongly un-complete a story the listener already heard through.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from primitives import StoryPartNumber, StorySeriesId
from schema import PLAYBACK_RESUME_STATE_SCHEMA_VERSION, PlaybackResumeState, SeriesResumeState
from storage import JsonStore

__all__ = ["PlaybackResumeStateStore", "ResumeCheckpointManager"]

DEFAULT_CHECKPOINT_INTERVAL_SECONDS = 15.0


@dataclass(frozen=True, slots=True)
class PlaybackResumeStateStore:
    """Typed persistence for the one `PlaybackResumeState` document (every
    story series' own resume state, keyed inside it by `series_id`)."""

    path: Path

    def load(self) -> PlaybackResumeState:
        store = JsonStore(self.path, schema_version=PLAYBACK_RESUME_STATE_SCHEMA_VERSION)
        return PlaybackResumeState.from_dict(store.read_or({}))

    def save(self, state: PlaybackResumeState) -> None:
        store = JsonStore(self.path, schema_version=PLAYBACK_RESUME_STATE_SCHEMA_VERSION)
        store.write(state.to_dict())


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass(slots=True)
class ResumeCheckpointManager:
    """Owns when a checkpoint write actually happens. Not frozen — it
    tracks mutable per-series `_last_write_monotonic` state between calls,
    same reasoning a sibling app's own `*Manager` classes carry mutable
    runtime state while the documents they persist stay frozen."""

    store: PlaybackResumeStateStore
    min_interval_seconds: float = DEFAULT_CHECKPOINT_INTERVAL_SECONDS
    _last_write_monotonic: dict[str, float] = field(default_factory=dict, init=False, repr=False)

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
        """Write this series' position if `force` is set or enough time
        has passed since its own last real write. Returns whether a write
        actually happened — useful for tests, not required by callers."""
        now = time.monotonic()
        last = self._last_write_monotonic.get(series_id.value)
        due = force or last is None or (now - last) >= self.min_interval_seconds
        if not due:
            return False

        state = self.store.load()
        existing = state.for_series(series_id.value)
        updated = SeriesResumeState(
            series_id=series_id.value,
            part_number=part_number.value,
            elapsed_seconds=elapsed_seconds,
            listened=existing.listened if existing is not None else False,
            last_updated=_now_iso(),
        )
        self.store.save(state.with_series(updated))
        self._last_write_monotonic[series_id.value] = now
        return True

    def mark_listened(self, series_id: StorySeriesId, *, final_part_number: StoryPartNumber) -> None:
        """Flags `series_id` as heard through to its end — always an
        immediate, unthrottled write (a completion event, not a periodic
        position tick). Preserves whatever `elapsed_seconds` was last
        checkpointed for this series rather than fabricating a value."""
        state = self.store.load()
        existing = state.for_series(series_id.value)
        updated = SeriesResumeState(
            series_id=series_id.value,
            part_number=final_part_number.value,
            elapsed_seconds=existing.elapsed_seconds if existing is not None else 0.0,
            listened=True,
            last_updated=_now_iso(),
        )
        self.store.save(state.with_series(updated))
