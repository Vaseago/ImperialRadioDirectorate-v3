"""Unit tests for `solvers.story_sequence` — pure walk, no filesystem, no
`adapters/` dependency at all (fake series data only)."""

from __future__ import annotations

from primitives import StoryPartNumber, StorySeriesId
from solvers.story_sequence import resolve_next_story_position

_P = StoryPartNumber
_S = StorySeriesId


def _order(*series: tuple[str, tuple[int, ...]]):
    return tuple((_S(sid), tuple(_P(n) for n in parts)) for sid, parts in series)


def test_empty_series_order_returns_none():
    assert resolve_next_story_position((), None, None) is None


def test_no_current_position_starts_at_first_series_first_part():
    order = _order(("alien_invasion", (1, 2, 3)), ("zeta_front", (1, 2)))
    result = resolve_next_story_position(order, None, None)
    assert result == (_S("alien_invasion"), _P(1))


def test_advances_to_next_part_within_same_series():
    order = _order(("alien_invasion", (1, 2, 3)))
    result = resolve_next_story_position(order, _S("alien_invasion"), _P(1))
    assert result == (_S("alien_invasion"), _P(2))


def test_advances_to_next_series_when_current_series_exhausted():
    order = _order(("alien_invasion", (1, 2)), ("zeta_front", (1, 2)))
    result = resolve_next_story_position(order, _S("alien_invasion"), _P(2))
    assert result == (_S("zeta_front"), _P(1))


def test_wraps_around_to_first_series_after_the_last_one_finishes():
    order = _order(("alien_invasion", (1, 2)), ("zeta_front", (1, 2)))
    result = resolve_next_story_position(order, _S("zeta_front"), _P(2))
    assert result == (_S("alien_invasion"), _P(1))


def test_single_series_wraps_to_its_own_start():
    order = _order(("alien_invasion", (1, 2)))
    result = resolve_next_story_position(order, _S("alien_invasion"), _P(2))
    assert result == (_S("alien_invasion"), _P(1))


def test_vanished_series_id_restarts_at_next_series_after_its_old_position():
    # The current series was deleted (not in series_order any more) —
    # falls through to "advance" semantics, landing on the first series.
    order = _order(("zeta_front", (1, 2)))
    result = resolve_next_story_position(order, _S("deleted_series"), _P(5))
    assert result == (_S("zeta_front"), _P(1))


def test_part_number_not_found_in_current_series_falls_through_to_next_series():
    # A stored resume part number that no longer exists in that series
    # (e.g. a file was removed) — treated as "series exhausted," not a crash.
    order = _order(("alien_invasion", (1, 2)), ("zeta_front", (1,)))
    result = resolve_next_story_position(order, _S("alien_invasion"), _P(99))
    assert result == (_S("zeta_front"), _P(1))


def test_numeric_ordering_is_trusted_as_given_not_resorted():
    # The solver never re-sorts — it trusts the order it was handed.
    order = _order(("alien_invasion", (1, 10, 2)))
    result = resolve_next_story_position(order, _S("alien_invasion"), _P(1))
    assert result == (_S("alien_invasion"), _P(10))
