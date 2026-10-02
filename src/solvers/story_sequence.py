"""Pure "what plays next on the Stories channel" walk.

Deliberately takes only identity data (`StorySeriesId` + an ordered tuple
of `StoryPartNumber`), never the real `adapters.library.StorySeries`/
`StoryPart` (which carry filesystem paths and Track data) — the layer DAG
forbids `solvers/` from importing `adapters/` at all, and this also keeps
the walk itself trivially unit-testable with fake series data, no
filesystem involved. `services/` is responsible for building this
structure from a real scan and mapping the result back to a real Track.

Series are expected pre-sorted (alphabetically, same order
`adapters.library.scan_story_dirs` already returns) and each series'
parts pre-sorted ascending — this module only walks the given order, it
never re-sorts.
"""

from __future__ import annotations

from primitives import StoryPartNumber, StorySeriesId

__all__ = ["StorySeriesOrder", "resolve_next_story_position"]

# (series_id, its parts in play order) for every series, in the order
# series themselves play.
StorySeriesOrder = tuple[tuple[StorySeriesId, tuple[StoryPartNumber, ...]], ...]


def resolve_next_story_position(
    series_order: StorySeriesOrder,
    current_series_id: StorySeriesId | None,
    current_part_number: StoryPartNumber | None,
) -> tuple[StorySeriesId, StoryPartNumber] | None:
    """The next (series, part) to play.

    * `current_series_id is None` — nothing has played yet (or the resume
      state was empty): returns the very first series' first part.
    * The current series still has parts left — returns the next part in
      that same series.
    * The current series just finished (or its id no longer exists in
      `series_order`, e.g. its folder was deleted) — returns the next
      series' first part, wrapping around to the first series once the
      last one finishes (the Stories channel loops, it doesn't stop).
    * `series_order` is empty — returns `None` (no story content exists).
    """
    if not series_order:
        return None

    if current_series_id is None:
        first_series_id, first_parts = series_order[0]
        return first_series_id, first_parts[0]

    index = next((i for i, (sid, _parts) in enumerate(series_order) if sid == current_series_id), None)

    if index is not None and current_part_number is not None:
        _sid, parts = series_order[index]
        try:
            position = parts.index(current_part_number)
        except ValueError:
            position = None
        if position is not None and position + 1 < len(parts):
            return current_series_id, parts[position + 1]

    # Current series exhausted, its id vanished, or no part was given —
    # advance to the next series, wrapping around to the first.
    next_index = 0 if index is None else (index + 1) % len(series_order)
    next_series_id, next_parts = series_order[next_index]
    return next_series_id, next_parts[0]
