from __future__ import annotations

import random
from collections import Counter

import pytest

from pretend2paint.core.part_b import (
    Deal,
    Role,
    RoundOutcome,
    RuleError,
    ScoreRules,
    VoteOutcome,
    WordCard,
    apply_scores,
    choose_spy,
    deal_words,
    is_correct_guess,
    normalize_guess,
    random_pick_index,
    ranking,
    resolve_blind_pick,
    resolve_vote,
    score_round,
    shuffle_gallery,
    tally_votes,
    valid_vote_targets,
)

PLAYERS = ("a", "b", "c", "d", "e")
SPY = "a"
CARD = WordCard("西瓜", "兩個字的水果", ("watermelon",))


def test_choose_spy_is_a_player_and_deterministic() -> None:
    assert choose_spy(PLAYERS, random.Random(123)) in PLAYERS
    assert choose_spy(PLAYERS, random.Random(123)) == choose_spy(PLAYERS, random.Random(123))


def test_choose_spy_uniform_approximately_10000_rounds() -> None:
    rng = random.Random(2026)
    counts = Counter(choose_spy(PLAYERS, rng) for _ in range(10000))
    assert set(counts) == set(PLAYERS)
    assert all(abs(count - 2000) < 180 for count in counts.values())


def test_previous_spy_can_repeat() -> None:
    rng = random.Random(42)
    repeats = [choose_spy(PLAYERS, rng) for _ in range(200)]
    assert any(a == b for a, b in zip(repeats, repeats[1:], strict=False))


def test_choose_spy_rejects_invalid_roster() -> None:
    with pytest.raises(RuleError):
        choose_spy([], random.Random(1))
    with pytest.raises(RuleError):
        choose_spy(["a", "a"], random.Random(1))


def test_deal_words_private_role_text() -> None:
    deals = deal_words(PLAYERS, SPY, CARD)
    assert set(deals) == set(PLAYERS)
    assert deals[SPY] == Deal(Role.SPY, "兩個字的水果")
    assert all(deals[name] == Deal(Role.CIVILIAN, "西瓜") for name in PLAYERS if name != SPY)
    assert all(not hasattr(deal, "answer") and not hasattr(deal, "spy_id") for deal in deals.values())


def test_deal_rejects_spy_not_in_players() -> None:
    with pytest.raises(RuleError):
        deal_words(PLAYERS, "missing", CARD)


def test_shuffle_permutation_and_determinism() -> None:
    authors = ("b", "c", "d", "e")
    shuffled = shuffle_gallery(authors, random.Random(2026))
    assert sorted(shuffled) == list(authors)
    assert shuffled == shuffle_gallery(authors, random.Random(2026))
    assert authors == ("b", "c", "d", "e")


def test_blind_pick_first_and_last() -> None:
    authors = ["b", "c", "d", "e"]
    assert resolve_blind_pick(authors, 0) == "b"
    assert resolve_blind_pick(authors, 3) == "e"


@pytest.mark.parametrize("index", [-1, 4, 99, True, 1.0])
def test_blind_pick_invalid_index(index) -> None:
    with pytest.raises(RuleError):
        resolve_blind_pick(["b", "c", "d", "e"], index)


def test_random_pick_index_valid_and_deterministic() -> None:
    assert 0 <= random_pick_index(4, random.Random(2)) < 4
    assert random_pick_index(4, random.Random(2)) == random_pick_index(4, random.Random(2))


@pytest.mark.parametrize("count", [0, -1, True, 2.0])
def test_random_pick_index_invalid_count(count) -> None:
    with pytest.raises(RuleError):
        random_pick_index(count, random.Random(2))


def test_valid_vote_targets_exclude_self_and_marked() -> None:
    assert valid_vote_targets(PLAYERS, "a", "b") == frozenset({"c", "d", "e"})
    assert valid_vote_targets(PLAYERS, "b", "b") == frozenset({"a", "c", "d", "e"})
    assert valid_vote_targets(PLAYERS, "b", None) == frozenset({"a", "c", "d", "e"})


def test_invalid_voter_and_marked_are_rejected() -> None:
    with pytest.raises(RuleError):
        valid_vote_targets(PLAYERS, "x", "b")
    with pytest.raises(RuleError):
        valid_vote_targets(PLAYERS, "a", "x")


def test_tally_votes_counts_only_submitted() -> None:
    votes = {"b": "a", "c": "d", "d": "a"}
    assert tally_votes(votes) == Counter({"a": 2, "d": 1})


def test_spy_caught_only_as_unique_highest() -> None:
    outcome = resolve_vote(Counter({"a": 3, "b": 1}), "a")
    assert outcome == VoteOutcome(("a",), True)


def test_tie_does_not_catch_spy() -> None:
    outcome = resolve_vote(Counter({"a": 2, "c": 2}), "a")
    assert outcome == VoteOutcome(("a", "c"), False)


def test_all_abstain() -> None:
    assert resolve_vote(tally_votes({}), SPY) == VoteOutcome((), False)


def test_single_vote() -> None:
    assert resolve_vote(tally_votes({"b": "a"}), SPY) == VoteOutcome(("a",), True)


def test_single_vote_on_non_spy() -> None:
    assert resolve_vote(tally_votes({"b": "c"}), SPY) == VoteOutcome(("c",), False)


def test_vote_counter_with_only_zeros() -> None:
    assert resolve_vote(Counter({"a": 0}), "a") == VoteOutcome((), False)


@pytest.mark.parametrize("input_text,expected", [
    (" 西瓜 ", "西瓜"),
    ("ＷＡＴＥＲＭＥＬＯＮ", "watermelon"),
    (" W A T E R M E L O N ", "watermelon"),
    ("water\nmelon", "watermelon"),
])
def test_normalize_guess(input_text, expected) -> None:
    assert normalize_guess(input_text) == expected


@pytest.mark.parametrize("guess,correct", [
    (" 西 瓜 ", True),
    ("ＷＡＴＥＲＭＥＬＯＮ", True),
    ("WATERMELON", True),
    ("water melon", True),
    ("哈密瓜", False),
    ("", False),
    ("西瓜。", False),
])
def test_is_correct_guess(guess, correct) -> None:
    assert is_correct_guess(guess, CARD) is correct


def _score(votes: dict[str, str], guess_correct: bool | None) -> dict[str, int]:
    outcome = RoundOutcome(PLAYERS, SPY, votes, resolve_vote(tally_votes(votes), SPY), guess_correct)
    return score_round(outcome, ScoreRules())


def test_scoring_spy_escapes_and_civilian_hits() -> None:
    # Unique highest vote is an innocent, so the spy escapes.
    assert _score({"b":"d", "c":"d", "d":"e", "e":"a"}, None) == {
        "a":3, "b":0, "c":0, "d":0, "e":8,
    }


def test_scoring_spy_caught_guesses_right() -> None:
    assert _score({"b":"a", "c":"a", "d":"a", "e":"d"}, True) == {
        "a":1, "b":8, "c":8, "d":8, "e":0,
    }


def test_scoring_spy_caught_guesses_wrong() -> None:
    assert _score({"b":"a", "c":"a", "d":"a", "e":"d"}, False) == {
        "a":-3, "b":11, "c":11, "d":11, "e":0,
    }


def test_score_all_abstain_is_not_escape() -> None:
    assert _score({}, False) == {"a":0, "b":0, "c":0, "d":0, "e":0}


def test_score_one_voter_spy_caught() -> None:
    assert _score({"b":"a"}, False) == {"a":-3, "b":11, "c":0, "d":0, "e":0}


def test_score_tie_guess_right() -> None:
    assert _score({"b":"a", "c":"e", "d":"e", "e":"a"}, True) == {
        "a":1,"b":8,"c":0,"d":0,"e":8,
    }


def test_score_tie_guess_wrong() -> None:
    assert _score({"b":"a", "c":"e", "d":"e", "e":"a"}, False) == {
        "a":0,"b":8,"c":0,"d":0,"e":8,
    }


def test_vote_outcome_cannot_be_forged() -> None:
    bad_outcome = RoundOutcome(PLAYERS, SPY, {"b": "a"}, VoteOutcome((), False), None)
    with pytest.raises(RuleError):
        score_round(bad_outcome, ScoreRules())


def test_guess_required_only_if_caught() -> None:
    with pytest.raises(RuleError):
        _score({"b": "a"}, None)
    with pytest.raises(RuleError):
        _score({"b":"d", "c":"d", "d":"e", "e":"a"}, False)


def test_self_vote_is_rejected_at_scoring() -> None:
    votes = {"a": "a"}
    outcome = RoundOutcome(PLAYERS, "a", votes, resolve_vote(tally_votes(votes), "a"), True)
    with pytest.raises(RuleError):
        score_round(outcome, ScoreRules())


def test_apply_scores_no_input_mutation_and_negative_scores() -> None:
    board = {"a": 10, "b": 0}
    delta = {"a": -1, "b": 2, "c": 1}
    updated = apply_scores(board, delta)
    assert updated == {"a": 9, "b": 2, "c": 1}
    assert board == {"a": 10, "b": 0}
    assert delta == {"a": -1, "b": 2, "c": 1}


def test_ranking_score_then_player_id() -> None:
    assert ranking({"d": 2, "c": 5, "b": 5, "a": -1}) == [
        ("b", 5), ("c", 5), ("d", 2), ("a", -1)
    ]
