"""Unit tests for `config.Config`."""

from __future__ import annotations

import json

import pytest

from config import SUPPORTED_AUDIO_EXTENSIONS, Config, ConfigError


def test_load_with_injected_env_resolves_fields(tmp_path):
    data = tmp_path / "data"
    cfg = Config.load({"IRD_DATA_DIR": str(data)}, frozen_build=False)
    assert cfg.data_dir == data
    assert data.is_dir()  # created
    assert cfg.web_port == 8060
    assert cfg.web_host == "0.0.0.0"
    assert cfg.resume_state_path == data / "playback_resume_state.json"


def test_default_library_dirs_are_siblings_of_base_dir(tmp_path):
    cfg = Config.load({"IRD_DATA_DIR": str(tmp_path / "data")}, frozen_build=False)
    assert cfg.music_dir.name == "music"
    assert cfg.stories_dir.name == "stories"
    assert cfg.interludes_dir.name == "commercials_and_snippets"


def test_library_dir_env_overrides(tmp_path):
    music = tmp_path / "my_music"
    stories = tmp_path / "my_stories"
    interludes = tmp_path / "my_breaks"
    cfg = Config.load(
        {
            "IRD_DATA_DIR": str(tmp_path / "data"),
            "IRD_MUSIC_DIR": str(music),
            "IRD_STORIES_DIR": str(stories),
            "IRD_INTERLUDES_DIR": str(interludes),
        },
        frozen_build=False,
    )
    assert cfg.music_dir == music
    assert cfg.stories_dir == stories
    assert cfg.interludes_dir == interludes


def test_uncreatable_data_dir_is_fatal(tmp_path):
    blocker = tmp_path / "afile"
    blocker.write_text("x", encoding="utf-8")
    with pytest.raises(ConfigError):
        Config.load({"IRD_DATA_DIR": str(blocker / "sub")}, frozen_build=False)


def test_web_port_env_override_and_bad_value_falls_back(tmp_path):
    env = {"IRD_DATA_DIR": str(tmp_path / "data")}
    assert Config.load({**env, "IRD_WEB_PORT": "9060"}, frozen_build=False).web_port == 9060
    assert Config.load({**env, "IRD_WEB_PORT": "not-a-number"}, frozen_build=False).web_port == 8060


def test_overrides_file_adds_extra_dirs(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    extra_music = tmp_path / "extra_music"
    (data / "config_overrides.json").write_text(
        json.dumps({"extra_music_dirs": [str(extra_music)]}), encoding="utf-8"
    )
    cfg = Config.load({"IRD_DATA_DIR": str(data)}, frozen_build=False)
    assert cfg.music_dirs == (cfg.music_dir, extra_music)


def test_malformed_overrides_file_is_ignored(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "config_overrides.json").write_text("not json", encoding="utf-8")
    cfg = Config.load({"IRD_DATA_DIR": str(data)}, frozen_build=False)
    assert cfg.extra_music_dirs == ()


def test_supported_audio_extensions_includes_mp4_alongside_m4a():
    # .mp4 carries forward as a verified fact from legacy IRD's own real
    # AI-generated-track testing (same MP4 container mutagen's EasyMP4
    # already reads for .m4a) — not copied code, just the same fact.
    assert ".m4a" in SUPPORTED_AUDIO_EXTENSIONS
    assert ".mp4" in SUPPORTED_AUDIO_EXTENSIONS
