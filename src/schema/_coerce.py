"""Tiny per-field coercion helpers for structural `from_dict` loaders.

JSON has no int keys and no tuples; a hand-edited or older file may carry
the wrong type entirely. Each helper turns *whatever was on disk* into the
field's expected shape, falling back to an empty/zero value rather than
raising — a stored document must always load, never crash the app over a
malformed field. Hand-matched from ILD v3's own `schema/_coerce.py` — generic
infra, not domain logic.
"""

from __future__ import annotations

__all__ = ["as_int", "as_optional_int", "as_str", "as_optional_str", "as_float"]


def as_int(value: object, default: int = 0) -> int:
    try:
        if isinstance(value, bool):
            return default
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def as_optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def as_str(value: object, default: str = "") -> str:
    return value if isinstance(value, str) else default


def as_optional_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def as_float(value: object, default: float = 0.0) -> float:
    try:
        if isinstance(value, bool):
            return default
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
