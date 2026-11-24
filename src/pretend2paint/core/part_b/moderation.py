"""Civilian-only, quota-limited sequential drawing review (pure rules).

All calls happen on a trusted referee. Caller owns deadlines, authentication,
replay protection, and confidential distribution of the drawings.
"""
from __future__ import annotations

import math
import random
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from .config import ScoreRules
from .types import DrawingId, PlayerId, RuleError

# Safe shared default: ScoreRules is a frozen dataclass.
_DEFAULT_SCORE_RULES = ScoreRules()


@dataclass(frozen=True)
class AuthorRecord:
    confirmed_violations: int = 0
    clean_round_streak: int = 0


@dataclass(frozen=True)
class ReviewerRecord:
    failure_streak: int = 0
    pending_suspensions: int = 0


@dataclass(frozen=True)
class ModerationLedger:
    """Trusted, persistent across attempts (including void attempts)."""
    authors: Mapping[PlayerId, AuthorRecord] = field(default_factory=dict)
    reviewers: Mapping[PlayerId, ReviewerRecord] = field(default_factory=dict)


@dataclass(frozen=True)
class ReviewResolution:
    """Private referee result. Never send reviewer votes or author IDs to clients."""
    flagged_drawings: frozenset[DrawingId]
    votes_by_drawing: Mapping[DrawingId, int]
    penalty_delta: Mapping[PlayerId, int]
    removed_players: frozenset[PlayerId]
    reviewer_suspended_this_attempt: frozenset[PlayerId]
    reviewer_eligible_this_attempt: frozenset[PlayerId]
    ledger: ModerationLedger
    attempt_id: int | None = None

    def may_show_to_spy_before_guess(self, drawing_id: DrawingId) -> bool:
        return drawing_id not in self.flagged_drawings


def review_vote_quota(total_players: int) -> int:
    if type(total_players) is not int or not 4 <= total_players <= 7:
        raise RuleError("Review quota supports 4–7 players")
    return 1 if total_players <= 5 else 2


def review_threshold(total_players: int, ratio: float = 2/3) -> int:
    if type(total_players) is not int or not 4 <= total_players <= 7:
        raise RuleError("Review threshold supports 4–7 players")
    if not isinstance(ratio,(int,float)) or isinstance(ratio,bool) or not math.isfinite(ratio) or not 0.5 < ratio <= 1:
        raise RuleError("ratio must be finite and in (0.5,1]")
    return math.ceil((total_players-1) * ratio)


def _validate_ledger(ledger: ModerationLedger, players: tuple[PlayerId, ...]) -> None:
    if not isinstance(ledger, ModerationLedger):
        raise RuleError("ledger must be ModerationLedger")
    for pid, record in ledger.authors.items():
        if pid not in players or not isinstance(record,AuthorRecord) or any(type(x) is not int or x < 0 for x in (record.confirmed_violations,record.clean_round_streak)):
            raise RuleError("Invalid author record")
    for pid, record in ledger.reviewers.items():
        if pid not in players or not isinstance(record,ReviewerRecord) or any(type(x) is not int or x < 0 for x in (record.failure_streak,record.pending_suspensions)):
            raise RuleError("Invalid reviewer record")


def review_round(
    *, players: Sequence[PlayerId], spy: PlayerId,
    drawing_authors: Mapping[DrawingId, PlayerId],
    review_order: Sequence[DrawingId],
    votes: Mapping[PlayerId, Sequence[DrawingId]],
    ledger: ModerationLedger,
    rng: random.Random,
    scores: ScoreRules = _DEFAULT_SCORE_RULES,
    threshold_ratio: float = 2/3,
    removal_at: int = 2,
    suspension_rounds: int = 1,
    attempt_id: int | None = None,
) -> ReviewResolution:
    """Resolve the full 5-sec/drawing sequence after deadlines.

    Each reviewer submits 0–quota drawing IDs; absent = default NO.
    One positive vote per drawing. Author MAY review their own drawing.
    On success: flagged => hidden from spy before guessing + author record;
    all drawings REMAIN voting candidates. Failed votes advance the reviewer's
    failure streak chronologically. 3 failures => -3; fourth => -6 plus
    one future civilian-review suspension; then reset failure streak.

    Suspensions are applied only if the ORIGINAL civilian threshold remains
    attainable. Pending suspensions are deferred, not silently discarded.
    An independent RNG break ties among simultaneous pending suspensions.
    """
    if attempt_id is not None and (type(attempt_id) is not int or attempt_id <= 0):
        raise RuleError("attempt_id must be a positive integer")
    if isinstance(players,(str,bytes)) or not isinstance(players,Sequence):
        raise RuleError("players must be a sequence")
    people = tuple(players)
    if not 4 <= len(people) <= 7 or len(people)!=len(set(people)) or any(not isinstance(x,str) or not x.strip() for x in people):
        raise RuleError("Expected 4–7 distinct player IDs")
    if spy not in people:
        raise RuleError("spy must be active")
    if not isinstance(scores,ScoreRules):
        raise RuleError("scores must be ScoreRules")
    if type(removal_at) is not int or removal_at < 2 or type(suspension_rounds) is not int or not 1 <= suspension_rounds <= 5:
        raise RuleError("Invalid removal/suspension policy")
    _validate_ledger(ledger,people)
    if not isinstance(drawing_authors, Mapping) or set(drawing_authors.values()) != set(people) or len(drawing_authors)!=len(people):
        raise RuleError("One drawing per active player required")
    drawings = tuple(drawing_authors)
    if any(not isinstance(d,str) or not d.strip() for d in drawings):
        raise RuleError("Drawing IDs must be strings")
    if not isinstance(review_order,Sequence) or isinstance(review_order,(str,bytes)) or len(review_order)!=len(drawings) or set(review_order)!=set(drawings) or len(set(review_order))!=len(drawings):
        raise RuleError("review_order must be an exact permutation of drawings")
    if not isinstance(votes,Mapping):
        raise RuleError("votes must map civilians to their selected drawing IDs")
    if any(pid not in people or pid==spy for pid in votes):
        raise RuleError("Only actual civilians can vote in review")

    civilians = [pid for pid in people if pid != spy]
    threshold = review_threshold(len(people),threshold_ratio)
    quota = review_vote_quota(len(people))
    prev_reviewers = {pid:ledger.reviewers.get(pid,ReviewerRecord()) for pid in people}
    pending = [pid for pid in civilians if prev_reviewers[pid].pending_suspensions > 0]
    rng.shuffle(pending)
    # Preserve fixed 2/3 population threshold; never permit a unilateral review.
    suspended = set(pending[:max(0,len(civilians)-threshold)])
    eligible = set(civilians)-suspended
    for pid, choices in votes.items():
        if pid not in eligible:
            raise RuleError("Suspended reviewer cannot cast a review vote")
        if isinstance(choices,(str,bytes)) or not isinstance(choices,Sequence):
            raise RuleError("Vote list must be a sequence")
        if len(choices)>quota or len(set(choices))!=len(choices) or any(d not in drawing_authors for d in choices):
            raise RuleError("Review quota, duplicate or target violation")

    counts: Counter[DrawingId] = Counter(d for selections in votes.values() for d in selections)
    flagged = frozenset(d for d in drawings if counts[d] >= threshold)
    author_records = dict(ledger.authors)
    reviewer_records = dict(ledger.reviewers)
    delta: dict[PlayerId,int] = {pid:0 for pid in people}
    removed: set[PlayerId] = set()
    for pid in people:
        old = author_records.get(pid,AuthorRecord())
        violation = any(d in flagged and drawing_authors[d]==pid for d in drawings)
        total = old.confirmed_violations + int(violation)
        author_records[pid] = AuthorRecord(
            confirmed_violations=total,
            clean_round_streak=0 if violation else old.clean_round_streak+1,
        )
        if violation:
            if total == 1:
                delta[pid] += scores.author_first_violation
            if total >= removal_at:
                removed.add(pid)

    for pid in people:
        old = prev_reviewers[pid]
        remaining = old.pending_suspensions - int(pid in suspended)
        streak = old.failure_streak
        if pid in eligible:
            selected = set(votes.get(pid,()))
            for drawing_id in review_order:
                if drawing_id not in selected:
                    continue
                if drawing_id in flagged:
                    streak = 0
                else:
                    streak += 1
                    if streak == 3:
                        delta[pid] += scores.reviewer_failure_three
                    elif streak >= 4:
                        delta[pid] += scores.reviewer_failure_four
                        remaining += suspension_rounds
                        streak = 0
        reviewer_records[pid] = ReviewerRecord(streak,remaining)
    return ReviewResolution(
        flagged_drawings=flagged,
        votes_by_drawing={d:counts[d] for d in drawings},
        penalty_delta=delta,
        removed_players=frozenset(removed),
        reviewer_suspended_this_attempt=frozenset(suspended),
        reviewer_eligible_this_attempt=frozenset(eligible),
        ledger=ModerationLedger(authors=author_records, reviewers=reviewer_records),
        attempt_id=attempt_id,
    )


def restrict_ledger(ledger: ModerationLedger, active_players: Sequence[PlayerId]) -> ModerationLedger:
    """After end-of-round removals, keep only remaining players' private records."""
    if not isinstance(ledger, ModerationLedger):
        raise RuleError("Expected ModerationLedger")
    active = set(active_players)
    if any(not isinstance(p,str) or not p.strip() for p in active):
        raise RuleError("Invalid PlayerId")
    return ModerationLedger(
        authors={p:r for p,r in ledger.authors.items() if p in active},
        reviewers={p:r for p,r in ledger.reviewers.items() if p in active},
    )
