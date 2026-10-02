"""Unit tests for `solvers.ad_scheduler` — deterministic via a seeded
`random.Random`, never asserting on a long-run statistical rate."""

from __future__ import annotations

import random

import pytest

from primitives import DomainRuleViolation
from solvers.ad_scheduler import (
    MUSIC_AD_CHANCE,
    STORY_AD_D100_THRESHOLD,
    roll_d100,
    should_play_interlude_after_music_track,
    should_play_interlude_after_story_part,
)


def test_music_ad_chance_constant_is_25_percent():
    assert MUSIC_AD_CHANCE == 0.25


def test_story_ad_threshold_constant_is_50():
    assert STORY_AD_D100_THRESHOLD == 50


class _FixedRandom(random.Random):
    """A `random.Random` stand-in returning fixed values, so the exact
    boundary condition is tested without relying on real randomness."""

    def __init__(self, *, random_value: float = 0.0, randint_value: int = 1) -> None:
        super().__init__()
        self._random_value = random_value
        self._randint_value = randint_value

    def random(self) -> float:
        return self._random_value

    def randint(self, a: int, b: int) -> int:
        return self._randint_value


def test_music_roll_triggers_just_below_threshold():
    assert should_play_interlude_after_music_track(_FixedRandom(random_value=0.24)) is True


def test_music_roll_does_not_trigger_at_or_above_threshold():
    assert should_play_interlude_after_music_track(_FixedRandom(random_value=0.25)) is False
    assert should_play_interlude_after_music_track(_FixedRandom(random_value=0.9)) is False


def test_roll_d100_is_in_range_with_real_rng():
    seeded = random.Random(12345)
    for _ in range(200):
        roll = roll_d100(seeded)
        assert 1 <= roll.value <= 100


def test_story_roll_triggers_on_1_to_50():
    assert should_play_interlude_after_story_part(_FixedRandom(randint_value=1)) is True
    assert should_play_interlude_after_story_part(_FixedRandom(randint_value=50)) is True


def test_story_roll_does_not_trigger_on_51_to_100():
    assert should_play_interlude_after_story_part(_FixedRandom(randint_value=51)) is False
    assert should_play_interlude_after_story_part(_FixedRandom(randint_value=100)) is False


def test_default_rng_is_used_when_none_given():
    # No crash, no DomainRuleViolation — the module-level `random` must be
    # a valid fallback, not just the injected-RNG path.
    for _ in range(50):
        should_play_interlude_after_music_track()
        should_play_interlude_after_story_part()


def test_roll_d100_never_produces_an_invalid_roll_even_with_pathological_rng():
    # A custom RNG that always returns 100 (the boundary) must still
    # construct a valid D100Roll, not raise.
    roll = roll_d100(_FixedRandom(randint_value=100))
    assert roll.value == 100


@pytest.mark.parametrize("bad_value", [0, 101, -5])
def test_fixed_random_feeding_an_out_of_range_randint_raises_via_d100roll(bad_value):
    # roll_d100 trusts its rng's randint contract; if something upstream
    # ever breaks that contract, D100Roll's own invariant still catches it
    # rather than silently accepting an impossible roll.
    with pytest.raises(DomainRuleViolation):
        roll_d100(_FixedRandom(randint_value=bad_value))
