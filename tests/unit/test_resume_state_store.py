"""Unit tests for `services.resume_state_store` — typed persistence plus
the per-series throttled-checkpoint policy on top of it."""

from __future__ import annotations

from primitives import StoryPartNumber, StorySeriesId
from schema import PlaybackResumeState, SeriesResumeState
from services.resume_state_store import PlaybackResumeStateStore, ResumeCheckpointManager


def test_store_load_returns_default_when_file_missing(tmp_path):
    store = PlaybackResumeStateStore(path=tmp_path / "resume.json")
    assert store.load() == PlaybackResumeState()


def test_store_save_then_load_roundtrips(tmp_path):
    store = PlaybackResumeStateStore(path=tmp_path / "resume.json")
    resumed = SeriesResumeState(series_id="alien_invasion", part_number=2, elapsed_seconds=10.5)
    store.save(PlaybackResumeState(series=(resumed,)))
    loaded = store.load()
    series_state = loaded.for_series("alien_invasion")
    assert series_state.part_number == 2
    assert series_state.elapsed_seconds == 10.5


def test_checkpoint_manager_first_call_always_writes(tmp_path):
    manager = ResumeCheckpointManager(store=PlaybackResumeStateStore(path=tmp_path / "resume.json"))
    wrote = manager.checkpoint(
        series_id=StorySeriesId("alien_invasion"),
        part_number=StoryPartNumber(1),
        elapsed_seconds=0.0,
    )
    assert wrote is True
    assert manager.load().for_series("alien_invasion").part_number == 1


def test_checkpoint_manager_throttles_rapid_calls(tmp_path, monkeypatch):
    fake_clock = [100.0]
    monkeypatch.setattr("services.resume_state_store.time.monotonic", lambda: fake_clock[0])

    manager = ResumeCheckpointManager(
        store=PlaybackResumeStateStore(path=tmp_path / "resume.json"), min_interval_seconds=15.0
    )
    assert manager.checkpoint(series_id=StorySeriesId("s"), part_number=StoryPartNumber(1), elapsed_seconds=0.0) is True

    fake_clock[0] += 5.0  # only 5s later — inside the 15s throttle window
    assert manager.checkpoint(
        series_id=StorySeriesId("s"),
        part_number=StoryPartNumber(1),
        elapsed_seconds=5.0,
    ) is False
    # the throttled call must not have overwritten the stored elapsed time
    assert manager.load().for_series("s").elapsed_seconds == 0.0


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
    assert manager.load().for_series("s").elapsed_seconds == 20.0


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
    assert manager.load().for_series("s").elapsed_seconds == 1.0


def test_checkpoint_manager_throttles_each_series_independently(tmp_path, monkeypatch):
    fake_clock = [100.0]
    monkeypatch.setattr("services.resume_state_store.time.monotonic", lambda: fake_clock[0])

    manager = ResumeCheckpointManager(
        store=PlaybackResumeStateStore(path=tmp_path / "resume.json"), min_interval_seconds=15.0
    )
    manager.checkpoint(series_id=StorySeriesId("alien_invasion"), part_number=StoryPartNumber(1), elapsed_seconds=0.0)

    fake_clock[0] += 5.0  # inside alien_invasion's own throttle window
    # A different series' first-ever checkpoint must still write immediately.
    wrote = manager.checkpoint(
        series_id=StorySeriesId("zeta_front"),
        part_number=StoryPartNumber(1),
        elapsed_seconds=0.0,
    )
    assert wrote is True


def test_mark_listened_always_writes_immediately_bypassing_throttle(tmp_path, monkeypatch):
    fake_clock = [100.0]
    monkeypatch.setattr("services.resume_state_store.time.monotonic", lambda: fake_clock[0])

    manager = ResumeCheckpointManager(
        store=PlaybackResumeStateStore(path=tmp_path / "resume.json"), min_interval_seconds=15.0
    )
    manager.checkpoint(series_id=StorySeriesId("s"), part_number=StoryPartNumber(1), elapsed_seconds=0.0)

    fake_clock[0] += 1.0  # well inside the throttle window — mark_listened ignores it entirely
    manager.mark_listened(StorySeriesId("s"), final_part_number=StoryPartNumber(3))

    saved = manager.load().for_series("s")
    assert saved.listened is True
    assert saved.part_number == 3


def test_mark_listened_preserves_the_last_checkpointed_elapsed_seconds(tmp_path):
    manager = ResumeCheckpointManager(store=PlaybackResumeStateStore(path=tmp_path / "resume.json"))
    manager.checkpoint(series_id=StorySeriesId("s"), part_number=StoryPartNumber(3), elapsed_seconds=612.5, force=True)

    manager.mark_listened(StorySeriesId("s"), final_part_number=StoryPartNumber(3))

    assert manager.load().for_series("s").elapsed_seconds == 612.5


def test_mark_listened_on_a_series_with_no_prior_checkpoint_defaults_elapsed_to_zero(tmp_path):
    manager = ResumeCheckpointManager(store=PlaybackResumeStateStore(path=tmp_path / "resume.json"))
    manager.mark_listened(StorySeriesId("s"), final_part_number=StoryPartNumber(1))
    saved = manager.load().for_series("s")
    assert saved.listened is True
    assert saved.elapsed_seconds == 0.0
