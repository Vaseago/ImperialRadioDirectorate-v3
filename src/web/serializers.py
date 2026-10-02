"""Plain-dict JSON shapes shared by more than one router — kept out of
any single router module so `music.py`/`stories.py` don't duplicate the
same track shape."""

from __future__ import annotations

from typing import Any

from adapters.library import Track
from primitives import StoryPartNumber, StorySeriesId
from services import StorySeriesSummary

__all__ = ["serialize_track", "serialize_story_position", "serialize_story_series_summary"]


def serialize_track(track: Track) -> dict[str, Any]:
    return {
        "id": track.id.value,
        "title": track.title,
        "artist": track.artist,
        "album": track.album,
        "duration_seconds": track.duration_seconds,
        "stream_url": f"/api/tracks/{track.id.value}/stream",
    }


def serialize_story_position(series_id: StorySeriesId, part_number: StoryPartNumber) -> dict[str, Any]:
    return {"series_id": series_id.value, "part_number": part_number.value}


def serialize_story_series_summary(summary: StorySeriesSummary) -> dict[str, Any]:
    return {
        "series_id": summary.series_id.value,
        "part_count": summary.part_count,
        "listened": summary.listened,
        "resume_part_number": summary.resume_part_number.value,
    }
