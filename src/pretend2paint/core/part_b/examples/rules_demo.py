"""Executable demonstration: one VOID attempt followed by two scored rounds.

Run in project root: python -m pretend2paint.core.part_b.examples.rules_demo
No sockets, UI, asynchronous tasks, or third-party packages are required.
"""

from __future__ import annotations

import random

from pretend2paint.core.part_b import (
    GameConfig,
    ModerationLedger,
    RoundOutcome,
    RoundProgress,
    RoundStatus,
    WordBank,
    apply_scores,
    build_anonymity_map,
    choose_spy,
    complete_drawings,
    deal_words,
    decode_public_votes,
    is_correct_guess,
    random_pick_index,
    resolve_blind_pick,
    resolve_vote,
    review_round,
    settle_round,
    shuffle_gallery,
    tally_votes,
    validate_votes,
)


def main() -> None:
    rng = random.Random(2026)  # deterministic demonstration ONLY
    players = ("alice", "bob", "cathy", "david", "eric")
    config = GameConfig(rounds=2)
    bank = WordBank.default()
    used: set[str] = set()
    board = {p: 0 for p in players}
    progress = RoundProgress(target_rounds=config.rounds)
    history: dict[str, int] = {}
    moderation = ModerationLedger()
    print("Referee is an automatic process, not a player.")

    while progress.completed_rounds < progress.target_rounds:
        progress = progress.begin_attempt()
        attempt = progress.current_attempt_id
        spy = choose_spy(players, rng, history if config.weighted_spy else None)
        card = bank.draw(rng, used)
        private_deals = deal_words(players, spy, card)
        assert private_deals[spy].text == card.hint
        civilians = tuple(p for p in players if p != spy)

        # The referee owns the ID mapping and the frozen drawings.
        drawing_authors = {f"image-{i}": p for i, p in enumerate(players, 1)}
        drawing_id_for = {p: d for d, p in drawing_authors.items()}
        ids = build_anonymity_map(players, drawing_authors, rng)
        original_drawings = complete_drawings(civilians, {}, lambda: {"strokes": []})
        assert len(original_drawings) == len(civilians)
        secret_order = shuffle_gallery(civilians, rng)
        reference_author = resolve_blind_pick(
            secret_order, random_pick_index(len(secret_order), rng)
        )
        reference_id = drawing_id_for[reference_author]

        # The automatic referee privately shows the selected drawing to the spy.
        # Attempt #1 demonstrates a confirmed violation of that reference.
        review_labels = ids.public_review_order(rng)
        review_order = tuple(ids.drawing_id_for_label(label) for label in review_labels)
        if attempt == 1:
            approve = civilians[:3]  # 3 / 4 => accepted
            review_votes = {p: (reference_id,) for p in approve}
        else:
            review_votes = {}  # everyone defaults to NO
        review_result = review_round(
            players=players,
            spy=spy,
            drawing_authors=drawing_authors,
            review_order=review_order,
            votes=review_votes,
            ledger=moderation,
            rng=rng,
            scores=config.score,
            threshold_ratio=config.review_threshold_ratio,
            removal_at=config.author_removal_at,
            suspension_rounds=config.review_suspension_rounds,
            attempt_id=attempt,
        )
        moderation = review_result.ledger
        if reference_id in review_result.flagged_drawings:
            # No ballot and no guess is allowed once the attempt is VOID.
            decision = None
        else:
            spy_label = ids.drawing_labels[drawing_id_for[spy]]
            public_votes = {p: spy_label for p in civilians}
            # Client knows ONLY drawing label; referee maps it to player ID.
            votes = decode_public_votes(public_votes, ids)
            validate_votes(votes, players, reference_author, spy=spy)
            verdict = resolve_vote(tally_votes(votes), spy)
            guess = card.answer if progress.completed_rounds == 0 else None
            guess_correct = is_correct_guess(guess, card)
            decision = RoundOutcome(
                players, spy, votes, verdict, guess_correct, marked=reference_author
            )
        settled = settle_round(
            progress=progress,
            review=review_result,
            reference_drawing_id=reference_id,
            drawing_authors=drawing_authors,
            players=players,
            spy=spy,
            spy_history=history,
            rules=config.score,
            outcome=decision,
        )
        history = dict(settled.spy_history)
        progress = settled.progress
        board = apply_scores(board, settled.total_delta)
        print(
            f"Attempt={attempt}, status={settled.status.value}, "
            f"completed={progress.completed_rounds}/{progress.target_rounds}, "
            f"reference={reference_author}, delta={settled.total_delta}"
        )
        if settled.status is RoundStatus.VOID_REFERENCE_VIOLATION:
            assert settled.normal_delta == {p: 0 for p in players}
        if settled.removed_players:
            print("Players removed after settlement:", sorted(settled.removed_players))
            # A must update active roster/reconnect policy and stop if <4.
            break
    print("Final board:", board)
    assert progress.completed_rounds == 2
    assert progress.attempts_started == 3
    assert sum(history.values()) == 2
    print("PASS: exactly two scored rounds despite three attempts")


if __name__ == "__main__":
    main()
