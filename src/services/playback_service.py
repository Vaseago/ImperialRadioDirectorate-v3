"""Orchestrates `adapters.library` scans + `solvers` scheduling into the
two channel-level services `web/` (Phase 5) will actually call: a router
never scans the filesystem or rolls dice itself.

Both channels draw their interludes from the exact same
`commercials_and_snippets/` pool via the shared `pick_interlude()` — no
separate "story interludes" vs "music interludes" distinction, confirmed
directly with the owner.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from adapters.library import StorySeries, Track, scan_library_dirs, scan_story_dirs
from config import Config
from primitives import StationName, StoryPartNumber, StorySeriesId, TrackId
from solvers import (
    next_part_in_series,
    pick_next_unlistened_series,
    resume_part_for_series,
    should_play_interlude_after_music_track,
    should_play_interlude_after_story_part,
)
from solvers.story_sequence import SeriesParts

from .resume_state_store import ResumeCheckpointManager

__all__ = [
    "pick_random_track",
    "pick_interlude",
    "find_track_by_id",
    "MusicChannelService",
    "StorySeriesSummary",
    "StoriesAdvanceResult",
    "StoriesChannelService",
]


def pick_random_track(
    tracks: tuple[Track, ...], *, exclude: TrackId | None = None, rng: random.Random | None = None
) -> Track | None:
    """One random track from `tracks`, avoiding `exclude`'s id when a
    different candidate exists — legacy IRD's own "avoid immediately
    repeating the last pick" rule, carried forward as a verified-good UX
    fact. Falls back to repeating it if it's the only track available.
    Returns `None` for an empty pool."""
    if not tracks:
        return None
    source = rng if rng is not None else random
    candidates = [t for t in tracks if exclude is None or t.id != exclude]
    pool = candidates or list(tracks)
    return source.choice(pool)


def pick_interlude(
    config: Config, *, exclude: TrackId | None = None, rng: random.Random | None = None
) -> Track | None:
    """A random item from the shared commercials/snippets pool, or `None`
    if it's empty — the ad-break logic simply never fires on an empty
    pool, same as legacy IRD's own behavior."""
    pool = scan_library_dirs(config.interludes_dirs)
    return pick_random_track(pool, exclude=exclude, rng=rng)


def find_track_by_id(config: Config, track_id: TrackId) -> Track | None:
    """The one real track behind `track_id`, searching every pool
    (music, interludes, story parts) — the streaming endpoint (Phase 5)
    serves any track by id regardless of which pool it came from, so it
    needs this cross-pool lookup rather than three separate endpoints."""
    for track in (*scan_library_dirs(config.music_dirs), *scan_library_dirs(config.interludes_dirs)):
        if track.id == track_id:
            return track
    for series in scan_story_dirs(config.stories_dirs):
        for part in series.parts:
            if part.track.id == track_id:
                return part.track
    return None


@dataclass(frozen=True, slots=True)
class MusicChannelService:
    config: Config

    def _all_tracks(self) -> tuple[Track, ...]:
        return scan_library_dirs(self.config.music_dirs)

    def list_stations(self) -> tuple[StationName, ...]:
        """Every distinct station, alphabetically — folder-per-station,
        same model as legacy."""
        seen: dict[str, StationName] = {}
        for track in self._all_tracks():
            seen.setdefault(track.station.value, track.station)
        return tuple(seen[name] for name in sorted(seen))

    def pick_track(
        self, station: StationName, *, exclude: TrackId | None = None, rng: random.Random | None = None
    ) -> Track | None:
        tracks = tuple(t for t in self._all_tracks() if t.station == station)
        return pick_random_track(tracks, exclude=exclude, rng=rng)

    def should_play_interlude(self, *, rng: random.Random | None = None) -> bool:
        return should_play_interlude_after_music_track(rng)


@dataclass(frozen=True, slots=True)
class StorySeriesSummary:
    """One series' listing entry for the tuner — enough for a picker to
    show what's available and whether it's already been heard."""

    series_id: StorySeriesId
    part_count: int
    listened: bool
    resume_part_number: StoryPartNumber


@dataclass(frozen=True, slots=True)
class StoriesAdvanceResult:
    """The outcome of finishing one story part. `next_position` is `None`
    only when the just-finished series completed the full library (every
    series now listened) — auto-advance stops there rather than resetting
    and looping (owner's own call, 2026-10-01)."""

    next_position: tuple[StorySeriesId, StoryPartNumber] | None
    series_completed: bool


@dataclass(frozen=True, slots=True)
class StoriesChannelService:
    """Stories is tuned per-series, like Music's stations — the listener
    picks which series to play (`list_series`/`tune_in`) — except each
    series remembers its own resume position independently, and finishing
    one auto-advances to the next series that hasn't been heard yet
    (`advance`), stopping once every series has been heard through at
    least once."""

    config: Config
    checkpoint_manager: ResumeCheckpointManager

    def _series(self) -> tuple[StorySeries, ...]:
        return scan_story_dirs(self.config.stories_dirs)

    @staticmethod
    def _parts_of(series: tuple[StorySeries, ...], series_id: StorySeriesId) -> SeriesParts:
        for one_series in series:
            if one_series.series_id == series_id:
                return tuple(p.part_number for p in one_series.parts)
        return ()

    @staticmethod
    def _track_for(
        series: tuple[StorySeries, ...], series_id: StorySeriesId, part_number: StoryPartNumber
    ) -> Track | None:
        for one_series in series:
            if one_series.series_id != series_id:
                continue
            for part in one_series.parts:
                if part.part_number == part_number:
                    return part.track
        return None

    def list_series(self) -> tuple[StorySeriesSummary, ...]:
        """Every story series, alphabetically — same order they're scanned
        in — with each one's part count, listened flag, and where tuning
        into it would resume."""
        series = self._series()
        state = self.checkpoint_manager.load()
        summaries: list[StorySeriesSummary] = []
        for one_series in series:
            parts = tuple(p.part_number for p in one_series.parts)
            saved = state.for_series(one_series.series_id.value)
            resume_part = resume_part_for_series(parts, saved) or parts[0]
            summaries.append(
                StorySeriesSummary(
                    series_id=one_series.series_id,
                    part_count=len(parts),
                    listened=saved.listened if saved is not None else False,
                    resume_part_number=resume_part,
                )
            )
        return tuple(summaries)

    def tune_in(self, series_id: StorySeriesId) -> tuple[StoryPartNumber, float] | None:
        """Where to resume `series_id`: its own saved position (elapsed
        time included), or the first part at 0:00 if it's never been
        started or has already been listened all the way through. `None`
        if the series doesn't exist."""
        series = self._series()
        parts = self._parts_of(series, series_id)
        if not parts:
            return None
        state = self.checkpoint_manager.load()
        saved = state.for_series(series_id.value)
        resume_part = resume_part_for_series(parts, saved)
        if resume_part is None:
            return None
        resumes_saved_position = saved is not None and not saved.listened and saved.part_number == resume_part.value
        elapsed_seconds = saved.elapsed_seconds if resumes_saved_position else 0.0
        return resume_part, elapsed_seconds

    def track_for_position(self, series_id: StorySeriesId, part_number: StoryPartNumber) -> Track | None:
        return self._track_for(self._series(), series_id, part_number)

    def advance(self, series_id: StorySeriesId, part_number: StoryPartNumber) -> StoriesAdvanceResult:
        """The part that just finished was `(series_id, part_number)`.
        Stays within the same series if it has parts left; otherwise marks
        it listened (an immediate, unthrottled write) and auto-advances to
        the next series that hasn't been heard yet."""
        series = self._series()
        parts = self._parts_of(series, series_id)
        next_part = next_part_in_series(parts, part_number) if parts else None
        if next_part is not None:
            return StoriesAdvanceResult(next_position=(series_id, next_part), series_completed=False)

        self.checkpoint_manager.mark_listened(series_id, final_part_number=part_number)

        state = self.checkpoint_manager.load()
        order = tuple(s.series_id for s in series)
        next_series_id = pick_next_unlistened_series(order, state.listened_series_ids(), start_after=series_id)
        if next_series_id is None:
            return StoriesAdvanceResult(next_position=None, series_completed=True)

        next_parts = self._parts_of(series, next_series_id)
        next_resume_part = resume_part_for_series(next_parts, state.for_series(next_series_id.value))
        if next_resume_part is None:
            return StoriesAdvanceResult(next_position=None, series_completed=True)
        return StoriesAdvanceResult(next_position=(next_series_id, next_resume_part), series_completed=True)

    def should_play_interlude(self, *, rng: random.Random | None = None) -> bool:
        return should_play_interlude_after_story_part(rng)

    def checkpoint(
        self,
        series_id: StorySeriesId,
        part_number: StoryPartNumber,
        elapsed_seconds: float,
        *,
        force: bool = False,
    ) -> bool:
        return self.checkpoint_manager.checkpoint(
            series_id=series_id, part_number=part_number, elapsed_seconds=elapsed_seconds, force=force
        )
