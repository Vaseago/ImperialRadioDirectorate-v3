"""Unit tests for `adapters.library.scanner` against real, small synthetic
WAV files generated on the fly (silence) in isolated tmp dirs — same
real-file-not-mocked technique legacy IRD verified, re-derived for pytest.
"""

from __future__ import annotations

import struct
import wave
from pathlib import Path

from adapters.library import scan_library_dirs


def _write_silent_wav(path: Path, seconds: float = 1.0, sample_rate: int = 8000) -> None:
    n_frames = int(seconds * sample_rate)
    with wave.open(str(path), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(struct.pack("<%dh" % n_frames, *([0] * n_frames)))


def test_scan_extracts_duration_and_falls_back_to_filename_title(tmp_path):
    tagged_path = tmp_path / "some_track.wav"
    _write_silent_wav(tagged_path, seconds=2.0)

    untagged_path = tmp_path / "Weird_File Name-2.wav"
    _write_silent_wav(untagged_path, seconds=1.0)

    (tmp_path / "notes.txt").write_text("not an audio file", encoding="utf-8")

    tracks = scan_library_dirs((tmp_path,))
    assert len(tracks) == 2, "unsupported extension should be skipped, not scanned"

    by_path = {t.path: t for t in tracks}
    assert by_path[untagged_path].title == "Weird File Name 2"
    assert by_path[tagged_path].duration_seconds > 1.5


def test_track_id_stable_across_rescans_changes_on_rename(tmp_path):
    path = tmp_path / "song.wav"
    _write_silent_wav(path, seconds=1.0)

    first = scan_library_dirs((tmp_path,))
    second = scan_library_dirs((tmp_path,))
    assert first[0].id == second[0].id

    renamed = tmp_path / "renamed_song.wav"
    path.rename(renamed)
    third = scan_library_dirs((tmp_path,))
    assert third[0].id != first[0].id


def test_missing_library_dir_is_skipped_not_an_error(tmp_path):
    missing = tmp_path / "does_not_exist"
    assert scan_library_dirs((missing,)) == ()


def test_station_derived_from_top_level_folder_with_general_fallback(tmp_path):
    root_path = tmp_path / "loose_track.wav"
    _write_silent_wav(root_path)

    station_dir = tmp_path / "low_sec-transit"
    station_dir.mkdir()
    station_path = station_dir / "watchful.wav"
    _write_silent_wav(station_path)

    nested_dir = station_dir / "extra_nesting"
    nested_dir.mkdir()
    nested_path = nested_dir / "deep.wav"
    _write_silent_wav(nested_path)

    tracks = scan_library_dirs((tmp_path,))
    by_path = {t.path: t for t in tracks}

    assert by_path[root_path].station.value == "General"
    assert by_path[station_path].station.value == "Low Sec Transit"
    assert by_path[nested_path].station.value == "Low Sec Transit"  # top-level folder, however deep nested


def test_scan_multiple_dirs_merges_results(tmp_path):
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()
    _write_silent_wav(dir_a / "one.wav")
    _write_silent_wav(dir_b / "two.wav")

    tracks = scan_library_dirs((dir_a, dir_b))
    assert len(tracks) == 2
