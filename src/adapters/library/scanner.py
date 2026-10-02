"""Scans configured library folders for audio files. No database — the
caller re-scans fresh (startup, or an explicit rescan action), matching
legacy IRD's own "no over-engineered persistence" posture: a personal
media library trivially fits in memory, the filesystem is the source of
truth.

Used for both `music/` (folder-per-station grouping matters) and
`commercials_and_snippets/` (a flat pool — station grouping is simply
ignored by callers that only want the pool).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import mutagen

from config import SUPPORTED_AUDIO_EXTENSIONS
from primitives import StationName, TrackId

from .models import Track

__all__ = ["scan_library_dirs"]


def _fallback_title(filename: str) -> str:
    """A cleaned-up filename when tags are missing/unreadable — verified
    fact carried forward from legacy IRD's own "reconstructed audio,
    fragmentary records" framing, which paid off functionally there too."""
    stem = Path(filename).stem
    return stem.replace("_", " ").replace("-", " ").strip()


def _track_id(relative_path: Path) -> TrackId:
    # Stable across rescans of an unchanged file (so stream URLs don't
    # break on every rescan); changes only if the file is renamed/moved —
    # legacy IRD's own accepted, documented simplification, carried
    # forward as a verified-safe fact, not a bug.
    digest = hashlib.sha1(str(relative_path).encode("utf-8")).hexdigest()
    return TrackId(digest[:16])


def _station_name(relative_path: Path) -> StationName:
    # Folder-per-station: a track's top-level subfolder (relative to its
    # library dir) is its station, however deep the file actually sits
    # within it. A track with no subfolder falls into a shared "General"
    # catch-all rather than being silently invisible — same rule legacy
    # IRD verified live.
    parts = relative_path.parts
    if len(parts) <= 1:
        return StationName("General")
    return StationName(parts[0].replace("_", " ").replace("-", " ").strip().title())


def _read_track(path: Path, library_dir: Path) -> Track | None:
    try:
        stat = path.stat()
        relative_path = path.relative_to(library_dir)

        title: str | None = None
        artist = ""
        album = ""
        duration_seconds = 0.0

        audio = mutagen.File(path, easy=True)
        if audio is not None:
            if audio.tags:
                title = (audio.tags.get("title") or [None])[0]
                artist = (audio.tags.get("artist") or [""])[0]
                album = (audio.tags.get("album") or [""])[0]
            if audio.info is not None and hasattr(audio.info, "length"):
                duration_seconds = float(audio.info.length)

        if not title:
            title = _fallback_title(path.name)

        return Track(
            id=_track_id(relative_path),
            title=title,
            artist=artist,
            album=album,
            duration_seconds=duration_seconds,
            path=path,
            library_dir=library_dir,
            mtime=stat.st_mtime,
            station=_station_name(relative_path),
        )
    except Exception:
        # One corrupt/unreadable file must never abort the whole scan —
        # same per-item resilience philosophy the sibling apps use for
        # per-section ESI/SDE parsing.
        return None


def scan_library_dirs(dirs: tuple[Path, ...]) -> tuple[Track, ...]:
    """Walk every dir in `dirs`, returning every supported audio file found
    as a `Track`. A missing dir is skipped, not an error — a fresh install
    may not have created its library folders' real content yet."""
    tracks: list[Track] = []
    for library_dir in dirs:
        if not library_dir.is_dir():
            continue
        for path in sorted(library_dir.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
                continue
            track = _read_track(path, library_dir)
            if track is not None:
                tracks.append(track)
    return tuple(tracks)
