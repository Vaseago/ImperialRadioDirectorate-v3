"""The one domain-rule exception for IRD v3.

`DomainRuleViolation` is raised whenever code attempts to construct or
mutate a value into a state the v3 domain rules forbid — a story part
number below 1, a d100 roll outside 1-100.

It is a *fatal* signal, not a recoverable one — the correct response is to
fix the caller that built the impossible request, never to catch it and
fall back to a default or silently clamp the value.

Its own file per the v3 decomposition rule: a single exception type
referenced across every layer is a distinct responsibility.
"""

from __future__ import annotations

__all__ = ["DomainRuleViolation"]


class DomainRuleViolation(Exception):
    """A caller tried to reach a state the v3 domain forbids.

    Parameters
    ----------
    message:
        Human-readable description of what was rejected and why.
    rule:
        Optional short stable identifier for the specific rule that fired
        (e.g. ``"story_part_number.positive"``). Tests and callers can
        branch on this without string-matching the message.
    """

    def __init__(self, message: str, *, rule: str | None = None) -> None:
        super().__init__(message)
        self.rule = rule

    def __str__(self) -> str:
        base = super().__str__()
        return f"[{self.rule}] {base}" if self.rule else base
