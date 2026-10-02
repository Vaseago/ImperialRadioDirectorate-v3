"""Pure data model for scanned library content — no filesystem/web
dependency of its own, mirrors legacy IRD's own `library/models.py`
separation-of-concerns principle (re-derived, not copied: this version
wraps identity in the validated `primitives` types instead of bare
strings)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from primitives import StationName, TrackId

__all__ = ["Track"]


@dataclass(frozen=True, slots=True)
class Track:
    """One scanned audio file — music, a commercial/snippet, or a story
    part (story parts additionally carry series/part identity, see
    `story_scanner.StoryPart`, which wraps one of these)."""

    id: TrackId
    title: str
    artist: str
    album: str
    duration_seconds: float
    path: Path
    library_dir: Path
    mtime: float
    station: StationName
