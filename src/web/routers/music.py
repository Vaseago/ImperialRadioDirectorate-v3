"""The Music channel REST surface.

No caching anywhere — every call re-scans the filesystem fresh (confirmed
directly with the owner, 2026-10-01: a personal library scans in
milliseconds, so there's no real performance cost, and it means "rescan"
isn't a concept this app needs at all, unlike legacy IRD's own cached
`app.state.tracks` + explicit `/rescan` action).

`GET /stations/{station}/next` returns a small ordered list (1 or 2
items): an interlude first if the 25% roll triggers, then always the
picked station track — the client just plays whatever's in `items` in
order, then calls this endpoint again once the last item ends. This keeps
every scheduling decision server-side; the frontend never rolls dice or
picks tracks itself.
"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from primitives import StationName, TrackId
from services import pick_interlude
from web.serializers import serialize_track

router = APIRouter(prefix="/api/music")


@router.get("/stations")
async def list_stations(request: Request) -> dict:
    stations = request.app.state.music_service.list_stations()
    return {"stations": [s.value for s in stations]}


@router.get("/stations/{station}/next")
async def next_for_station(
    station: str, request: Request, exclude_track_id: str | None = Query(default=None)
) -> dict:
    service = request.app.state.music_service
    config = request.app.state.config
    exclude = TrackId(exclude_track_id) if exclude_track_id else None

    items: list[dict] = []
    if service.should_play_interlude():
        interlude = pick_interlude(config)
        if interlude is not None:
            items.append({"kind": "interlude", "track": serialize_track(interlude)})

    track = service.pick_track(StationName(station), exclude=exclude)
    if track is not None:
        items.append({"kind": "track", "track": serialize_track(track)})

    return {"items": items}
