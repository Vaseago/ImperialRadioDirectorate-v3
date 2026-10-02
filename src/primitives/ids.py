"""Core identity/value types for IRD v3.

Each type enforces its own invariant at construction — an invalid state
(an empty track id, a story part numbered 0, a d100 roll of 101) is
unconstructible, never a runtime assertion scattered at every call site.
"""

from __future__ import annotations

from dataclasses import dataclass

from primitives.errors import DomainRuleViolation

__all__ = ["TrackId", "StationName", "StorySeriesId", "StoryPartNumber", "D100Roll"]


@dataclass(frozen=True, slots=True)
class TrackId:
    """A stable track identity — ``sha1(relative_path)[:16]``, same scheme
    legacy IRD verified live (stable across rescans, changes on rename — a
    documented, accepted simplification, not a bug)."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise DomainRuleViolation("TrackId cannot be empty", rule="track_id.non_empty")


@dataclass(frozen=True, slots=True)
class StationName:
    """A music station name, derived from a track's top-level subfolder
    (folder-per-station, legacy IRD's own model) — never blank; a track
    with no subfolder falls into the "General" catch-all, it's never
    assigned a blank station name."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise DomainRuleViolation("StationName cannot be blank", rule="station_name.non_blank")


@dataclass(frozen=True, slots=True)
class StorySeriesId:
    """A story series identity — its top-level subfolder name under
    ``stories/`` (e.g. ``alien_invasion``)."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise DomainRuleViolation("StorySeriesId cannot be blank", rule="story_series_id.non_blank")


@dataclass(frozen=True, slots=True)
class StoryPartNumber:
    """A 1-indexed part number within a story series — part numbering
    always starts at 1, never 0 or negative."""

    value: int

    def __post_init__(self) -> None:
        if self.value < 1:
            raise DomainRuleViolation(
                f"StoryPartNumber must be >= 1, got {self.value}", rule="story_part_number.positive"
            )


@dataclass(frozen=True, slots=True)
class D100Roll:
    """The result of rolling one d100 — always in [1, 100]. The ad/snippet
    schedulers compare this against a threshold rather than calling
    ``random.random()`` directly, so the exact mechanic (a d100 roll, not
    an arbitrary float) stays visible and independently testable."""

    value: int

    def __post_init__(self) -> None:
        if not (1 <= self.value <= 100):
            raise DomainRuleViolation(
                f"D100Roll must be in [1, 100], got {self.value}", rule="d100_roll.range"
            )

    def triggers(self, threshold: int) -> bool:
        """True if this roll is within the triggering range ``[1, threshold]``."""
        if not (1 <= threshold <= 100):
            raise DomainRuleViolation(
                f"threshold must be in [1, 100], got {threshold}", rule="d100_roll.threshold_range"
            )
        return self.value <= threshold
