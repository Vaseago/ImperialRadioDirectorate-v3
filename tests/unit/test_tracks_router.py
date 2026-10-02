"""Unit tests for `web.routers.tracks` — the shared cross-pool streaming
endpoint, and the error-handler mapping (`web.errors`)."""

from __future__ import annotations

import struct
import wave
from pathlib import Path

from fastapi.testclient import TestClient

from adapters.library import scan_library_dirs, scan_story_dirs
from web.app import create_app


def write_silent_wav(path: Path, seconds: float = 0.5, sample_rate: int = 8000) -> None:
    n_frames = int(seconds * sample_rate)
    with wave.open(str(path), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(struct.pack("<%dh" % n_frames, *([0] * n_frames)))


def test_stream_unknown_track_id_returns_404(make_config):
    app = create_app(make_config())
    client = TestClient(app)
    resp = client.get("/api/tracks/doesnotexist1234/stream")
    assert resp.status_code == 404


def test_stream_finds_a_music_track(make_config):
    cfg = make_config()
    (cfg.music_dir / "Ambient").mkdir()
    write_silent_wav(cfg.music_dir / "Ambient" / "a.wav")
    track = scan_library_dirs((cfg.music_dir,))[0]

    app = create_app(cfg)
    client = TestClient(app)
    resp = client.get(f"/api/tracks/{track.id.value}/stream")
    assert resp.status_code == 200


def test_stream_finds_an_interlude_track(make_config):
    cfg = make_config()
    write_silent_wav(cfg.interludes_dir / "ad1.wav")
    track = scan_library_dirs((cfg.interludes_dir,))[0]

    app = create_app(cfg)
    client = TestClient(app)
    resp = client.get(f"/api/tracks/{track.id.value}/stream")
    assert resp.status_code == 200


def test_stream_finds_a_story_part_track(make_config):
    cfg = make_config()
    series_dir = cfg.stories_dir / "alien_invasion"
    series_dir.mkdir()
    write_silent_wav(series_dir / "alien_invasion1.wav")

    series = scan_story_dirs((cfg.stories_dir,))
    track = series[0].parts[0].track

    app = create_app(cfg)
    client = TestClient(app)
    resp = client.get(f"/api/tracks/{track.id.value}/stream")
    assert resp.status_code == 200


def test_stream_supports_range_requests(make_config):
    cfg = make_config()
    (cfg.music_dir / "Ambient").mkdir()
    write_silent_wav(cfg.music_dir / "Ambient" / "a.wav", seconds=2.0)
    track = scan_library_dirs((cfg.music_dir,))[0]

    app = create_app(cfg)
    client = TestClient(app)
    resp = client.get(f"/api/tracks/{track.id.value}/stream", headers={"Range": "bytes=0-99"})
    assert resp.status_code == 206
    assert "Content-Range" in resp.headers
