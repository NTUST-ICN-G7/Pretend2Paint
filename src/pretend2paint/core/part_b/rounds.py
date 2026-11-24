"""Round accounting; void reference violations never consume a completed round."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

from .config import ScoreRules
from .moderation import ReviewResolution
from .rules import RoundOutcome, score_round
from .types import DrawingId, PlayerId, RoundStatus, RuleError


@dataclass(frozen=True)
class RoundProgress:
    target_rounds: int
    attempts_started: int = 0
    attempts_settled: int = 0
    completed_rounds: int = 0

    def __post_init__(self) -> None:
        values = (self.target_rounds,self.attempts_started,self.attempts_settled,self.completed_rounds)
        if any(type(x) is not int for x in values) or not 1 <= self.target_rounds <= 100 or not 0 <= self.completed_rounds <= self.attempts_settled <= self.attempts_started or self.attempts_started-self.attempts_settled > 1 or self.completed_rounds > self.target_rounds:
            raise RuleError("Invalid RoundProgress counters")

    def begin_attempt(self) -> RoundProgress:
        if self.attempts_started != self.attempts_settled or self.completed_rounds >= self.target_rounds:
            raise RuleError("Cannot begin: unfinished attempt or target reached")
        return replace(self,attempts_started=self.attempts_started+1)

    @property
    def current_attempt_id(self) -> int:
        return self.attempts_started


@dataclass(frozen=True)
class RoundSettlement:
    status: RoundStatus
    attempt_id: int
    normal_delta: Mapping[PlayerId,int]
    disciplinary_delta: Mapping[PlayerId,int]
    total_delta: Mapping[PlayerId,int]
    removed_players: frozenset[PlayerId]
    progress: RoundProgress
    spy_history: Mapping[PlayerId,int]


def settle_round(
    *, progress: RoundProgress,
    review: ReviewResolution,
    reference_drawing_id: DrawingId,
    drawing_authors: Mapping[DrawingId, PlayerId],
    players: tuple[PlayerId,...],
    spy: PlayerId,
    spy_history: Mapping[PlayerId,int],
    rules: ScoreRules,
    outcome: RoundOutcome | None = None,
) -> RoundSettlement:
    """Run immediately after review if reference is flagged; otherwise after ballot/guess.

    VOID: no normal score, penalties and reviewer stats remain, no completed
    round added, spy history unchanged. Never use a reused/late attempt ID.
    """
    if not isinstance(progress,RoundProgress) or progress.attempts_started != progress.attempts_settled+1:
        raise RuleError("Exactly one open attempt required")
    if not isinstance(review,ReviewResolution) or not isinstance(rules,ScoreRules):
        raise RuleError("ReviewResolution and ScoreRules required")
    if review.attempt_id is not None and review.attempt_id != progress.current_attempt_id:
        raise RuleError("Review belongs to a different attempt; reject stale/replayed review")
    if not isinstance(drawing_authors,Mapping) or reference_drawing_id not in drawing_authors or drawing_authors[reference_drawing_id] == spy:
        raise RuleError("Reference must be an actual civilian drawing")
    if len(players)!=len(set(players)) or set(drawing_authors.values())!=set(players) or spy not in players:
        raise RuleError("Inconsistent active players / drawing mapping")
    if not isinstance(spy_history,Mapping) or any(pid not in players or type(count) is not int or count<0 for pid,count in spy_history.items()):
        raise RuleError("Invalid spy assignment history")
    if set(review.penalty_delta) != set(players):
        raise RuleError("Review penalties must cover exactly active players")

    is_void = reference_drawing_id in review.flagged_drawings
    if is_void:
        if outcome is not None:
            raise RuleError("Void reference review must skip voting/guessing")
        normal = {p:0 for p in players}
        status = RoundStatus.VOID_REFERENCE_VIOLATION
        history = dict(spy_history)
    else:
        if not isinstance(outcome,RoundOutcome) or set(outcome.players)!=set(players) or outcome.spy!=spy or outcome.marked!=drawing_authors[reference_drawing_id]:
            raise RuleError("Non-void round requires matching RoundOutcome and marked author")
        normal = score_round(outcome,rules)
        status = RoundStatus.SCORED
        history = dict(spy_history)
        history[spy] = history.get(spy,0)+1
    total = {p: normal[p]+review.penalty_delta[p] for p in players}
    next_progress = replace(progress, attempts_settled=progress.attempts_settled+1,
                            completed_rounds=progress.completed_rounds+int(not is_void))
    return RoundSettlement(status,progress.current_attempt_id,normal,
                           dict(review.penalty_delta),total,review.removed_players,
                           next_progress,history)
