"""The FastAPI app factory for IRD v3.

`create_app(config)` is dependency-injected — a test builds an app against
an isolated `Config` pointed at tmp-dir library folders, never the real
filesystem. `create_app_from_config` is the thin real-entry-point wrapper
`ird_v3_web_main.py` calls with `Config.load()`.

No static/template mounting, no `pages` router — Phase 6 (the frontend)
has not started, standing instruction from the owner, 2026-10-01.

`ResumeCheckpointManager` is constructed exactly once per app and stored
on `app.state` — its throttling state (`_last_write_monotonic`) must
persist across requests, unlike the stateless channel services.
"""

from __future__ import annotations

from fastapi import FastAPI

from config import Config
from services import MusicChannelService, PlaybackResumeStateStore, ResumeCheckpointManager, StoriesChannelService

from .errors import register_exception_handlers
from .routers import music, stories, tracks

__all__ = ["create_app", "create_app_from_config"]


def create_app(config: Config) -> FastAPI:
    app = FastAPI(title="Imperial Radio Directorate (web)")
    app.state.config = config

    checkpoint_manager = ResumeCheckpointManager(store=PlaybackResumeStateStore(path=config.resume_state_path))
    app.state.music_service = MusicChannelService(config=config)
    app.state.stories_service = StoriesChannelService(config=config, checkpoint_manager=checkpoint_manager)

    register_exception_handlers(app)
    app.include_router(music.router)
    app.include_router(stories.router)
    app.include_router(tracks.router)
    return app


def create_app_from_config(config: Config | None = None) -> FastAPI:
    return create_app(config if config is not None else Config.load())
