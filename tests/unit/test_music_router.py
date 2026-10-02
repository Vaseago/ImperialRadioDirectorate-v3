"""Unit tests for `web.routers.music`, via `TestClient` against a real
app built from an isolated `Config`."""

from __future__ import annotations

import struct
import wave
from pathlib import Path

from fastapi.testclient import TestClient

from web.app import create_app


def write_silent_wav(path: Path, seconds: float = 0.5, sample_rate: int = 8000) -> None:
    n_frames = int(seconds * sample_rate)
    with wave.open(str(path), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(struct.pack("<%dh" % n_frames, *([0] * n_frames)))


def test_list_stations_empty_library(make_config):
    app = create_app(make_config())
    client = TestClient(app)
    resp = client.get("/api/music/stations")
    assert resp.status_code == 200
    assert resp.json() == {"stations": []}


def test_list_stations_returns_real_stations(make_config):
    cfg = make_config()
    (cfg.music_dir / "Ambient").mkdir()
    write_silent_wav(cfg.music_dir / "Ambient" / "a.wav")
    app = create_app(cfg)
    client = TestClient(app)

    resp = client.get("/api/music/stations")
    assert resp.json() == {"stations": ["Ambient"]}


def test_next_for_empty_station_returns_no_items(make_config):
    app = create_app(make_config())
    client = TestClient(app)
    resp = client.get("/api/music/stations/Nonexistent/next")
    assert resp.status_code == 200
    assert resp.json() == {"items": []}


def test_next_for_station_returns_a_track_item(make_config):
    cfg = make_config()
    (cfg.music_dir / "Ambient").mkdir()
    write_silent_wav(cfg.music_dir / "Ambient" / "a.wav")
    app = create_app(cfg)
    client = TestClient(app)

    resp = client.get("/api/music/stations/Ambient/next")
    data = resp.json()
    kinds = [item["kind"] for item in data["items"]]
    assert "track" in kinds
    track_item = next(i for i in data["items"] if i["kind"] == "track")
    assert track_item["track"]["stream_url"].startswith("/api/tracks/")


def test_stream_url_from_next_actually_streams(make_config):
    cfg = make_config()
    (cfg.music_dir / "Ambient").mkdir()
    write_silent_wav(cfg.music_dir / "Ambient" / "a.wav")
    app = create_app(cfg)
    client = TestClient(app)

    next_resp = client.get("/api/music/stations/Ambient/next")
    track_item = next(i for i in next_resp.json()["items"] if i["kind"] == "track")

    stream_resp = client.get(track_item["track"]["stream_url"])
    assert stream_resp.status_code == 200
    assert stream_resp.headers["content-type"] == "audio/x-wav" or stream_resp.headers["content-type"].startswith(
        "audio/"
    )
