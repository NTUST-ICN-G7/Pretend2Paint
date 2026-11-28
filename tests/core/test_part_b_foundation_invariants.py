"""Finite-model guards for approved Core B foundation behavior.

Issue #11: local portions of 02-01, 02-03, 02-04 and manual blind selection.
These tests do not approve candidate game policies or assert wire compatibility.
"""

from __future__ import annotations

import json
import random
from dataclasses import asdict
from itertools import permutations

import pytest

from pretend2paint.core.part_b import (
    Role,
    RuleError,
    WordCard,
    choose_spy,
    deal_words,
    resolve_blind_pick,
    shuffle_gallery,
)

# A bounded fixture, not a declaration of the required player count.
_ROSTER = ("host", "p1", "p2", "p3")
_CARD = WordCard("watermelon", "a fruit", ("melon",))


def _view(deal: object) -> dict[str, str]:
    """Observe the existing local Deal DTO, not the streaming packet."""
    return json.loads(json.dumps(asdict(deal)))


@pytest.mark.parametrize("roster", list(permutations(_ROSTER)))
def test_deal_views_are_role_specific_and_noninterfering(roster: tuple[str, ...]) -> None:
    """Exercise every possible spy identity in every fixture roster order."""
    answer_changed = WordCard("pineapple", _CARD.hint, ("ananas",))
    hint_changed = WordCard(_CARD.answer, "a summer food", _CARD.aliases)
    for spy in roster:
        original = deal_words(roster, spy, _CARD)
        new_answer = deal_words(roster, spy, answer_changed)
        new_hint = deal_words(roster, spy, hint_changed)

        assert set(original) == set(roster)
        assert [pid for pid in roster if original[pid].role is Role.SPY] == [spy]
        for pid in roster:
            expected = {
                "role": "spy" if pid == spy else "civilian",
                "text": _CARD.hint if pid == spy else _CARD.answer,
            }
            assert _view(original[pid]) == expected
            if pid == spy:
                assert _view(new_answer[pid]) == expected
                assert _view(new_hint[pid]) == {"role": "spy", "text": hint_changed.hint}
            else:
                assert _view(new_hint[pid]) == expected
                assert _view(new_answer[pid]) == {
                    "role": "civilian",
                    "text": answer_changed.answer,
                }

        # A consumer modifying the returned mapping cannot contaminate a later deal.
        original.pop(spy)
        assert set(deal_words(roster, spy, _CARD)) == set(roster)


@pytest.mark.parametrize("roster", list(permutations(_ROSTER)))
def test_blind_reference_index_matches_private_order(roster: tuple[str, ...]) -> None:
    """Model manual selection over all positions without an automatic-pick policy."""
    for spy in roster:
        civilians = tuple(pid for pid in roster if pid != spy)
        order = shuffle_gallery(civilians, random.Random(2718))
        assert order == shuffle_gallery(civilians, random.Random(2718))
        assert sorted(order) == sorted(civilians)
        before = tuple(order)
        for index, expected in enumerate(before):
            assert resolve_blind_pick(order, index) == expected
            assert expected != spy
        for invalid in (-1, len(order), True):
            with pytest.raises(RuleError):
                resolve_blind_pick(order, invalid)
        assert tuple(order) == before


@pytest.mark.parametrize("players", [[], ["host", "host"], ["host", " "], "host"])
def test_invalid_roster_does_not_consume_randomness(players: object) -> None:
    """Reject invalid inputs before altering the caller-owned RNG state."""
    rng = random.Random(314)
    before = rng.getstate()
    with pytest.raises(RuleError):
        choose_spy(players, rng)
    assert rng.getstate() == before
