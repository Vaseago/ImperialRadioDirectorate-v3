"""Typed persisted-document models for IRD v3 — one, for now:
`PlaybackResumeState`. Re-exports the package's public names."""

from __future__ import annotations

from .playback_resume_state import PLAYBACK_RESUME_STATE_SCHEMA_VERSION, PlaybackResumeState

__all__ = ["PlaybackResumeState", "PLAYBACK_RESUME_STATE_SCHEMA_VERSION"]
