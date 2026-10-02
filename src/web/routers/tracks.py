"""The shared audio-streaming endpoint — one route serves any track
regardless of which pool it came from (music, a story part, or an
interlude), via `services.find_track_by_id`'s cross-pool lookup.

Uses plain `FileResponse` for Range-request support (seeking) — verified
fact carried forward from legacy IRD's own direct check against the
installed Starlette version's source: `FileResponse` natively handles
single-range `Range` requests (206 Partial Content, `Content-Range`), so
no hand-rolled Range parsing is needed here either.
"""

from __future__ import annotations

import mimetypes

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from primitives import TrackId
from services import find_track_by_id

router = APIRouter(prefix="/api/tracks")

# stdlib `mimetypes` gets these three wrong for what an <audio> element
# expects — verified live 2026-10-01 (see docs/ROADMAP_HISTORY.md's Phase 2
# entry): .mp4 guesses "video/mp4" (legacy IRD's own known issue — these
# files are audio-only in intent even though the container also carries a
# video track), .aac guesses the non-standard "audio/vnd.dlna.adts", .flac
# guesses the older "audio/x-flac".
_MIME_TYPE_OVERRIDES = {
    ".mp4": "audio/mp4",
    ".aac": "audio/aac",
    ".flac": "audio/flac",
}


@router.get("/{track_id}/stream")
async def stream_track(track_id: str, request: Request) -> FileResponse:
    config = request.app.state.config
    track = find_track_by_id(config, TrackId(track_id))
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")

    ext = track.path.suffix.lower()
    media_type = _MIME_TYPE_OVERRIDES.get(ext) or mimetypes.guess_type(str(track.path))[0] or "audio/mpeg"
    return FileResponse(track.path, media_type=media_type)
