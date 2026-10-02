"""Typed persisted-document models for IRD v3 — one, for now:
`PlaybackResumeState` (a collection of per-series `SeriesResumeState`).
Re-exports the package's public names."""

from __future__ import annotations

from .playback_resume_state import PLAYBACK_RESUME_STATE_SCHEMA_VERSION, PlaybackResumeState, SeriesResumeState

__all__ = ["PlaybackResumeState", "SeriesResumeState", "PLAYBACK_RESUME_STATE_SCHEMA_VERSION"]
