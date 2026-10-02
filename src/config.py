"""Immutable application configuration for IRD v3.

`Config` is a frozen snapshot resolved once from the environment (+ an
optional `config_overrides.json`). Unlike IID v3/ISD v3/ILD v3's own
`config.py`, this app has ZERO EVE ESI dependency and ZERO SDE dependency —
no shared-SDE dir, no ESI client id/callback, no ESI scopes. It's a local
media player, themed around EVE, with no EVE Online API dependency at all —
deliberately smaller than its siblings' `Config`, not an oversight (mirrors
legacy IRD's own `config.py` docstring framing).

Environment (all optional):
* ``IRD_DATA_DIR``         — writable state dir (default: ``<repo>/data`` or,
                              frozen, ``%PROGRAMDATA%/Imperial Radio Directorate``)
* ``IRD_MUSIC_DIR``        — music library root (default: ``<repo>/music``)
* ``IRD_STORIES_DIR``      — story-series library root (default: ``<repo>/stories``)
* ``IRD_INTERLUDES_DIR``   — shared commercials/news-snippets pool
                              (default: ``<repo>/commercials_and_snippets``)
* ``IRD_WEB_PORT``         — web port (default 8060 — IRD's legacy port)
* ``IMPERIAL_APPS_ON_PI``  — force the Raspberry-Pi flag

`config_overrides.json` (in the data dir) may add extra library directories:
``extra_music_dirs`` / ``extra_stories_dirs`` / ``extra_interludes_dirs``
(each a JSON list of path strings) — same per-machine override mechanism the
sibling v3 apps use for their own `config_overrides.json`. A missing /
corrupt / wrong-shaped file is ignored.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["Config", "ConfigError", "SUPPORTED_AUDIO_EXTENSIONS"]


class ConfigError(Exception):
    """A required path is missing or unusable."""


# .mp4 included alongside .m4a: several AI music/voice generators export
# audio-only tracks in a plain .mp4 container, the identical MP4 container
# `mutagen`'s EasyMP4 class already reads for .m4a — verified fact carried
# forward from legacy IRD's own real-file testing, not copied code.
SUPPORTED_AUDIO_EXTENSIONS: frozenset[str] = frozenset(
    {".mp3", ".ogg", ".oga", ".flac", ".wav", ".m4a", ".mp4", ".aac"}
)

_OVERRIDE_KEYS = ("extra_music_dirs", "extra_stories_dirs", "extra_interludes_dirs")


def _detect_raspberry_pi(env: Mapping[str, str]) -> bool:
    if env.get("IMPERIAL_APPS_ON_PI", "").strip().lower() in ("1", "true", "yes"):
        return True
    try:
        with open("/proc/device-tree/model", "rb") as fh:
            return b"raspberry pi" in fh.read().lower()
    except OSError:
        return False


def _load_overrides(path: Path) -> dict:
    """The post-install override keys, or ``{}`` on any problem — a missing
    or broken overrides file must never break startup."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if k in _OVERRIDE_KEYS}


def _extra_dirs(overrides: dict, key: str) -> tuple[Path, ...]:
    raw = overrides.get(key, [])
    if not isinstance(raw, list):
        return ()
    return tuple(Path(p) for p in raw if isinstance(p, str) and p)


@dataclass(frozen=True, slots=True)
class Config:
    """An immutable configuration snapshot. Build with `Config.load`."""

    base_dir: Path
    data_dir: Path

    # Deliberately NOT data_dir-derived — read-only, shared identically by
    # the web service and any desktop shell instance (same reasoning as the
    # sibling apps' SHARED_SDE_DIR: nothing here ever WRITES to a library
    # dir, so there's no whole-file-save race to isolate per-instance).
    music_dir: Path
    stories_dir: Path
    interludes_dir: Path
    extra_music_dirs: tuple[Path, ...] = field(default_factory=tuple)
    extra_stories_dirs: tuple[Path, ...] = field(default_factory=tuple)
    extra_interludes_dirs: tuple[Path, ...] = field(default_factory=tuple)

    web_host: str = "0.0.0.0"
    web_port: int = 8060

    on_raspberry_pi: bool = False

    @property
    def music_dirs(self) -> tuple[Path, ...]:
        return (self.music_dir, *self.extra_music_dirs)

    @property
    def stories_dirs(self) -> tuple[Path, ...]:
        return (self.stories_dir, *self.extra_stories_dirs)

    @property
    def interludes_dirs(self) -> tuple[Path, ...]:
        return (self.interludes_dir, *self.extra_interludes_dirs)

    @property
    def resume_state_path(self) -> Path:
        return self.data_dir / "playback_resume_state.json"

    # ------------------------------------------------------------------ #

    @classmethod
    def load(
        cls,
        env: Mapping[str, str] | None = None,
        *,
        frozen_build: bool | None = None,
        create_dirs: bool = True,
    ) -> Config:
        """Resolve a `Config` from `env` (default: ``os.environ``).

        Raises `ConfigError` if the data dir cannot be created.
        """
        env = os.environ if env is None else env
        if frozen_build is None:
            frozen_build = bool(getattr(sys, "frozen", False))

        base_dir = Path(__file__).resolve().parent

        if "IRD_DATA_DIR" in env:
            data_dir = Path(env["IRD_DATA_DIR"])
        elif frozen_build:
            data_dir = Path(env.get("PROGRAMDATA", "")) / "Imperial Radio Directorate"
        else:
            data_dir = base_dir.parent / "data"

        if create_dirs:
            try:
                data_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise ConfigError(f"cannot create data dir {data_dir}: {exc}") from exc

        def _int(name: str, default: int) -> int:
            try:
                return int(env.get(name, default))
            except (TypeError, ValueError):
                return default

        music_dir = Path(env.get("IRD_MUSIC_DIR", base_dir.parent / "music"))
        stories_dir = Path(env.get("IRD_STORIES_DIR", base_dir.parent / "stories"))
        interludes_dir = Path(
            env.get("IRD_INTERLUDES_DIR", base_dir.parent / "commercials_and_snippets")
        )

        overrides = _load_overrides(data_dir / "config_overrides.json")

        return cls(
            base_dir=base_dir,
            data_dir=data_dir,
            music_dir=music_dir,
            stories_dir=stories_dir,
            interludes_dir=interludes_dir,
            extra_music_dirs=_extra_dirs(overrides, "extra_music_dirs"),
            extra_stories_dirs=_extra_dirs(overrides, "extra_stories_dirs"),
            extra_interludes_dirs=_extra_dirs(overrides, "extra_interludes_dirs"),
            web_host="0.0.0.0",
            web_port=_int("IRD_WEB_PORT", 8060),
            on_raspberry_pi=_detect_raspberry_pi(env),
        )
