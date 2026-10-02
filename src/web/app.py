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

**App-update poller** (added 2026-10-02, clean-room from IID v3's own):
needs no `Config` at all (git operations against a structurally-derived
repo path, same anchor `web.routers.app_update` uses), so it's
unconditionally constructed here, unlike a config-gated capability. Its
`run_forever()` task only actually starts once this app's ASGI lifespan
runs — a plain `TestClient(app)` used without `with` (every existing
router test in this repo) never triggers that, so test runs never shell
out to real git in the background. `create_app_from_config` (the real
entry point) runs under real uvicorn, which always drives the lifespan."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import Config
from services import MusicChannelService, PlaybackResumeStateStore, ResumeCheckpointManager, StoriesChannelService

from .errors import register_exception_handlers
from .poller.app_update_poll import AppUpdatePoller
from .routers import app_update, music, stories, tracks

__all__ = ["create_app", "create_app_from_config"]

_STATIC_DIR = Path(__file__).parent / "static"

# src/web/app.py -> parents[2] is the repo root — same derivation
# web/routers/app_update.py uses from its own (one level deeper) location.
_APP_REPO_ROOT = Path(__file__).resolve().parents[2]


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
    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
        poller_task = asyncio.create_task(app.state.app_update_poller.run_forever())
        try:
            yield
        finally:
            poller_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await poller_task

    app = FastAPI(title="Imperial Radio Directorate (web)", lifespan=_lifespan)
    app.state.config = config

    checkpoint_manager = ResumeCheckpointManager(store=PlaybackResumeStateStore(path=config.resume_state_path))
    app.state.music_service = MusicChannelService(config=config)
    app.state.stories_service = StoriesChannelService(config=config, checkpoint_manager=checkpoint_manager)

    # Not config-gated — git operations don't touch Config, same posture
    # as the router itself. The closures read/write app.state lazily (not
    # a snapshot taken now), so construction order here doesn't matter.
    app.state.pending_app_update = None
    app.state.app_update_poller = AppUpdatePoller(
        repo_root=_APP_REPO_ROOT,
        get_pending=lambda: app.state.pending_app_update,
        set_pending=lambda pending: setattr(app.state, "pending_app_update", pending),
    )

    register_exception_handlers(app)
    app.include_router(music.router)
    app.include_router(stories.router)
    app.include_router(tracks.router)
    app.include_router(app_update.router)
    app.mount("/", _NoCacheStaticFiles(directory=_STATIC_DIR, html=True), name="static")
    return app


def create_app_from_config(config: Config | None = None) -> FastAPI:
    return create_app(config if config is not None else Config.load())
