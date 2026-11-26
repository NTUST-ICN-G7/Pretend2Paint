from __future__ import annotations

import json
import random
from pathlib import Path

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
    path.write_text(
        json.dumps([{"answer": "hello", "hint": "world", "aliases": "word"}]), encoding="utf-8"
    )
    with pytest.raises(RuleError):
        WordBank.from_json(path)


def test_no_repeats_until_exhaustion_then_reset() -> None:
    cards = [
        WordCard("蘋果", "一種水果"),
        WordCard("香蕉", "常見熱帶水果"),
        WordCard("西瓜", "兩個字的水果"),
    ]
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


def test_from_records_no_io_and_independent_of_input(monkeypatch) -> None:
    records = [{"answer": "apple", "hint": "fruit", "aliases": ["pome"]}]

    def forbidden_open(*args, **kwargs):
        raise AssertionError("from_records must not open a file")

    monkeypatch.setattr(Path, "open", forbidden_open)
    bank = WordBank.from_records(records)
    records[0]["answer"] = "pear"
    records[0]["aliases"].append("changed")
    assert bank.cards == (WordCard("apple", "fruit", ("pome",)),)


@pytest.mark.parametrize(
    "records",
    [
        [],
        "invalid",
        {"answer": "apple", "hint": "fruit"},
        [None],
        [{"answer": "apple"}],
        [{"answer": 42, "hint": "fruit"}],
        [{"answer": "apple", "hint": "fruit", "extra": True}],
        [{"answer": "apple", "hint": "fruit", "aliases": "pome"}],
        [{"answer": "apple", "hint": "fruit", "aliases": [1]}],
        [{"answer": "apple", "hint": "APPLE tree"}],
        [{"answer": "apple", "hint": "fruit"}, {"answer": "ＡＰＰＬＥ", "hint": "food"}],
        [{"answer": "apple", "hint": "pome fruit", "aliases": ["pome"]}],
    ],
)
def test_from_records_rejects_invalid_data(records) -> None:
    with pytest.raises(RuleError):
        WordBank.from_records(records)


def test_from_records_matches_legacy_json(tmp_path) -> None:
    records = [{"answer": "apple", "hint": "fruit", "aliases": ["pome"]}]
    path = tmp_path / "words.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    assert WordBank.from_records(records).cards == WordBank.from_json(path).cards


@pytest.mark.parametrize("seed", range(20))
def test_draw_avoids_repeat_across_cycles(seed: int) -> None:
    bank = WordBank.from_records(
        [
            {"answer": "apple", "hint": "fruit"},
            {"answer": "pear", "hint": "food"},
            {"answer": "melon", "hint": "round"},
        ]
    )
    used: set[str] = set()
    rng = random.Random(seed)
    last_answer = None
    issued = []
    for _ in range(12):
        card = bank.draw(rng, used, last_answer=last_answer)
        assert card.answer != last_answer
        issued.append(card.answer)
        last_answer = card.answer
    for start in range(0, len(issued), 3):
        assert len(set(issued[start : start + 3])) == 3


def test_draw_one_card_can_repeat() -> None:
    bank = WordBank.from_records([{"answer": "apple", "hint": "fruit"}])
    used = {"apple"}
    assert bank.draw(random.Random(1), used, last_answer="apple").answer == "apple"
    assert used == {"apple"}


def test_draw_normalizes_previous_answer() -> None:
    bank = WordBank.from_records(
        [{"answer": "apple", "hint": "fruit"}, {"answer": "pear", "hint": "food"}]
    )
    used = {"apple", "pear"}
    assert bank.draw(random.Random(1), used, last_answer="ＡＰＰＬＥ").answer == "pear"
    assert used == {"pear"}


def test_failed_draw_preserves_used() -> None:
    bank = WordBank.from_records([{"answer": "apple", "hint": "fruit"}])
    used = {"apple"}
    with pytest.raises(RuleError):
        bank.draw(random.Random(1), used, last_answer=" ")
    assert used == {"apple"}

    class FailingRandom(random.Random):
        def choice(self, seq):
            raise RuntimeError("choice failed")

    with pytest.raises(RuntimeError, match="choice failed"):
        bank.draw(FailingRandom(), used, last_answer="apple")
    assert used == {"apple"}
