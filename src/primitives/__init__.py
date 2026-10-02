"""Core value vocabulary for IRD v3 — ids, errors.

Re-exports the package's public names so callers write
``from primitives import TrackId, DomainRuleViolation`` rather than
reaching into individual submodules.
"""

from __future__ import annotations

from .errors import DomainRuleViolation
from .ids import D100Roll, StationName, StoryPartNumber, StorySeriesId, TrackId

__all__ = [
    "TrackId",
    "StationName",
    "StorySeriesId",
    "StoryPartNumber",
    "D100Roll",
    "DomainRuleViolation",
]
