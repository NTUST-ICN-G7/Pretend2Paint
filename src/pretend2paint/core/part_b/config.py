"""Settings for the automatic referee and Part B rules (no I/O or timers)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field, fields
from typing import Any, Mapping
from .types import Phase, RuleError

_TIMED_PHASES = (Phase.DEAL, Phase.DRAWING, Phase.SPY_ACTION,
                 Phase.REVIEW, Phase.VOTING, Phase.SPY_GUESS,
                 Phase.REVEAL, Phase.ROUND_END)


def default_phase_seconds() -> dict[Phase, float]:
    """Per-stage caps; REVIEW means seconds PER DRAWING, not the entire phase."""
    return {Phase.DEAL: 5.0, Phase.DRAWING: 30.0,
            Phase.SPY_ACTION: 30.0, Phase.REVIEW: 5.0,
            Phase.VOTING: 20.0, Phase.SPY_GUESS: 15.0,
            Phase.REVEAL: 5.0, Phase.ROUND_END: 5.0}


@dataclass(frozen=True)
class ScoreRules:
    """Initial PROVISIONAL balance, freely configurable and not play-tested."""
    spy_escape: int = 3
    spy_caught_guess_right: int = 1
    spy_caught_guess_wrong: int = -3
    civilian_hit: int = 5                 # four-player base
    civilian_hit_spy_lost: int = 8        # four-player base
    civilian_per_extra_player: int = 3
    spy_tie_right: int = 1
    spy_tie_wrong: int = 0
    author_first_violation: int = -15
    reviewer_failure_three: int = -3
    reviewer_failure_four: int = -6

    def civilian_reward(self, total_players: int, *, caught_wrong: bool) -> int:
        if type(total_players) is not int or not 4 <= total_players <= 7:
            raise RuleError("Civilian score supports 4–7 active players")
        base = self.civilian_hit_spy_lost if caught_wrong else self.civilian_hit
        return base + self.civilian_per_extra_player * (total_players - 4)


@dataclass(frozen=True)
class GameConfig:
    rounds: int = 5                       # completed, not attempted rounds
    min_players: int = 4
    max_players: int = 7
    phase_seconds: Mapping[Phase, float] = field(default_factory=default_phase_seconds)
    # Legacy API field retained: pick is now AUTOMATIC, no separate pick timer is run.
    spy_pick_seconds: float = 10.0
    score: ScoreRules = field(default_factory=ScoreRules)
    review_threshold_ratio: float = 2 / 3
    review_suspension_rounds: int = 1
    author_removal_at: int = 2
    weighted_spy: bool = True

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not _int_between(self.rounds, 1, 100):
            errors.append("rounds must be an integer from 1 to 100")
        if not _int_between(self.min_players, 4, 7):
            errors.append("min_players must be 4–7")
        if not _int_between(self.max_players, 4, 7):
            errors.append("max_players must be 4–7")
        if isinstance(self.min_players, int) and isinstance(self.max_players, int):
            if self.min_players > self.max_players:
                errors.append("min_players must not exceed max_players")
        if not isinstance(self.phase_seconds, Mapping):
            errors.append("phase_seconds must be a mapping")
        else:
            if set(self.phase_seconds) != set(_TIMED_PHASES):
                errors.append("phase_seconds must contain exactly each timed phase")
            if any(not isinstance(k, Phase) or not _seconds(v) for k,v in self.phase_seconds.items()):
                errors.append("phase_seconds requires Phase keys and finite positive seconds")
        if not _seconds(self.spy_pick_seconds):
            errors.append("spy_pick_seconds must be finite and positive")
        if not isinstance(self.score, ScoreRules):
            errors.append("score must be ScoreRules")
        else:
            for item in fields(ScoreRules):
                v = getattr(self.score, item.name)
                if not _int_between(v, -1000, 1000):
                    errors.append(f"score.{item.name} must be an integer in [-1000,1000]")
        if not isinstance(self.review_threshold_ratio, (int,float)) or isinstance(self.review_threshold_ratio,bool) or not math.isfinite(self.review_threshold_ratio) or not 0.5 < self.review_threshold_ratio <= 1:
            errors.append("review_threshold_ratio must be > 0.5 and <= 1")
        if not _int_between(self.review_suspension_rounds, 1, 5):
            errors.append("review_suspension_rounds must be 1–5")
        if not _int_between(self.author_removal_at, 2, 10):
            errors.append("author_removal_at must be 2–10")
        if type(self.weighted_spy) is not bool:
            errors.append("weighted_spy must be a bool")
        return errors

    def to_payload(self) -> dict[str, Any]:
        if errors := self.validate():
            raise RuleError("Invalid GameConfig: " + "; ".join(errors))
        return {
            "rounds": self.rounds,
            "min_players": self.min_players,
            "max_players": self.max_players,
            "phase_seconds": {key.value: value for key,value in self.phase_seconds.items()},
            "spy_pick_seconds": self.spy_pick_seconds,
            "score": {f.name: getattr(self.score,f.name) for f in fields(ScoreRules)},
            "review_threshold_ratio": self.review_threshold_ratio,
            "review_suspension_rounds": self.review_suspension_rounds,
            "author_removal_at": self.author_removal_at,
            "weighted_spy": self.weighted_spy,
        }

    @classmethod
    def from_payload(cls, data: Mapping[str, Any]) -> "GameConfig":
        if not isinstance(data, Mapping):
            raise RuleError("GameConfig payload must be a mapping")
        if set(data) - {f.name for f in fields(cls)}:
            raise RuleError("Unknown GameConfig fields")
        kwargs = dict(data)
        if "phase_seconds" in kwargs:
            raw = kwargs["phase_seconds"]
            if not isinstance(raw, Mapping):
                raise RuleError("phase_seconds must be a mapping")
            try:
                phases = {Phase(k):v for k,v in raw.items()}
            except (ValueError, TypeError) as exc:
                raise RuleError("Unknown phase") from exc
            if len(phases) != len(raw):
                raise RuleError("Duplicate phase keys")
            kwargs["phase_seconds"] = phases
        if "score" in kwargs:
            scores = kwargs["score"]
            if not isinstance(scores, Mapping) or set(scores) - {f.name for f in fields(ScoreRules)}:
                raise RuleError("Invalid score payload")
            try:
                kwargs["score"] = ScoreRules(**scores)
            except TypeError as exc:
                raise RuleError("Invalid ScoreRules") from exc
        try:
            result = cls(**kwargs)
        except TypeError as exc:
            raise RuleError("Invalid GameConfig") from exc
        if errors := result.validate():
            raise RuleError("Invalid GameConfig: " + "; ".join(errors))
        return result


def _int_between(v: object, lo: int, hi: int) -> bool:
    return type(v) is int and lo <= v <= hi


def _seconds(v: object) -> bool:
    return isinstance(v, (int,float)) and not isinstance(v,bool) and math.isfinite(v) and v > 0
