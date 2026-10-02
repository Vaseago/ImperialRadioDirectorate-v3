"""Unit tests for `services.resume_state_store` — typed persistence plus
the throttled-checkpoint policy on top of it."""

from __future__ import annotations

from primitives import StoryPartNumber, StorySeriesId
from schema import PlaybackResumeState
from services.resume_state_store import PlaybackResumeStateStore, ResumeCheckpointManager


def test_store_load_returns_default_when_file_missing(tmp_path):
    store = PlaybackResumeStateStore(path=tmp_path / "resume.json")
    state = store.load()
    assert state.series_id == ""
    assert state.part_number == 1


def test_store_save_then_load_roundtrips(tmp_path):
    store = PlaybackResumeStateStore(path=tmp_path / "resume.json")
    store.save(PlaybackResumeState(series_id="alien_invasion", part_number=2, elapsed_seconds=10.5))
    loaded = store.load()
    assert loaded.series_id == "alien_invasion"
    assert loaded.part_number == 2
    assert loaded.elapsed_seconds == 10.5


def test_checkpoint_manager_first_call_always_writes(tmp_path):
    manager = ResumeCheckpointManager(store=PlaybackResumeStateStore(path=tmp_path / "resume.json"))
    wrote = manager.checkpoint(series_id=StorySeriesId("alien_invasion"), part_number=StoryPartNumber(1), elapsed_seconds=0.0)
    assert wrote is True
    assert manager.load().series_id == "alien_invasion"


def test_checkpoint_manager_throttles_rapid_calls(tmp_path, monkeypatch):
    fake_clock = [100.0]
    monkeypatch.setattr("services.resume_state_store.time.monotonic", lambda: fake_clock[0])

    manager = ResumeCheckpointManager(
        store=PlaybackResumeStateStore(path=tmp_path / "resume.json"), min_interval_seconds=15.0
    )
    assert manager.checkpoint(series_id=StorySeriesId("s"), part_number=StoryPartNumber(1), elapsed_seconds=0.0) is True

    fake_clock[0] += 5.0  # only 5s later — inside the 15s throttle window
    assert manager.checkpoint(series_id=StorySeriesId("s"), part_number=StoryPartNumber(1), elapsed_seconds=5.0) is False
    # the throttled call must not have overwritten the stored elapsed time
    assert manager.load().elapsed_seconds == 0.0


def test_checkpoint_manager_writes_again_after_interval_elapses(tmp_path, monkeypatch):
    fake_clock = [100.0]
    monkeypatch.setattr("services.resume_state_store.time.monotonic", lambda: fake_clock[0])

    manager = ResumeCheckpointManager(
        store=PlaybackResumeStateStore(path=tmp_path / "resume.json"), min_interval_seconds=15.0
    )
    manager.checkpoint(series_id=StorySeriesId("s"), part_number=StoryPartNumber(1), elapsed_seconds=0.0)

    fake_clock[0] += 20.0  # past the throttle window
    wrote = manager.checkpoint(series_id=StorySeriesId("s"), part_number=StoryPartNumber(1), elapsed_seconds=20.0)
    assert wrote is True
    assert manager.load().elapsed_seconds == 20.0


def test_checkpoint_manager_force_bypasses_throttle(tmp_path, monkeypatch):
    fake_clock = [100.0]
    monkeypatch.setattr("services.resume_state_store.time.monotonic", lambda: fake_clock[0])

    manager = ResumeCheckpointManager(
        store=PlaybackResumeStateStore(path=tmp_path / "resume.json"), min_interval_seconds=15.0
    )
    manager.checkpoint(series_id=StorySeriesId("s"), part_number=StoryPartNumber(1), elapsed_seconds=0.0)

    fake_clock[0] += 1.0  # well inside the throttle window
    wrote = manager.checkpoint(
        series_id=StorySeriesId("s"), part_number=StoryPartNumber(1), elapsed_seconds=1.0, force=True
    )
    assert wrote is True
    assert manager.load().elapsed_seconds == 1.0
