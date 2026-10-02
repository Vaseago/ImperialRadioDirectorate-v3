"""Pure "what plays next on the Stories channel" logic.

Resolved 2026-10-01: Stories is tuned per-series, like Music's stations —
the listener picks which series to play — so there is no single global
walk through every series any more. What remains pure and testable:

* `resume_part_for_series` — where to resume *one* series the listener
  just tuned (or auto-advanced) into.
* `next_part_in_series` — the next part after the one that just finished,
  within that same series, or `None` once the series is exhausted.
* `pick_next_unlistened_series` — which series to auto-advance into once
  the current one finishes: the next one (in series order) that has not
  been heard through yet, searching forward and wrapping around so a
  full library pass is fair; `None` once nothing unlistened remains
  (auto-advance stops there — owner's own call, not a reset-and-loop).

Deliberately takes only identity data (`StorySeriesId` / `StoryPartNumber`
/ `SeriesResumeState`), never the real `adapters.library.StorySeries` —
the layer DAG forbids `solvers/` from importing `adapters/` at all, and
this keeps the walk trivially unit-testable with fake data, no filesystem
involved. `services/` builds this structure from a real scan and maps the
result back to a real `Track`.

Series/parts are expected pre-sorted (alphabetically for series, same
order `adapters.library.scan_story_dirs` already returns; ascending for
parts within a series) — this module only walks the given order, it never
re-sorts.
"""

from __future__ import annotations

from primitives import StoryPartNumber, StorySeriesId
from schema import SeriesResumeState

__all__ = ["SeriesParts", "resume_part_for_series", "next_part_in_series", "pick_next_unlistened_series"]

# One series' parts, in play order.
SeriesParts = tuple[StoryPartNumber, ...]


def resume_part_for_series(parts: SeriesParts, saved: SeriesResumeState | None) -> StoryPartNumber | None:
    """Where to resume this series: the first part if it has never been
    started, has already been listened all the way through, or its saved
    part number no longer exists in `parts` (e.g. a file was removed
    since) — otherwise the saved part number. `None` if the series has no
    parts at all."""
    if not parts:
        return None
    if saved is None or saved.listened:
        return parts[0]
    candidate = StoryPartNumber(saved.part_number)
    return candidate if candidate in parts else parts[0]


def next_part_in_series(parts: SeriesParts, current_part_number: StoryPartNumber) -> StoryPartNumber | None:
    """The part after `current_part_number` in `parts`, or `None` if it
    was the last one (the series just finished) or no longer exists in
    `parts` (e.g. a file was removed since — treated the same as
    "finished," not a crash)."""
    try:
        index = parts.index(current_part_number)
    except ValueError:
        return None
    return parts[index + 1] if index + 1 < len(parts) else None


def pick_next_unlistened_series(
    series_ids_in_order: tuple[StorySeriesId, ...],
    listened_series_ids: frozenset[str],
    *,
    start_after: StorySeriesId | None = None,
) -> StorySeriesId | None:
    """The next series in `series_ids_in_order` not present in
    `listened_series_ids`, searching forward from just after
    `start_after` and wrapping around once — so every series gets exactly
    one fair look per full pass. `None` once no unlistened series
    remains, which is where auto-advance stops (it does not reset the
    `listened` set and loop the whole library again)."""
    if not series_ids_in_order:
        return None

    start_index = 0
    if start_after is not None:
        found = next((i for i, sid in enumerate(series_ids_in_order) if sid == start_after), None)
        if found is not None:
            start_index = (found + 1) % len(series_ids_in_order)

    count = len(series_ids_in_order)
    for offset in range(count):
        candidate = series_ids_in_order[(start_index + offset) % count]
        if candidate.value not in listened_series_ids:
            return candidate
    return None
