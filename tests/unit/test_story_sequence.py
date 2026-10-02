"""Unit tests for `solvers.story_sequence` — pure per-series resume/advance
logic plus the next-unlistened-series pick, no filesystem, no `adapters/`
dependency at all (fake series/state data only)."""

from __future__ import annotations

from primitives import StoryPartNumber, StorySeriesId
from schema import SeriesResumeState
from solvers.story_sequence import next_part_in_series, pick_next_unlistened_series, resume_part_for_series

_P = StoryPartNumber
_S = StorySeriesId


def _parts(*numbers: int) -> tuple[StoryPartNumber, ...]:
    return tuple(_P(n) for n in numbers)


# -- resume_part_for_series ---------------------------------------------- #


def test_resume_part_for_series_returns_none_for_empty_parts():
    assert resume_part_for_series((), None) is None


def test_resume_part_for_series_starts_at_first_part_with_no_saved_state():
    assert resume_part_for_series(_parts(1, 2, 3), None) == _P(1)


def test_resume_part_for_series_resumes_at_the_saved_part():
    saved = SeriesResumeState(series_id="alien_invasion", part_number=2)
    assert resume_part_for_series(_parts(1, 2, 3), saved) == _P(2)


def test_resume_part_for_series_restarts_at_first_part_once_already_listened():
    saved = SeriesResumeState(series_id="alien_invasion", part_number=3, listened=True)
    assert resume_part_for_series(_parts(1, 2, 3), saved) == _P(1)


def test_resume_part_for_series_falls_back_to_first_part_when_saved_part_vanished():
    # Saved part 5 no longer exists in this series (e.g. a file was removed).
    saved = SeriesResumeState(series_id="alien_invasion", part_number=5)
    assert resume_part_for_series(_parts(1, 2, 3), saved) == _P(1)


# -- next_part_in_series --------------------------------------------------- #


def test_next_part_in_series_advances_to_the_next_part():
    assert next_part_in_series(_parts(1, 2, 3), _P(1)) == _P(2)


def test_next_part_in_series_returns_none_when_current_is_the_last():
    assert next_part_in_series(_parts(1, 2, 3), _P(3)) is None


def test_next_part_in_series_returns_none_when_current_part_not_found():
    assert next_part_in_series(_parts(1, 2), _P(99)) is None


def test_next_part_in_series_trusts_given_order_not_resorted():
    # The solver never re-sorts — it trusts the order it was handed.
    assert next_part_in_series(_parts(1, 10, 2), _P(1)) == _P(10)


# -- pick_next_unlistened_series -------------------------------------------- #


def test_pick_next_unlistened_series_returns_none_for_empty_order():
    assert pick_next_unlistened_series((), frozenset()) is None


def test_pick_next_unlistened_series_returns_first_when_nothing_listened():
    order = (_S("alien_invasion"), _S("zeta_front"))
    assert pick_next_unlistened_series(order, frozenset()) == _S("alien_invasion")


def test_pick_next_unlistened_series_skips_listened_ones():
    order = (_S("alien_invasion"), _S("zeta_front"))
    assert pick_next_unlistened_series(order, frozenset({"alien_invasion"})) == _S("zeta_front")


def test_pick_next_unlistened_series_searches_forward_from_start_after():
    order = (_S("alien_invasion"), _S("mid_front"), _S("zeta_front"))
    result = pick_next_unlistened_series(order, frozenset(), start_after=_S("alien_invasion"))
    assert result == _S("mid_front")


def test_pick_next_unlistened_series_wraps_around():
    order = (_S("alien_invasion"), _S("mid_front"), _S("zeta_front"))
    # Everything except alien_invasion is listened; starting after zeta_front
    # should wrap around and land back on alien_invasion.
    listened = frozenset({"mid_front", "zeta_front"})
    result = pick_next_unlistened_series(order, listened, start_after=_S("zeta_front"))
    assert result == _S("alien_invasion")


def test_pick_next_unlistened_series_returns_none_once_everything_listened():
    order = (_S("alien_invasion"), _S("zeta_front"))
    listened = frozenset({"alien_invasion", "zeta_front"})
    assert pick_next_unlistened_series(order, listened, start_after=_S("zeta_front")) is None


def test_pick_next_unlistened_series_unknown_start_after_starts_from_the_top():
    order = (_S("alien_invasion"), _S("zeta_front"))
    result = pick_next_unlistened_series(order, frozenset(), start_after=_S("deleted_series"))
    assert result == _S("alien_invasion")
