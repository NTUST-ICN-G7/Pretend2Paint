"""Pure game-rule functions for the drawing-based undercover game (Part B).

No network I/O, timers, sleep, UI, global RNG state, or imports of Part A.
"""

from __future__ import annotations

import random
import unicodedata
from collections import Counter
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence, TypeVar

from .config import ScoreRules
from .types import PlayerId, Role, RuleError, VoteStatus
from .words import WordCard


def _players(sequence: Sequence[PlayerId], *, allow_empty: bool = False) -> tuple[PlayerId, ...]:
    if isinstance(sequence, (str, bytes)) or not isinstance(sequence, Sequence):
        raise RuleError("players/authors must be a sequence of PlayerIds")
    result = tuple(sequence)
    if not allow_empty and not result:
        raise RuleError("players/authors cannot be empty")
    if any(not isinstance(player, str) or not player.strip() for player in result):
        raise RuleError("PlayerIds must be nonempty strings")
    if len(result) != len(set(result)):
        raise RuleError("PlayerIds must be unique")
    return result


# --- Role assignment and private deals ---

def choose_spy(
    players: Sequence[PlayerId], rng: random.Random,
    history: Mapping[PlayerId, int] | None = None,
) -> PlayerId:
    """Weighted random: w_i=1/(1+completed_spy_rounds_i)^2.

    Passing no history preserves the v1.1 uniform API. Only COMPLETED round
    spy assignments count; void attempts must not increase the history.
    """
    people = _players(players)
    if history is None:
        return rng.choice(people)
    if not isinstance(history, Mapping) or any(
        pid not in people or type(count) is not int or count < 0
        for pid, count in history.items()
    ):
        raise RuleError("history must map active PlayerIds to nonnegative integers")
    weights = [1 / (1 + history.get(pid,0)) ** 2 for pid in people]
    return rng.choices(people, weights=weights, k=1)[0]


@dataclass(frozen=True)
class Deal:
    role: Role
    text: str


def deal_words(players: Sequence[PlayerId], spy: PlayerId, card: WordCard) -> dict[PlayerId, Deal]:
    """Each player receives only their own role and word/hint."""
    people = _players(players)
    if spy not in people:
        raise RuleError("Spy must be an active player")
    if not isinstance(card, WordCard):
        raise RuleError("card must be a WordCard")
    # Do not include the answer in the spy's Deal (or the hint in civilians' Deals).
    return {player: Deal(Role.SPY, card.hint) if player == spy
            else Deal(Role.CIVILIAN, card.answer) for player in people}


# --- Blind reference selection ---

DrawingT = TypeVar("DrawingT")


def complete_drawings(
    players: Sequence[PlayerId],
    received: Mapping[PlayerId, DrawingT],
    blank_factory: Callable[[], DrawingT],
) -> dict[PlayerId, DrawingT]:
    """Finalize eligible submissions with one fresh blank canvas per missing player.

    A/the authoritative referee calls this at the server-side drawing deadline.
    `received` contains the latest server-accepted snapshots and may include an
    *intentional* empty-stroke drawing, which is preserved as a valid result.
    `blank_factory` is provided by `common.Drawing`, not implemented in Part B.
    This function handles rules, NOT timers, packet delivery, or stroke formats.
    """
    eligible = _players(players)
    if not isinstance(received, Mapping):
        raise RuleError("received must map PlayerIds to drawings")
    if not callable(blank_factory):
        raise RuleError("blank_factory must be callable")
    if any(player not in eligible for player in received):
        raise RuleError("received contains a non-eligible drawing author")
    return {player: received[player] if player in received else blank_factory()
            for player in eligible}


def shuffle_gallery(authors: Sequence[PlayerId], rng: random.Random) -> list[PlayerId]:
    """Permute eligible civilian authors; the referee privately retains the mapping."""
    order = list(_players(authors))
    rng.shuffle(order)
    return order


def resolve_blind_pick(order: Sequence[PlayerId], index: int) -> PlayerId:
    """Map 0-based blind index to an author; invalid indices raise RuleError."""
    people = _players(order)
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(people):
        raise RuleError("Blind-pick index is outside the gallery")
    return people[index]


def random_pick_index(count: int, rng: random.Random) -> int:
    """Choose a uniformly random reference index automatically (no manual pick)."""
    if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
        raise RuleError("Gallery must contain at least one reference")
    return rng.randrange(count)


# --- Vote validation and resolution ---

def valid_vote_targets(
    players: Sequence[PlayerId], voter: PlayerId, marked: PlayerId | None
) -> frozenset[PlayerId]:
    """Legal vote candidates: everyone except self and marked civilian."""
    people = _players(players)
    if voter not in people:
        raise RuleError("Voter must be an active player")
    if marked is not None and marked not in people:
        raise RuleError("Marked author must be an active player")
    return frozenset(player for player in people if player != voter and player != marked)


def tally_votes(votes: Mapping[PlayerId, PlayerId]) -> Counter[PlayerId]:
    """Count votes; missing voters are abstentions."""
    if not isinstance(votes, Mapping):
        raise RuleError("votes must be a voter-to-target mapping")
    if any(not isinstance(voter, str) or not voter.strip() or
           not isinstance(target, str) or not target.strip()
           for voter, target in votes.items()):
        raise RuleError("votes must contain nonempty PlayerIds")
    return Counter(votes.values())


@dataclass(frozen=True)
class VoteOutcome:
    top: tuple[PlayerId, ...]
    caught: bool

    def status(self, spy: PlayerId) -> VoteStatus:
        if self.caught:
            return VoteStatus.SPY_CAUGHT
        if not self.top:
            return VoteStatus.NO_VOTES
        if len(self.top) > 1:
            return VoteStatus.TIE
        return VoteStatus.SPY_ESCAPED


def resolve_vote(tally: Counter[PlayerId], spy: PlayerId) -> VoteOutcome:
    """Spy is caught iff they alone have the highest positive vote count."""
    if not isinstance(tally, Counter):
        raise RuleError("tally must be collections.Counter")
    if not isinstance(spy, str) or not spy.strip():
        raise RuleError("spy must be a PlayerId")
    if not tally:
        return VoteOutcome((), False)
    if any(not isinstance(name, str) or not name.strip() or
           not isinstance(count, int) or isinstance(count, bool) or count < 0
           for name, count in tally.items()):
        raise RuleError("tally contains invalid entries")
    highest = max(tally.values(), default=0)
    if highest == 0:
        return VoteOutcome((), False)
    top = tuple(sorted(name for name, count in tally.items() if count == highest))
    return VoteOutcome(top=top, caught=(top == (spy,)))


# --- Guess matching ---

def normalize_guess(text: str) -> str:
    """NFKC, remove all Unicode whitespace, then case-fold."""
    if not isinstance(text, str):
        raise RuleError("Guess must be text")
    return "".join(unicodedata.normalize("NFKC", text).split()).casefold()


def is_correct_guess(guess: str | None, card: WordCard) -> bool:
    """Only normalized exact answer/alias matches count; None (timeout) is wrong."""
    if not isinstance(card, WordCard):
        raise RuleError("card must be a WordCard")
    if guess is None:
        return False
    normalized = normalize_guess(guess)
    if not normalized:
        return False
    return normalized in {normalize_guess(card.answer),
                          *(normalize_guess(alias) for alias in card.aliases)}


# --- Score accounting ---

@dataclass(frozen=True)
class RoundOutcome:
    players: tuple[PlayerId, ...]
    spy: PlayerId
    votes: Mapping[PlayerId, PlayerId]
    vote: VoteOutcome
    guess_correct: bool | None
    marked: PlayerId | None = None  # publicly safe civilian; optional for v1.0 compatibility


def validate_votes(
    votes: Mapping[PlayerId, PlayerId],
    players: Sequence[PlayerId],
    marked: PlayerId | None = None,
    *, spy: PlayerId | None = None,
) -> None:
    """Reject invalid ballots (not silently counted): self, unknown or marked.

    Only ACTIVE eligible participants should be passed in `players`.
    Part A additionally checks stage, sender authentication and first-vote-only.
    """
    people = _players(players)
    if not isinstance(votes, Mapping):
        raise RuleError("votes must be a mapping")
    if marked is not None and marked not in people:
        raise RuleError("Marked civilian must be an eligible player")
    if spy is not None and spy not in people:
        raise RuleError("spy must be active")
    for voter, target in votes.items():
        if voter == spy:
            raise RuleError("Spy cannot cast an effective ballot")
        if voter not in people or target not in valid_vote_targets(people, voter, marked):
            raise RuleError("votes contain an unknown, self or marked target")


def score_round(outcome: RoundOutcome, rules: ScoreRules) -> dict[PlayerId, int]:
    """Provisional 4–7 player balance; only civilians may vote.

    A unique highest-vote civilian => spy escape +3, no guess.
    A unique highest-vote spy => guess (+1 or -3).
    TIE or NO_VOTES => spy guess (+1 correct, 0 incorrect/timeout).
    Civilian voters hitting the spy always earn base+3*(N-4).
    If caught + incorrect guess, correct voters earn an extra 3.
    """
    if not isinstance(outcome, RoundOutcome) or not isinstance(rules, ScoreRules):
        raise RuleError("score_round requires RoundOutcome and ScoreRules")
    people = _players(outcome.players)
    if not 4 <= len(people) <= 7 or outcome.spy not in people:
        raise RuleError("Exactly 4–7 active players including spy required")
    if outcome.marked == outcome.spy:
        raise RuleError("Reference author cannot be the spy")
    validate_votes(outcome.votes, people, outcome.marked, spy=outcome.spy)
    computed = resolve_vote(tally_votes(outcome.votes), outcome.spy)
    if not isinstance(outcome.vote, VoteOutcome) or computed != outcome.vote:
        raise RuleError("VoteOutcome inconsistent with submitted votes")
    status = computed.status(outcome.spy)
    if status is VoteStatus.SPY_ESCAPED:
        if outcome.guess_correct is not None:
            raise RuleError("Escaping spy must not receive a guess phase")
    elif type(outcome.guess_correct) is not bool:
        raise RuleError("Caught/tied/no-vote spy requires a guess result")
    result = {p:0 for p in people}
    if status is VoteStatus.SPY_ESCAPED:
        result[outcome.spy] = rules.spy_escape
    elif status is VoteStatus.SPY_CAUGHT:
        result[outcome.spy] = (rules.spy_caught_guess_right if outcome.guess_correct
                               else rules.spy_caught_guess_wrong)
    else:
        result[outcome.spy] = (rules.spy_tie_right if outcome.guess_correct
                               else rules.spy_tie_wrong)
    reward = rules.civilian_reward(len(people), caught_wrong=(status is VoteStatus.SPY_CAUGHT and not outcome.guess_correct))
    for voter,target in outcome.votes.items():
        if target == outcome.spy:
            result[voter] = reward
    return result


def apply_scores(board: Mapping[PlayerId, int], delta: Mapping[PlayerId, int]) -> dict[PlayerId, int]:
    """Return a new scoreboard without mutating either input mapping."""
    if not isinstance(board, Mapping) or not isinstance(delta, Mapping):
        raise RuleError("Scoreboard and delta must be mappings")
    if any(not isinstance(player, str) or not player.strip() or
           not isinstance(points, int) or isinstance(points, bool)
           for collection in (board, delta) for player, points in collection.items()):
        raise RuleError("Scores must have valid PlayerId and integer points")
    result = dict(board)
    for player, points in delta.items():
        result[player] = result.get(player, 0) + points
    return result


def ranking(board: Mapping[PlayerId, int]) -> list[tuple[PlayerId, int]]:
    """Descending score; ties sorted lexicographically by PlayerId."""
    if not isinstance(board, Mapping):
        raise RuleError("board must be a mapping")
    if any(not isinstance(player, str) or not player.strip() or
           not isinstance(points, int) or isinstance(points, bool)
           for player, points in board.items()):
        raise RuleError("board contains invalid entries")
    return sorted(board.items(), key=lambda entry: (-entry[1], entry[0]))


def rank_with_ties(board: Mapping[PlayerId, int]) -> list[tuple[PlayerId, int, int]]:
    """Competition ranks: (player, score, place), e.g. 1,1,3 (ties stay ties)."""
    ordered = ranking(board)
    result: list[tuple[PlayerId, int, int]] = []
    prior_score: int | None = None
    place = 0
    for idx, (player, points) in enumerate(ordered, 1):
        if prior_score is None or points != prior_score:
            place = idx
        result.append((player, points, place))
        prior_score = points
    return result


def winners(board: Mapping[PlayerId, int]) -> tuple[PlayerId, ...]:
    """All equal-highest players are winners; caller excludes removed users."""
    ordered = ranking(board)
    if not ordered:
        return ()
    best = ordered[0][1]
    return tuple(player for player, points in ordered if points == best)
