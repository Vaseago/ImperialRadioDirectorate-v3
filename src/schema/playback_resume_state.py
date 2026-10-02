"""`PlaybackResumeState` — every story series' own resume position.

Resolved 2026-10-01 (owner, live session): Stories is tuned like a Music
station — the listener picks which series to play, same as picking a
station — rather than one combined channel that auto-cycles through
every series in a fixed order. That means resume position can no longer
be a single global document: each series remembers its own
(`part_number`, `elapsed_seconds`) independently, so tuning back into any
story resumes exactly where that story was left off, regardless of what
else was listened to in between. Each series also tracks whether it has
been `listened` through to its end at least once — `services.
playback_service.StoriesChannelService.advance` uses this to auto-advance
to the next unheard series once the current one finishes, stopping once
every series has been heard through once (owner's own call — not a
reset-and-loop, not an infinite repeat of the last one).

Schema version bumped to 2 for this shape change — this gaming-PC test
environment has no real persisted data to migrate, so it's a clean break,
not a migration path.

A checkpoint is written periodically during story playback and on
pause/stop (`services.resume_state_store`), not continuously — the
owner's own words, "as close as possible," not frame-exact. Marking a
series `listened` is a discrete milestone, not a periodic tick, so it is
always force-written (`ResumeCheckpointManager.mark_listened`), never
subject to the periodic-checkpoint throttle.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ._coerce import as_bool, as_float, as_int, as_str

__all__ = ["PLAYBACK_RESUME_STATE_SCHEMA_VERSION", "SeriesResumeState", "PlaybackResumeState"]

PLAYBACK_RESUME_STATE_SCHEMA_VERSION = 2


@dataclass(frozen=True, slots=True)
class SeriesResumeState:
    """Where one story series left off, and whether it has been heard
    through to its end at least once."""

    series_id: str
    part_number: int = 1
    elapsed_seconds: float = 0.0
    listened: bool = False
    last_updated: str = ""  # ISO-8601 UTC timestamp; "" if never saved

    def to_dict(self) -> dict[str, Any]:
        return {
            "series_id": self.series_id,
            "part_number": self.part_number,
            "elapsed_seconds": self.elapsed_seconds,
            "listened": self.listened,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, d: object) -> SeriesResumeState:
        if not isinstance(d, dict):
            return cls(series_id="")
        part_number = as_int(d.get("part_number"), default=1)
        return cls(
            series_id=as_str(d.get("series_id")),
            part_number=part_number if part_number >= 1 else 1,
            elapsed_seconds=max(0.0, as_float(d.get("elapsed_seconds"))),
            listened=as_bool(d.get("listened")),
            last_updated=as_str(d.get("last_updated")),
        )


@dataclass(frozen=True, slots=True)
class PlaybackResumeState:
    """Every story series' own resume state. An empty tuple means no
    story has ever been played."""

    series: tuple[SeriesResumeState, ...] = ()

    def for_series(self, series_id: str) -> SeriesResumeState | None:
        return next((s for s in self.series if s.series_id == series_id), None)

    def listened_series_ids(self) -> frozenset[str]:
        return frozenset(s.series_id for s in self.series if s.listened)

    def with_series(self, updated: SeriesResumeState) -> PlaybackResumeState:
        """A new state with `updated` replacing any existing entry for its
        `series_id` (or appended if that series has no entry yet)."""
        remaining = tuple(s for s in self.series if s.series_id != updated.series_id)
        return PlaybackResumeState(series=(*remaining, updated))

    def to_dict(self) -> dict[str, Any]:
        return {"series": [s.to_dict() for s in self.series]}

    @classmethod
    def from_dict(cls, d: object) -> PlaybackResumeState:
        if not isinstance(d, dict):
            return cls()
        raw_series = d.get("series")
        if not isinstance(raw_series, list):
            return cls()
        series = tuple(
            SeriesResumeState.from_dict(raw) for raw in raw_series if isinstance(raw, dict) and raw.get("series_id")
        )
        return cls(series=series)
