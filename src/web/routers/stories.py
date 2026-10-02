"""The Stories channel REST surface — exactly one channel, series play in
order, parts within a series always sequential, position persists across
restarts.

`GET /current` never rolls the interlude dice — resuming mid-story should
never surprise the listener with an ad before anything has even started
playing again. `POST /advance` (the part that just finished) does roll it,
returning the same 1-or-2-item `items` shape as the Music router's `next`
endpoint. `POST /checkpoint` is the one real state-changing write in this
app, so it's the one route guarded by `require_same_origin_header`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from primitives import StoryPartNumber, StorySeriesId
from services import pick_interlude
from web.security import require_same_origin_header
from web.serializers import serialize_story_position, serialize_track

router = APIRouter(prefix="/api/stories")


@router.get("/current")
async def current(request: Request) -> dict:
    service = request.app.state.stories_service
    position = service.current_position()
    if position is None:
        return {"position": None, "elapsed_seconds": 0.0, "track": None}

    series_id, part_number = position
    track = service.track_for_position(series_id, part_number)
    return {
        "position": serialize_story_position(series_id, part_number),
        "elapsed_seconds": service.current_elapsed_seconds(),
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

    next_position = service.advance(StorySeriesId(body.series_id), StoryPartNumber(body.part_number))
    if next_position is not None:
        series_id, part_number = next_position
        track = service.track_for_position(series_id, part_number)
        if track is not None:
            items.append(
                {
                    "kind": "track",
                    "track": serialize_track(track),
                    "position": serialize_story_position(series_id, part_number),
                }
            )

    return {"items": items}


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
