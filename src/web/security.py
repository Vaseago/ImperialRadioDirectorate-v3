"""CSRF mitigation for this app's one real state-changing route
(`POST /api/stories/checkpoint`). Re-derived from legacy IRD's own
`web/security.py` (a verified-good, intentionally lightweight fact, not
copied): NOT a real anti-forgery token (nothing secret or per-session) —
deliberately doesn't need to be, since the goal is only to rule out a bare
HTML form submitting cross-origin, not to authenticate the caller. This
app has no concept of authenticated callers at all.
"""

from __future__ import annotations

from fastapi import Header, HTTPException

__all__ = ["REQUIRED_HEADER_NAME", "REQUIRED_HEADER_VALUE", "require_same_origin_header"]

REQUIRED_HEADER_NAME = "X-IRD-Request"
REQUIRED_HEADER_VALUE = "1"


def require_same_origin_header(x_ird_request: str | None = Header(default=None)) -> None:
    if x_ird_request != REQUIRED_HEADER_VALUE:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Missing or invalid {REQUIRED_HEADER_NAME} header — this endpoint "
                "only accepts requests from this app's own frontend."
            ),
        )
