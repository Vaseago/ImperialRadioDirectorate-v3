"""Unit tests for `adapters.library.story_scanner` — series-folder
grouping and numeric part ordering."""

from __future__ import annotations

import struct
import wave
from pathlib import Path

from adapters.library import scan_story_dirs


def _write_silent_wav(path: Path, seconds: float = 0.5, sample_rate: int = 8000) -> None:
    n_frames = int(seconds * sample_rate)
    with wave.open(str(path), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(struct.pack(f"<{n_frames}h", *([0] * n_frames)))


def test_parts_sort_numerically_not_as_strings(tmp_path):
    series_dir = tmp_path / "alien_invasion"
    series_dir.mkdir()
    # Deliberately written out of order, and includes a 2-digit part
    # number — a naive string sort would put "10" before "2".
    for n in (2, 10, 1):
        _write_silent_wav(series_dir / f"alien_invasion{n}.wav")

    series = scan_story_dirs((tmp_path,))
    assert len(series) == 1
    numbers = [p.part_number.value for p in series[0].parts]
    assert numbers == [1, 2, 10]


def test_series_id_is_the_folder_name(tmp_path):
    series_dir = tmp_path / "alien_invasion"
    series_dir.mkdir()
    _write_silent_wav(series_dir / "alien_invasion1.wav")

    series = scan_story_dirs((tmp_path,))
    assert series[0].series_id.value == "alien_invasion"
    assert series[0].parts[0].series_id.value == "alien_invasion"


def test_file_with_no_trailing_digits_is_skipped(tmp_path):
    series_dir = tmp_path / "alien_invasion"
    series_dir.mkdir()
    _write_silent_wav(series_dir / "alien_invasion1.wav")
    _write_silent_wav(series_dir / "intro.wav")  # no trailing digits — unplaceable

    series = scan_story_dirs((tmp_path,))
    assert len(series) == 1
    assert len(series[0].parts) == 1
    assert series[0].parts[0].part_number.value == 1


def test_series_with_zero_placeable_parts_is_omitted(tmp_path):
    series_dir = tmp_path / "empty_series"
    series_dir.mkdir()
    _write_silent_wav(series_dir / "intro.wav")  # no trailing digits

    assert scan_story_dirs((tmp_path,)) == ()


def test_multiple_series_sorted_alphabetically(tmp_path):
    for name in ("zeta_front", "alien_invasion"):
        series_dir = tmp_path / name
        series_dir.mkdir()
        _write_silent_wav(series_dir / f"{name}1.wav")

    series = scan_story_dirs((tmp_path,))
    assert [s.series_id.value for s in series] == ["alien_invasion", "zeta_front"]


def test_missing_stories_dir_is_skipped_not_an_error(tmp_path):
    assert scan_story_dirs((tmp_path / "does_not_exist",)) == ()


def test_loose_file_at_stories_root_is_not_a_series(tmp_path):
    # A file directly under a stories dir (no series subfolder) can't be
    # grouped into any series — only subfolders are series.
    _write_silent_wav(tmp_path / "loose1.wav")
    assert scan_story_dirs((tmp_path,)) == ()
