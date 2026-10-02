"""Unit tests for `primitives.ids` — each type's invariant is enforced at
construction, not left to a runtime assertion elsewhere."""

from __future__ import annotations

import pytest

from primitives import D100Roll, DomainRuleViolation, StationName, StorySeriesId, StoryPartNumber, TrackId


def test_track_id_rejects_empty():
    TrackId("abc123")  # valid, no raise
    with pytest.raises(DomainRuleViolation):
        TrackId("")


def test_station_name_rejects_blank():
    StationName("Ambient")  # valid, no raise
    with pytest.raises(DomainRuleViolation):
        StationName("")
    with pytest.raises(DomainRuleViolation):
        StationName("   ")


def test_story_series_id_rejects_blank():
    StorySeriesId("alien_invasion")  # valid, no raise
    with pytest.raises(DomainRuleViolation):
        StorySeriesId("")


def test_story_part_number_must_be_positive():
    StoryPartNumber(1)  # valid, no raise
    with pytest.raises(DomainRuleViolation):
        StoryPartNumber(0)
    with pytest.raises(DomainRuleViolation):
        StoryPartNumber(-1)


def test_d100_roll_must_be_in_range():
    D100Roll(1)
    D100Roll(100)
    with pytest.raises(DomainRuleViolation):
        D100Roll(0)
    with pytest.raises(DomainRuleViolation):
        D100Roll(101)


def test_d100_roll_triggers_boundary():
    # threshold=50: 1-50 triggers, 51-100 doesn't — the owner's own
    # literal framing ("roll it 1-50 and 51-100").
    assert D100Roll(1).triggers(50) is True
    assert D100Roll(50).triggers(50) is True
    assert D100Roll(51).triggers(50) is False
    assert D100Roll(100).triggers(50) is False


def test_d100_roll_triggers_rejects_invalid_threshold():
    with pytest.raises(DomainRuleViolation):
        D100Roll(1).triggers(0)
    with pytest.raises(DomainRuleViolation):
        D100Roll(1).triggers(101)
