"""The Stories channel REST surface.

Resolved 2026-10-01: Stories is tuned per-series, like Music's stations —
`GET /series` lists what's available (name, part count, listened flag,
where it would resume), `GET /series/{id}` tunes into one directly. Each
series remembers its own resume position independently.

`GET /series/{id}` never rolls the interlude dice — tuning in shouldn't
surprise the listener with an ad before anything's even started playing
again. `POST /advance` (the part that just finished) does roll it,
returning the same 1-or-2-item `items` shape as the Music router's `next`
endpoint — except when the series that just finished was the last
unlistened one, in which case `items` comes back empty and
`series_completed` is `True` with no auto-advance (owner's own call: stop
there, don't reset-and-loop the whole library). `POST /checkpoint` is the
one real state-changing write in this app, so it's the one route guarded
by `require_same_origin_header`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from primitives import StoryPartNumber, StorySeriesId
from services import pick_interlude
from web.security import require_same_origin_header
from web.serializers import serialize_story_position, serialize_story_series_summary, serialize_track

router = APIRouter(prefix="/api/stories")


@router.get("/series")
async def list_series(request: Request) -> dict:
    service = request.app.state.stories_service
    summaries = service.list_series()
    return {"series": [serialize_story_series_summary(s) for s in summaries]}


@router.get("/series/{series_id}")
async def tune_in(series_id: str, request: Request) -> dict:
    service = request.app.state.stories_service
    result = service.tune_in(StorySeriesId(series_id))
    if result is None:
        raise HTTPException(status_code=404, detail="Story series not found")

    part_number, elapsed_seconds = result
    track = service.track_for_position(StorySeriesId(series_id), part_number)
    return {
        "position": serialize_story_position(StorySeriesId(series_id), part_number),
        "elapsed_seconds": elapsed_seconds,
        "track": serialize_track(track) if track is not None else None,
    }


class AdvanceRequest(BaseModel):
    series_id: str
    part_number: int


@router.post("/advance")
async def advance(body: AdvanceRequest, request: Request) -> dict:
    service = request.app.state.stories_service
    config = request.app.state.config

    items: list[dict] = []
    if service.should_play_interlude():
        interlude = pick_interlude(config)
        if interlude is not None:
            items.append({"kind": "interlude", "track": serialize_track(interlude)})

    result = service.advance(StorySeriesId(body.series_id), StoryPartNumber(body.part_number))
    if result.next_position is not None:
        series_id, part_number = result.next_position
        track = service.track_for_position(series_id, part_number)
        if track is not None:
            items.append(
                {
                    "kind": "track",
                    "track": serialize_track(track),
                    "position": serialize_story_position(series_id, part_number),
                }
            )

    return {"items": items, "series_completed": result.series_completed}


class CheckpointRequest(BaseModel):
    series_id: str
    part_number: int
    elapsed_seconds: float
    force: bool = False


@router.post("/checkpoint", dependencies=[Depends(require_same_origin_header)])
async def checkpoint(body: CheckpointRequest, request: Request) -> dict:
    service = request.app.state.stories_service
    saved = service.checkpoint(
        StorySeriesId(body.series_id), StoryPartNumber(body.part_number), body.elapsed_seconds, force=body.force
    )
    return {"saved": saved}
