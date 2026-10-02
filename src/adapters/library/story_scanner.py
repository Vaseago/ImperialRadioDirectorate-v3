"""Scans `stories/` for story series. Each top-level subfolder is one
series (e.g. `stories/alien_invasion/`); files inside are ordered by the
trailing digit run in their filename stem (`alien_invasion1.mp3`,
`alien_invasion2.mp3`, ... `alien_invasion10.mp3` sorts numerically, not
as strings — a file named `alien_invasion10` must not sort before
`alien_invasion2`).

A file with no trailing digits can't be placed in sequence, so it's
skipped from the story entirely (same per-item resilience philosophy as
`scanner.py` skipping an unreadable audio file) rather than guessing an
order or aborting the whole scan.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from config import SUPPORTED_AUDIO_EXTENSIONS
from primitives import StoryPartNumber, StorySeriesId

from .models import Track
from .scanner import _read_track

__all__ = ["StoryPart", "StorySeries", "scan_story_dirs"]

_TRAILING_DIGITS = re.compile(r"(\d+)$")


@dataclass(frozen=True, slots=True)
class StoryPart:
    series_id: StorySeriesId
    part_number: StoryPartNumber
    track: Track


@dataclass(frozen=True, slots=True)
class StorySeries:
    series_id: StorySeriesId
    parts: tuple[StoryPart, ...]  # always sorted ascending by part_number


def _part_number_from_filename(stem: str) -> StoryPartNumber | None:
    match = _TRAILING_DIGITS.search(stem)
    if match is None:
        return None
    return StoryPartNumber(int(match.group(1)))


def _scan_one_series_dir(series_dir: Path) -> StorySeries | None:
    series_id = StorySeriesId(series_dir.name)
    parts: list[StoryPart] = []
    for path in sorted(series_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
            continue
        part_number = _part_number_from_filename(path.stem)
        if part_number is None:
            continue  # can't place it in sequence — skip, don't guess
        track = _read_track(path, series_dir)
        if track is None:
            continue  # unreadable file — same resilience rule as scanner.py
        parts.append(StoryPart(series_id=series_id, part_number=part_number, track=track))

    if not parts:
        return None
    parts.sort(key=lambda p: p.part_number.value)
    return StorySeries(series_id=series_id, parts=tuple(parts))


def scan_story_dirs(dirs: tuple[Path, ...]) -> tuple[StorySeries, ...]:
    """Every story series found across `dirs`, sorted alphabetically by
    series id — the deterministic order the Stories channel plays them in.
    A series folder with zero placeable parts is omitted entirely."""
    series: list[StorySeries] = []
    for stories_dir in dirs:
        if not stories_dir.is_dir():
            continue
        for entry in sorted(stories_dir.iterdir()):
            if not entry.is_dir():
                continue
            found = _scan_one_series_dir(entry)
            if found is not None:
                series.append(found)
    series.sort(key=lambda s: s.series_id.value)
    return tuple(series)
