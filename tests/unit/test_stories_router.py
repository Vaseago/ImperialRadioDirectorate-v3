"""Unit tests for `web.routers.stories`, via `TestClient`."""

from __future__ import annotations

import struct
import wave
from pathlib import Path

from fastapi.testclient import TestClient

from web.app import create_app
from web.security import REQUIRED_HEADER_NAME, REQUIRED_HEADER_VALUE


def write_silent_wav(path: Path, seconds: float = 0.5, sample_rate: int = 8000) -> None:
    n_frames = int(seconds * sample_rate)
    with wave.open(str(path), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(struct.pack("<%dh" % n_frames, *([0] * n_frames)))


def _make_series(cfg, name: str, parts: tuple[int, ...]) -> None:
    series_dir = cfg.stories_dir / name
    series_dir.mkdir()
    for n in parts:
        write_silent_wav(series_dir / f"{name}{n}.wav")


def test_list_series_empty_library(make_config):
    app = create_app(make_config())
    client = TestClient(app)
    resp = client.get("/api/stories/series")
    assert resp.status_code == 200
    assert resp.json() == {"series": []}


def test_list_series_returns_real_series(make_config):
    cfg = make_config()
    _make_series(cfg, "alien_invasion", (1, 2))
    app = create_app(cfg)
    client = TestClient(app)

    resp = client.get("/api/stories/series")
    data = resp.json()["series"]
    assert data == [{"series_id": "alien_invasion", "part_count": 2, "listened": False, "resume_part_number": 1}]


def test_tune_in_starts_at_first_part_with_no_resume_state(make_config):
    cfg = make_config()
    _make_series(cfg, "alien_invasion", (1, 2))
    app = create_app(cfg)
    client = TestClient(app)

    resp = client.get("/api/stories/series/alien_invasion")
    data = resp.json()
    assert data["position"] == {"series_id": "alien_invasion", "part_number": 1}
    assert data["elapsed_seconds"] == 0.0
    assert data["track"] is not None


def test_tune_in_nonexistent_series_returns_404(make_config):
    app = create_app(make_config())
    client = TestClient(app)
    resp = client.get("/api/stories/series/ghost_series")
    assert resp.status_code == 404


def test_advance_moves_to_next_part_within_the_same_series(make_config):
    cfg = make_config()
    _make_series(cfg, "alien_invasion", (1, 2))
    app = create_app(cfg)
    client = TestClient(app)

    resp = client.post("/api/stories/advance", json={"series_id": "alien_invasion", "part_number": 1})
    data = resp.json()
    assert data["series_completed"] is False
    track_item = next(i for i in data["items"] if i["kind"] == "track")
    assert track_item["position"] == {"series_id": "alien_invasion", "part_number": 2}


def test_advance_past_last_part_auto_advances_to_next_unlistened_series(make_config):
    cfg = make_config()
    _make_series(cfg, "alien_invasion", (1,))
    _make_series(cfg, "zeta_front", (1,))
    app = create_app(cfg)
    client = TestClient(app)

    resp = client.post("/api/stories/advance", json={"series_id": "alien_invasion", "part_number": 1})
    data = resp.json()
    assert data["series_completed"] is True
    track_item = next(i for i in data["items"] if i["kind"] == "track")
    assert track_item["position"] == {"series_id": "zeta_front", "part_number": 1}

    series_list = client.get("/api/stories/series").json()["series"]
    alien = next(s for s in series_list if s["series_id"] == "alien_invasion")
    assert alien["listened"] is True


def test_advance_past_last_part_with_nothing_else_unlistened_stops_with_no_items(make_config):
    cfg = make_config()
    _make_series(cfg, "alien_invasion", (1,))
    app = create_app(cfg)
    client = TestClient(app)

    resp = client.post("/api/stories/advance", json={"series_id": "alien_invasion", "part_number": 1})
    data = resp.json()
    assert data["series_completed"] is True
    assert [i for i in data["items"] if i["kind"] == "track"] == []


def test_checkpoint_requires_the_csrf_header(make_config):
    cfg = make_config()
    _make_series(cfg, "alien_invasion", (1,))
    app = create_app(cfg)
    client = TestClient(app)

    resp = client.post(
        "/api/stories/checkpoint",
        json={"series_id": "alien_invasion", "part_number": 1, "elapsed_seconds": 3.0},
    )
    assert resp.status_code == 403


def test_checkpoint_succeeds_with_the_csrf_header_then_tune_in_reflects_it(make_config):
    cfg = make_config()
    _make_series(cfg, "alien_invasion", (1, 2))
    app = create_app(cfg)
    client = TestClient(app, headers={REQUIRED_HEADER_NAME: REQUIRED_HEADER_VALUE})

    resp = client.post(
        "/api/stories/checkpoint",
        json={"series_id": "alien_invasion", "part_number": 2, "elapsed_seconds": 7.5, "force": True},
    )
    assert resp.status_code == 200
    assert resp.json() == {"saved": True}

    current = client.get("/api/stories/series/alien_invasion").json()
    assert current["position"] == {"series_id": "alien_invasion", "part_number": 2}
    assert current["elapsed_seconds"] == 7.5


def test_advance_with_malformed_body_returns_422_not_500(make_config):
    app = create_app(make_config())
    client = TestClient(app)
    resp = client.post("/api/stories/advance", json={"series_id": "x"})  # missing part_number
    assert resp.status_code == 422


def test_advance_with_invalid_part_number_returns_400_not_500(make_config):
    # part_number=0 is a real DomainRuleViolation (StoryPartNumber must be
    # >= 1) — the global error handler must turn this into a clean 400,
    # never a raw 500.
    cfg = make_config()
    _make_series(cfg, "alien_invasion", (1,))
    app = create_app(cfg)
    client = TestClient(app)

    resp = client.post("/api/stories/advance", json={"series_id": "alien_invasion", "part_number": 0})
    assert resp.status_code == 400
    assert resp.json()["rule"] == "story_part_number.positive"
