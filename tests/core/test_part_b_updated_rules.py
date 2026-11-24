"""Regression tests for user-confirmed rule changes (v1.1.0)."""

import random

import pytest

from pretend2paint.core.part_b import (
    RoundOutcome,
    RuleError,
    ScoreRules,
    WordCard,
    complete_drawings,
    is_correct_guess,
    resolve_blind_pick,
    resolve_vote,
    score_round,
    shuffle_gallery,
    tally_votes,
    valid_vote_targets,
    validate_votes,
)

PLAYERS = ("a", "b", "c", "d", "e")


def test_all_players_can_play_without_human_referee():
    assert set(PLAYERS) == {"a", "b", "c", "d", "e"}
    assert "referee" not in PLAYERS


def test_all_blank_civilian_drawings_are_valid_and_selectable():
    civilians = ("b", "c", "d", "e")
    results = complete_drawings(civilians, {}, lambda: {"strokes": []})
    assert len(results) == 4
    assert all(drawing == {"strokes": []} for drawing in results.values())
    order = shuffle_gallery(tuple(results), random.Random(19))
    assert set(order) == set(civilians)
    assert resolve_blind_pick(order, 0) in civilians


def test_blank_drawings_independent_objects():
    results = complete_drawings(("a", "b"), {}, lambda: {"strokes": []})
    assert results["a"] is not results["b"]
    results["a"]["strokes"].append(1)
    assert results["b"] == {"strokes": []}


def test_received_explicit_blank_not_discarded():
    existing = {"strokes": []}
    results = complete_drawings(("a", "b"), {"a": existing}, lambda: {"strokes": []})
    assert results["a"] is existing
    assert results["b"] == {"strokes": []}


def test_received_partial_canvas_preserved():
    existing = {"strokes": [[(1, 2), (3, 4)]]}
    results = complete_drawings(("a", "b"), {"a": existing}, lambda: {"strokes": []})
    assert results["a"] == existing
    assert results["b"] == {"strokes": []}


def test_unrecognized_submission_author_rejected():
    with pytest.raises(RuleError):
        complete_drawings(("a", "b"), {"attacker": {}}, dict)


def test_blank_factory_required():
    with pytest.raises(RuleError):
        complete_drawings(("a",), {}, None)


@pytest.mark.parametrize("timeout", [None, "", "  "])
def test_guess_timeout_or_empty_wrong(timeout):
    assert is_correct_guess(timeout, WordCard("西瓜", "兩個字的水果")) is False


def test_marked_civilian_cannot_be_targeted():
    with pytest.raises(RuleError):
        validate_votes({"b": "c"}, PLAYERS, "c")


def test_self_vote_rejected_at_ingress():
    with pytest.raises(RuleError):
        validate_votes({"b": "b"}, PLAYERS, "c")


def test_unknown_voter_rejected_at_ingress():
    with pytest.raises(RuleError):
        validate_votes({"unknown": "b"}, PLAYERS, "c")


def test_legal_vote_accepted():
    assert validate_votes({"b": "a", "c": "a"}, PLAYERS, "d") is None


def test_marked_target_rejected_by_score_even_if_not_validated_earlier():
    votes = {"b": "c"}
    outcome = RoundOutcome(PLAYERS, "a", votes, resolve_vote(tally_votes(votes), "a"), None, marked="c")
    with pytest.raises(RuleError):
        score_round(outcome, ScoreRules())


def test_marked_spy_rejected():
    votes = {"b": "a"}
    outcome = RoundOutcome(PLAYERS, "a", votes, resolve_vote(tally_votes(votes), "a"), False, marked="a")
    with pytest.raises(RuleError):
        score_round(outcome, ScoreRules())


def test_timeout_loses_three_and_civilian_hit_gets_eleven():
    card = WordCard("西瓜", "兩個字的水果")
    votes = {"b": "a", "c": "a", "d": "a", "e": "b"}
    result = resolve_vote(tally_votes(votes), "a")
    assert result.caught
    score = score_round(RoundOutcome(PLAYERS, "a", votes, result, is_correct_guess(None, card), marked="e"), ScoreRules())
    assert score == {"a": -3, "b": 11, "c": 11, "d": 11, "e": 0}


def test_real_civilian_blank_can_be_marked_safe():
    civilians = ("b", "c", "d", "e")
    gallery = complete_drawings(civilians, {}, lambda: [])
    order = shuffle_gallery(tuple(gallery), random.Random(2))
    marked = resolve_blind_pick(order, 0)
    assert gallery[marked] == []
    assert marked not in valid_vote_targets(PLAYERS, "a", marked)


def test_word_bank_rejects_alias_visible_in_hint():
    from pretend2paint.core.part_b import WordBank
    with pytest.raises(RuleError):
        WordBank([WordCard("西瓜", "this is a watermelon", ("watermelon",))])
