from __future__ import annotations

import json
import random

import pytest

from pretend2paint.core.part_b import RuleError, WordBank, WordCard


def test_bundled_bank_meets_minimum_30_cards() -> None:
    bank = WordBank.default()
    assert len(bank) >= 30
    assert all(card.answer and card.hint for card in bank.cards)


def test_duplicate_exact_or_normalized_answer_is_rejected() -> None:
    with pytest.raises(RuleError):
        WordBank([WordCard("西瓜", "兩個字的水果"), WordCard("西瓜", "另一個提示")])
    with pytest.raises(RuleError):
        WordBank([WordCard("ABC", "three letters"), WordCard("ＡＢＣ", "another hint")])


def test_hint_must_not_contain_answer() -> None:
    with pytest.raises(RuleError):
        WordBank([WordCard("西瓜", "這就是西瓜")])
    with pytest.raises(RuleError):
        WordBank([WordCard("Apple", "A big APPLE in a basket")])


def test_empty_answers_hints_aliases_are_rejected() -> None:
    with pytest.raises(RuleError):
        WordBank([WordCard("  ", "提示")])
    with pytest.raises(RuleError):
        WordBank([WordCard("答案", "  ")])
    with pytest.raises(RuleError):
        WordBank([WordCard("答案", "提示", ("",))])


def test_bad_json_is_rejected(tmp_path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("not json", encoding="utf-8")
    with pytest.raises(RuleError):
        WordBank.from_json(path)
    path.write_text(json.dumps({"answer": "x"}), encoding="utf-8")
    with pytest.raises(RuleError):
        WordBank.from_json(path)


def test_invalid_json_card_is_rejected(tmp_path) -> None:
    path = tmp_path / "bad_card.json"
    path.write_text(json.dumps([{"answer": "hello", "hint": "world", "aliases": "word"}]), encoding="utf-8")
    with pytest.raises(RuleError):
        WordBank.from_json(path)


def test_no_repeats_until_exhaustion_then_reset() -> None:
    cards = [WordCard("蘋果", "一種水果"), WordCard("香蕉", "常見熱帶水果"), WordCard("西瓜", "兩個字的水果")]
    bank = WordBank(cards)
    used: set[str] = set()
    rng = random.Random(45)
    first_cycle = [bank.draw(rng, used).answer for _ in range(3)]
    assert set(first_cycle) == {card.answer for card in cards}
    assert set(used) == set(first_cycle)
    fourth = bank.draw(rng, used)
    assert used == {fourth.answer}
    second_cycle = [fourth.answer] + [bank.draw(rng, used).answer for _ in range(2)]
    assert len(set(second_cycle)) == 3


def test_draw_is_deterministic_with_seed() -> None:
    bank = WordBank.default()
    def run():
        rng = random.Random(1234)
        used: set[str] = set()
        return [bank.draw(rng, used).answer for _ in range(10)]
    assert run() == run()


def test_draw_requires_mutable_set() -> None:
    with pytest.raises(RuleError):
        WordBank.default().draw(random.Random(1), frozenset())  # type: ignore[arg-type]


def test_loaded_cards_are_read_only_tuple() -> None:
    bank = WordBank.default()
    assert isinstance(bank.cards, tuple)
