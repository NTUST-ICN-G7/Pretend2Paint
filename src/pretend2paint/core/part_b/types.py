"""Shared Part B contracts. The referee, not a human host, owns hidden state."""

from __future__ import annotations

from enum import StrEnum

from pretend2paint.common.types import Role as Role

type PlayerId = str
type DrawingId = str


class RuleError(ValueError):
    """Invalid player action or inconsistent authoritative state."""


class Phase(StrEnum):
    LOBBY = "LOBBY"
    DEAL = "DEAL"
    DRAWING = "DRAWING"
    SPY_ACTION = "SPY_ACTION"
    REVIEW = "REVIEW"  # Sequential civilian-only moderation, 5 seconds/drawing
    VOTING = "VOTING"
    SPY_GUESS = "SPY_GUESS"
    REVEAL = "REVEAL"  # FULL reveal only after outcome is locked
    ROUND_END = "ROUND_END"


class RoundStatus(StrEnum):
    SCORED = "SCORED"
    VOID_REFERENCE_VIOLATION = "VOID_REFERENCE_VIOLATION"


class VoteStatus(StrEnum):
    SPY_CAUGHT = "SPY_CAUGHT"
    SPY_ESCAPED = "SPY_ESCAPED"
    TIE = "TIE"
    NO_VOTES = "NO_VOTES"
