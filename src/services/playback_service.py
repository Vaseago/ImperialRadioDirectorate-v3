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
    resolve_next_story_position,
    should_play_interlude_after_music_track,
    should_play_interlude_after_story_part,
)
from solvers.story_sequence import StorySeriesOrder

from .resume_state_store import ResumeCheckpointManager

__all__ = [
    "pick_random_track",
    "pick_interlude",
    "find_track_by_id",
    "MusicChannelService",
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
class StoriesChannelService:
    """Exactly one channel — plays every series in order, parts within a
    series always sequential, resume position persists across restarts."""

    config: Config
    checkpoint_manager: ResumeCheckpointManager

    def _series(self) -> tuple[StorySeries, ...]:
        return scan_story_dirs(self.config.stories_dirs)

    @staticmethod
    def _series_order(series: tuple[StorySeries, ...]) -> StorySeriesOrder:
        return tuple((s.series_id, tuple(p.part_number for p in s.parts)) for s in series)

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

    def current_position(self) -> tuple[StorySeriesId, StoryPartNumber] | None:
        """Where playback should resume: the saved checkpoint if it still
        points at real content, otherwise the very first position. `None`
        if no story content exists at all."""
        series = self._series()
        if not series:
            return None
        state = self.checkpoint_manager.load()
        if state.series_id:
            candidate = (StorySeriesId(state.series_id), StoryPartNumber(state.part_number))
            if self._track_for(series, *candidate) is not None:
                return candidate
        # No saved state, or it points at content that no longer exists
        # (e.g. a series folder was deleted) — start from the beginning.
        return resolve_next_story_position(self._series_order(series), None, None)

    def current_elapsed_seconds(self) -> float:
        return self.checkpoint_manager.load().elapsed_seconds

    def track_for_position(self, series_id: StorySeriesId, part_number: StoryPartNumber) -> Track | None:
        return self._track_for(self._series(), series_id, part_number)

    def advance(
        self, series_id: StorySeriesId, part_number: StoryPartNumber
    ) -> tuple[StorySeriesId, StoryPartNumber] | None:
        series = self._series()
        return resolve_next_story_position(self._series_order(series), series_id, part_number)

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
