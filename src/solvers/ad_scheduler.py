"""Whether to play an interlude (commercial/snippet) next — two distinct,
deliberately NOT-unified mechanisms, confirmed directly with the owner:

* **Music**: a plain 25% chance per track end. No dice framing — the owner
  was asked directly whether this should also become a d100 roll for
  consistency with Stories, and said no, keep it a plain percentage check.
* **Stories**: a d100 roll, 1-50 triggers, 51-100 doesn't — the owner's own
  literal D&D-dice framing ("roll it 1-50 and 51-100").

Both pure functions take an injected `random.Random` (defaulting to the
module-level `random`), so a test can seed it for a deterministic result
instead of asserting on a long-run statistical rate.
"""

from __future__ import annotations

import random

from primitives import D100Roll

__all__ = [
    "MUSIC_AD_CHANCE",
    "STORY_AD_D100_THRESHOLD",
    "roll_d100",
    "should_play_interlude_after_music_track",
    "should_play_interlude_after_story_part",
]

MUSIC_AD_CHANCE = 0.25
STORY_AD_D100_THRESHOLD = 50


def roll_d100(rng: random.Random | None = None) -> D100Roll:
    """Roll one d100 — a value in [1, 100]."""
    source = rng if rng is not None else random
    return D100Roll(source.randint(1, 100))


def should_play_interlude_after_music_track(rng: random.Random | None = None) -> bool:
    source = rng if rng is not None else random
    return source.random() < MUSIC_AD_CHANCE


def should_play_interlude_after_story_part(rng: random.Random | None = None) -> bool:
    return roll_d100(rng).triggers(STORY_AD_D100_THRESHOLD)
