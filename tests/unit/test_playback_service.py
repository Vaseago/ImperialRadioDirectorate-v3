"""Unit tests for `services.playback_service` — real synthetic WAV files
on disk (same technique as the Phase 2 scanner tests), not mocks."""

from __future__ import annotations

import random
import struct
import wave
from pathlib import Path

from config import Config
from primitives import StationName, StoryPartNumber, StorySeriesId
from services.playback_service import MusicChannelService, StoriesChannelService, pick_interlude, pick_random_track
from services.resume_state_store import PlaybackResumeStateStore, ResumeCheckpointManager


def _write_silent_wav(path: Path, seconds: float = 0.5) -> None:
    n_frames = int(seconds * 8000)
    with wave.open(str(path), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(8000)
        f.writeframes(struct.pack("<%dh" % n_frames, *([0] * n_frames)))


def _make_config(tmp_path: Path) -> Config:
    music = tmp_path / "music"
    stories = tmp_path / "stories"
    interludes = tmp_path / "commercials_and_snippets"
    data = tmp_path / "data"
    for d in (music, stories, interludes, data):
        d.mkdir()
    return Config(base_dir=tmp_path, data_dir=data, music_dir=music, stories_dir=stories, interludes_dir=interludes)


def _checkpoint_manager(cfg: Config) -> ResumeCheckpointManager:
    return ResumeCheckpointManager(store=PlaybackResumeStateStore(path=cfg.resume_state_path))


# -- pick_random_track -------------------------------------------------- #


def test_pick_random_track_returns_none_for_empty_pool():
    assert pick_random_track(()) is None


def test_pick_random_track_avoids_immediate_repeat_when_alternatives_exist(tmp_path):
    cfg = _make_config(tmp_path)
    station_dir = cfg.music_dir / "Ambient"
    station_dir.mkdir()
    _write_silent_wav(station_dir / "one.wav")
    _write_silent_wav(station_dir / "two.wav")

    service = MusicChannelService(config=cfg)
    first = service.pick_track(StationName("Ambient"), rng=random.Random(1))
    second = service.pick_track(StationName("Ambient"), exclude=first.id, rng=random.Random(1))
    assert second.id != first.id


def test_pick_random_track_repeats_when_its_the_only_track(tmp_path):
    cfg = _make_config(tmp_path)
    station_dir = cfg.music_dir / "Ambient"
    station_dir.mkdir()
    _write_silent_wav(station_dir / "only.wav")

    service = MusicChannelService(config=cfg)
    first = service.pick_track(StationName("Ambient"))
    second = service.pick_track(StationName("Ambient"), exclude=first.id)
    assert second.id == first.id


# -- MusicChannelService -------------------------------------------------- #


def test_list_stations_is_alphabetical(tmp_path):
    cfg = _make_config(tmp_path)
    for name in ("Combat", "Ambient"):
        d = cfg.music_dir / name
        d.mkdir()
        _write_silent_wav(d / "track.wav")

    service = MusicChannelService(config=cfg)
    assert [s.value for s in service.list_stations()] == ["Ambient", "Combat"]


def test_pick_track_only_returns_tracks_from_the_requested_station(tmp_path):
    cfg = _make_config(tmp_path)
    (cfg.music_dir / "Ambient").mkdir()
    (cfg.music_dir / "Combat").mkdir()
    _write_silent_wav(cfg.music_dir / "Ambient" / "a.wav")
    _write_silent_wav(cfg.music_dir / "Combat" / "c.wav")

    service = MusicChannelService(config=cfg)
    track = service.pick_track(StationName("Combat"))
    assert track.station.value == "Combat"


# -- interludes (shared pool) ---------------------------------------------- #


def test_pick_interlude_returns_none_when_pool_empty(tmp_path):
    cfg = _make_config(tmp_path)
    assert pick_interlude(cfg) is None


def test_pick_interlude_returns_item_from_the_shared_pool(tmp_path):
    cfg = _make_config(tmp_path)
    _write_silent_wav(cfg.interludes_dir / "ad1.wav")
    track = pick_interlude(cfg)
    assert track is not None


# -- StoriesChannelService -------------------------------------------------- #


def _make_story_series(cfg: Config) -> None:
    for series_name, parts in (("alien_invasion", (1, 2, 3)), ("zeta_front", (1, 2))):
        series_dir = cfg.stories_dir / series_name
        series_dir.mkdir()
        for n in parts:
            _write_silent_wav(series_dir / f"{series_name}{n}.wav")


def test_list_series_is_alphabetical_with_no_resume_state(tmp_path):
    cfg = _make_config(tmp_path)
    _make_story_series(cfg)
    service = StoriesChannelService(config=cfg, checkpoint_manager=_checkpoint_manager(cfg))

    summaries = service.list_series()
    assert [s.series_id.value for s in summaries] == ["alien_invasion", "zeta_front"]
    assert [s.part_count for s in summaries] == [3, 2]
    assert all(not s.listened for s in summaries)
    assert all(s.resume_part_number == StoryPartNumber(1) for s in summaries)


def test_list_series_reflects_a_saved_resume_position(tmp_path):
    cfg = _make_config(tmp_path)
    _make_story_series(cfg)
    manager = _checkpoint_manager(cfg)
    manager.checkpoint(series_id=StorySeriesId("zeta_front"), part_number=StoryPartNumber(2), elapsed_seconds=42.0, force=True)

    service = StoriesChannelService(config=cfg, checkpoint_manager=manager)
    zeta = next(s for s in service.list_series() if s.series_id.value == "zeta_front")
    assert zeta.resume_part_number == StoryPartNumber(2)
    assert zeta.listened is False


def test_tune_in_starts_at_first_part_with_no_resume_state(tmp_path):
    cfg = _make_config(tmp_path)
    _make_story_series(cfg)
    service = StoriesChannelService(config=cfg, checkpoint_manager=_checkpoint_manager(cfg))

    result = service.tune_in(StorySeriesId("alien_invasion"))
    assert result == (StoryPartNumber(1), 0.0)


def test_tune_in_resumes_at_the_saved_checkpoint(tmp_path):
    cfg = _make_config(tmp_path)
    _make_story_series(cfg)
    manager = _checkpoint_manager(cfg)
    manager.checkpoint(series_id=StorySeriesId("zeta_front"), part_number=StoryPartNumber(2), elapsed_seconds=42.0, force=True)

    service = StoriesChannelService(config=cfg, checkpoint_manager=manager)
    assert service.tune_in(StorySeriesId("zeta_front")) == (StoryPartNumber(2), 42.0)


def test_tune_in_restarts_fresh_once_already_listened(tmp_path):
    cfg = _make_config(tmp_path)
    _make_story_series(cfg)
    manager = _checkpoint_manager(cfg)
    manager.checkpoint(series_id=StorySeriesId("zeta_front"), part_number=StoryPartNumber(2), elapsed_seconds=42.0, force=True)
    manager.mark_listened(StorySeriesId("zeta_front"), final_part_number=StoryPartNumber(2))

    service = StoriesChannelService(config=cfg, checkpoint_manager=manager)
    assert service.tune_in(StorySeriesId("zeta_front")) == (StoryPartNumber(1), 0.0)


def test_tune_in_returns_none_for_a_nonexistent_series(tmp_path):
    cfg = _make_config(tmp_path)
    _make_story_series(cfg)
    service = StoriesChannelService(config=cfg, checkpoint_manager=_checkpoint_manager(cfg))
    assert service.tune_in(StorySeriesId("ghost_series")) is None


def test_advance_moves_to_next_part_within_the_same_series(tmp_path):
    cfg = _make_config(tmp_path)
    _make_story_series(cfg)
    service = StoriesChannelService(config=cfg, checkpoint_manager=_checkpoint_manager(cfg))

    result = service.advance(StorySeriesId("alien_invasion"), StoryPartNumber(1))
    assert result.next_position == (StorySeriesId("alien_invasion"), StoryPartNumber(2))
    assert result.series_completed is False


def test_advance_past_the_last_part_marks_listened_and_moves_to_next_unlistened_series(tmp_path):
    cfg = _make_config(tmp_path)
    _make_story_series(cfg)  # alien_invasion (3 parts), zeta_front (2 parts)
    manager = _checkpoint_manager(cfg)
    service = StoriesChannelService(config=cfg, checkpoint_manager=manager)

    result = service.advance(StorySeriesId("alien_invasion"), StoryPartNumber(3))
    assert result.next_position == (StorySeriesId("zeta_front"), StoryPartNumber(1))
    assert result.series_completed is True
    assert manager.load().for_series("alien_invasion").listened is True


def test_advance_past_the_last_part_resumes_a_partially_heard_unlistened_series(tmp_path):
    cfg = _make_config(tmp_path)
    _make_story_series(cfg)
    manager = _checkpoint_manager(cfg)
    manager.checkpoint(
        series_id=StorySeriesId("zeta_front"), part_number=StoryPartNumber(2), elapsed_seconds=5.0, force=True
    )
    service = StoriesChannelService(config=cfg, checkpoint_manager=manager)

    result = service.advance(StorySeriesId("alien_invasion"), StoryPartNumber(3))
    assert result.next_position == (StorySeriesId("zeta_front"), StoryPartNumber(2))


def test_advance_stops_once_every_series_has_been_listened(tmp_path):
    cfg = _make_config(tmp_path)
    _make_story_series(cfg)
    manager = _checkpoint_manager(cfg)
    manager.mark_listened(StorySeriesId("zeta_front"), final_part_number=StoryPartNumber(2))
    service = StoriesChannelService(config=cfg, checkpoint_manager=manager)

    result = service.advance(StorySeriesId("alien_invasion"), StoryPartNumber(3))
    assert result.next_position is None
    assert result.series_completed is True


def test_track_for_position_returns_the_real_track(tmp_path):
    cfg = _make_config(tmp_path)
    _make_story_series(cfg)
    service = StoriesChannelService(config=cfg, checkpoint_manager=_checkpoint_manager(cfg))

    track = service.track_for_position(StorySeriesId("alien_invasion"), StoryPartNumber(1))
    assert track is not None
    assert track.path.name == "alien_invasion1.wav"


def test_checkpoint_persists_through_the_service(tmp_path):
    cfg = _make_config(tmp_path)
    _make_story_series(cfg)
    manager = _checkpoint_manager(cfg)
    service = StoriesChannelService(config=cfg, checkpoint_manager=manager)

    service.checkpoint(StorySeriesId("alien_invasion"), StoryPartNumber(3), 12.0, force=True)
    assert service.tune_in(StorySeriesId("alien_invasion")) == (StoryPartNumber(3), 12.0)
