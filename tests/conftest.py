"""Shared test fixtures — real synthetic silent WAV files on disk (never
mocks) and an isolated `Config` pointed at tmp-dir library folders."""

from __future__ import annotations

import struct
import wave
from pathlib import Path

import pytest

from config import Config


def write_silent_wav(path: Path, seconds: float = 0.5, sample_rate: int = 8000) -> None:
    n_frames = int(seconds * sample_rate)
    with wave.open(str(path), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(struct.pack(f"<{n_frames}h", *([0] * n_frames)))


@pytest.fixture
def make_config(tmp_path: Path):
    def _make(name: str = "default") -> Config:
        root = tmp_path / name
        music = root / "music"
        stories = root / "stories"
        interludes = root / "commercials_and_snippets"
        data = root / "data"
        for d in (music, stories, interludes, data):
            d.mkdir(parents=True)
        return Config(base_dir=root, data_dir=data, music_dir=music, stories_dir=stories, interludes_dir=interludes)

    return _make
