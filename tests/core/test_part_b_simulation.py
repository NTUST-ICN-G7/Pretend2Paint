"""Contract-level multi-round simulation without implementing Part A engines."""

from __future__ import annotations

import random

from pretend2paint.core.part_b import (
    GameConfig,
    Role,
    RoundOutcome,
    WordBank,
    apply_scores,
    choose_spy,
    deal_words,
    is_correct_guess,
    ranking,
    resolve_blind_pick,
    resolve_vote,
    score_round,
    shuffle_gallery,
    tally_votes,
    valid_vote_targets,
)


def test_two_rounds_five_humans_automatic_referee_deterministic() -> None:
    def run() -> tuple[list[dict[str, int]], list[tuple[str, int]]]:
        rng = random.Random(2026)
        bank = WordBank.default()
        config = GameConfig(rounds=2)
        automatic_referee_process = "referee-process"
        players = ("p1", "p2", "p3", "p4", "p5")
        assert automatic_referee_process not in players
        scoreboard = {player: 0 for player in players}
        used: set[str] = set()
        deltas = []
        for _ in range(config.rounds):
            card = bank.draw(rng, used)
            spy = choose_spy(players, rng)
            deals = deal_words(players, spy, card)
            assert deals[spy].role is Role.SPY
            assert deals[spy].text == card.hint
            assert all(deals[player].role is Role.CIVILIAN for player in players if player != spy)
            authors = [player for player in players if player != spy]
            hidden_order = shuffle_gallery(authors, rng)
            index = rng.randrange(len(hidden_order))
            marked = resolve_blind_pick(hidden_order, index)
            assert marked != spy
            votes = {}
            for voter in authors:
                candidates = valid_vote_targets(players, voter, marked)
                votes[voter] = sorted(candidates)[0]
            decision = resolve_vote(tally_votes(votes), spy)
            guess_correct = (None if len(decision.top)==1 and not decision.caught
                             else is_correct_guess(card.answer, card))
            result = RoundOutcome(players, spy, votes, decision, guess_correct, marked=marked)
            delta = score_round(result, config.score)
            assert sum(1 for player in players if player in delta) == 5
            deltas.append(delta)
            scoreboard = apply_scores(scoreboard, delta)
        assert automatic_referee_process not in scoreboard
        return deltas, ranking(scoreboard)

    assert run() == run()
