"""Plain-dict JSON shapes shared by more than one router — kept out of
any single router module so `music.py`/`stories.py` don't duplicate the
same track shape."""

from __future__ import annotations

from typing import Any

from adapters.library import Track
from primitives import StoryPartNumber, StorySeriesId

__all__ = ["serialize_track", "serialize_story_position"]


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
