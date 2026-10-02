"""Pure algorithm layer for IRD v3 — the ad/interlude scheduler and the
story-sequencing walk. No I/O, no filesystem, no `adapters/` import at
all. Re-exports the package's public names."""

from __future__ import annotations

from .ad_scheduler import (
    MUSIC_AD_CHANCE,
    STORY_AD_D100_THRESHOLD,
    roll_d100,
    should_play_interlude_after_music_track,
    should_play_interlude_after_story_part,
)
from .story_sequence import StorySeriesOrder, resolve_next_story_position

__all__ = [
    "MUSIC_AD_CHANCE",
    "STORY_AD_D100_THRESHOLD",
    "roll_d100",
    "should_play_interlude_after_music_track",
    "should_play_interlude_after_story_part",
    "StorySeriesOrder",
    "resolve_next_story_position",
]
