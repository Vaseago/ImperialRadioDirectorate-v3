"""Unit tests for `schema.playback_resume_state` — every story series' own
resume position (the one piece of real persisted state IRD v3 needs)."""

from __future__ import annotations

from schema import PlaybackResumeState, SeriesResumeState


def test_default_state_means_nothing_played_yet():
    state = PlaybackResumeState()
    assert state.series == ()
    assert state.for_series("alien_invasion") is None
    assert state.listened_series_ids() == frozenset()


def test_series_to_dict_from_dict_roundtrip():
    series_state = SeriesResumeState(
        series_id="alien_invasion",
        part_number=2,
        elapsed_seconds=612.5,
        listened=False,
        last_updated="2026-10-01T00:00:00Z",
    )
    restored = SeriesResumeState.from_dict(series_state.to_dict())
    assert restored == series_state


def test_state_to_dict_from_dict_roundtrip_with_multiple_series():
    state = PlaybackResumeState(
        series=(
            SeriesResumeState(series_id="alien_invasion", part_number=2, elapsed_seconds=10.0),
            SeriesResumeState(series_id="zeta_front", part_number=1, elapsed_seconds=0.0, listened=True),
        )
    )
    restored = PlaybackResumeState.from_dict(state.to_dict())
    assert restored == state


def test_for_series_finds_the_matching_entry():
    state = PlaybackResumeState(
        series=(
            SeriesResumeState(series_id="alien_invasion", part_number=2),
            SeriesResumeState(series_id="zeta_front", part_number=1),
        )
    )
    assert state.for_series("zeta_front").part_number == 1
    assert state.for_series("nonexistent") is None


def test_listened_series_ids_only_includes_listened_entries():
    state = PlaybackResumeState(
        series=(
            SeriesResumeState(series_id="alien_invasion", listened=True),
            SeriesResumeState(series_id="zeta_front", listened=False),
        )
    )
    assert state.listened_series_ids() == frozenset({"alien_invasion"})


def test_with_series_replaces_an_existing_entry_not_appends():
    state = PlaybackResumeState(series=(SeriesResumeState(series_id="alien_invasion", part_number=1),))
    updated = state.with_series(SeriesResumeState(series_id="alien_invasion", part_number=3))
    assert len(updated.series) == 1
    assert updated.for_series("alien_invasion").part_number == 3


def test_with_series_appends_a_new_entry():
    state = PlaybackResumeState(series=(SeriesResumeState(series_id="alien_invasion", part_number=1),))
    updated = state.with_series(SeriesResumeState(series_id="zeta_front", part_number=1))
    assert len(updated.series) == 2
    assert updated.for_series("zeta_front") is not None


def test_from_dict_non_dict_input_falls_back_to_default():
    assert PlaybackResumeState.from_dict(None) == PlaybackResumeState()
    assert PlaybackResumeState.from_dict("not a dict") == PlaybackResumeState()


def test_from_dict_non_list_series_falls_back_to_default():
    assert PlaybackResumeState.from_dict({"series": "not a list"}) == PlaybackResumeState()


def test_from_dict_skips_entries_with_no_series_id():
    state = PlaybackResumeState.from_dict({"series": [{"part_number": 2}, {"series_id": "zeta_front"}]})
    assert len(state.series) == 1
    assert state.for_series("zeta_front") is not None


def test_series_from_dict_clamps_invalid_part_number_to_one():
    assert SeriesResumeState.from_dict({"series_id": "x", "part_number": 0}).part_number == 1
    assert SeriesResumeState.from_dict({"series_id": "x", "part_number": -5}).part_number == 1
    assert SeriesResumeState.from_dict({"series_id": "x", "part_number": "not an int"}).part_number == 1


def test_series_from_dict_clamps_negative_elapsed_seconds_to_zero():
    assert SeriesResumeState.from_dict({"series_id": "x", "elapsed_seconds": -10.0}).elapsed_seconds == 0.0


def test_series_from_dict_missing_fields_use_defaults():
    state = SeriesResumeState.from_dict({"series_id": "alien_invasion"})
    assert state.series_id == "alien_invasion"
    assert state.part_number == 1
    assert state.elapsed_seconds == 0.0
    assert state.listened is False
    assert state.last_updated == ""
