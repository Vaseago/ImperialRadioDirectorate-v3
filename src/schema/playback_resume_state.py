"""`PlaybackResumeState` — the one piece of real persisted state IRD v3
needs that legacy IRD never did.

Legacy IRD has zero persisted state at all (`app.state.tracks` rebuilt
fresh every run) — music stays that way in v3 too (tune in, get a random
pick, no position to remember). Stories are different: they're long-form
serialized content, and the owner asked that tuning back into the Stories
channel resume "as close as possible" to wherever it was left off, not
restart from part 1. This is a singleton document — one current position
for the whole app, not scoped per anything else.

A checkpoint is written periodically during story playback and on
pause/stop (`services.resume_state_store`), not continuously — the owner's
own words, "as close as possible," not frame-exact.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ._coerce import as_float, as_int, as_str

__all__ = ["PLAYBACK_RESUME_STATE_SCHEMA_VERSION", "PlaybackResumeState"]

PLAYBACK_RESUME_STATE_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class PlaybackResumeState:
    """Where the Stories channel left off. ``series_id == ""`` means no
    story has ever been played — the Stories channel starts at the first
    series' first part."""

    series_id: str = ""
    part_number: int = 1
    elapsed_seconds: float = 0.0
    last_updated: str = ""  # ISO-8601 UTC timestamp; "" if never saved

    def to_dict(self) -> dict[str, Any]:
        return {
            "series_id": self.series_id,
            "part_number": self.part_number,
            "elapsed_seconds": self.elapsed_seconds,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, d: object) -> PlaybackResumeState:
        if not isinstance(d, dict):
            return cls()
        part_number = as_int(d.get("part_number"), default=1)
        return cls(
            series_id=as_str(d.get("series_id")),
            part_number=part_number if part_number >= 1 else 1,
            elapsed_seconds=max(0.0, as_float(d.get("elapsed_seconds"))),
            last_updated=as_str(d.get("last_updated")),
        )
