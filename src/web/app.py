"""The FastAPI app factory for IRD v3.

`create_app(config)` is dependency-injected — a test builds an app against
an isolated `Config` pointed at tmp-dir library folders, never the real
filesystem. `create_app_from_config` is the thin real-entry-point wrapper
`ird_v3_web_main.py` calls with `Config.load()`.

Phase 6 (the frontend) functional skeleton mounted 2026-10-01 — plain,
un-styled HTML/JS wired to the real endpoints, explicitly a placeholder;
real visual design is a separate later pass. `src/web/static/` is mounted
last so the API routers above always take precedence over the catch-all
static handler.

`ResumeCheckpointManager` is constructed exactly once per app and stored
on `app.state` — its throttling state (`_last_write_monotonic`) must
persist across requests, unlike the stateless channel services.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import Config
from services import MusicChannelService, PlaybackResumeStateStore, ResumeCheckpointManager, StoriesChannelService

from .errors import register_exception_handlers
from .routers import music, stories, tracks

__all__ = ["create_app", "create_app_from_config"]

_STATIC_DIR = Path(__file__).parent / "static"


class _NoCacheStaticFiles(StaticFiles):
    """Plain `StaticFiles` sends no `Cache-Control` at all — only
    `ETag`/`Last-Modified` — which leaves a browser free to apply RFC 7234
    heuristic caching and skip revalidation on an ordinary reload, serving
    stale JS after a rebuild. `Cache-Control: no-cache` forces ETag
    revalidation on every request instead (a 304 is tiny — this costs
    nothing meaningful, unlike `no-store`, which would also defeat the
    browser disk cache itself)."""

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


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
    app.mount("/", _NoCacheStaticFiles(directory=_STATIC_DIR, html=True), name="static")
    return app


def create_app_from_config(config: Config | None = None) -> FastAPI:
    return create_app(config if config is not None else Config.load())
