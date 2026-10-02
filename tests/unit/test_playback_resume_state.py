"""Unit tests for `schema.playback_resume_state.PlaybackResumeState` — the
one piece of real persisted state IRD v3 needs (Stories-channel resume
position)."""

from __future__ import annotations

from schema import PlaybackResumeState


def test_default_state_means_nothing_played_yet():
    state = PlaybackResumeState()
    assert state.series_id == ""
    assert state.part_number == 1
    assert state.elapsed_seconds == 0.0


def test_to_dict_from_dict_roundtrip():
    state = PlaybackResumeState(
        series_id="alien_invasion", part_number=2, elapsed_seconds=612.5, last_updated="2026-10-01T00:00:00Z"
    )
    restored = PlaybackResumeState.from_dict(state.to_dict())
    assert restored == state


def test_from_dict_non_dict_input_falls_back_to_default():
    assert PlaybackResumeState.from_dict(None) == PlaybackResumeState()
    assert PlaybackResumeState.from_dict("not a dict") == PlaybackResumeState()


def test_from_dict_clamps_invalid_part_number_to_one():
    assert PlaybackResumeState.from_dict({"part_number": 0}).part_number == 1
    assert PlaybackResumeState.from_dict({"part_number": -5}).part_number == 1
    assert PlaybackResumeState.from_dict({"part_number": "not an int"}).part_number == 1


def test_from_dict_clamps_negative_elapsed_seconds_to_zero():
    assert PlaybackResumeState.from_dict({"elapsed_seconds": -10.0}).elapsed_seconds == 0.0


def test_from_dict_missing_fields_use_defaults():
    state = PlaybackResumeState.from_dict({"series_id": "alien_invasion"})
    assert state.series_id == "alien_invasion"
    assert state.part_number == 1
    assert state.elapsed_seconds == 0.0
    assert state.last_updated == ""
