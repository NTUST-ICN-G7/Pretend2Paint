"""Word cards and a JSON-backed question bank (Part B)."""

from __future__ import annotations

import json
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .types import RuleError


def _normalized(value: str) -> str:
    # The lazy import avoids a circular dependency with rules.py.
    import unicodedata

    return "".join(unicodedata.normalize("NFKC", value).split()).casefold()


@dataclass(frozen=True)
class WordCard:
    answer: str
    hint: str
    aliases: tuple[str, ...] = ()


class WordBank:
    """Validated immutable list of questions; callers own the `used` set."""

    def __init__(self, cards: Sequence[WordCard]) -> None:
        if isinstance(cards, (str, bytes)) or not isinstance(cards, Sequence) or not cards:
            raise RuleError("WordBank requires at least one WordCard")
        seen: set[str] = set()
        validated: list[WordCard] = []
        for number, card in enumerate(cards, start=1):
            if not isinstance(card, WordCard):
                raise RuleError(f"Card {number} is not a WordCard")
            if not isinstance(card.answer, str) or not _normalized(card.answer):
                raise RuleError(f"Card {number} has an empty answer")
            if not isinstance(card.hint, str) or not _normalized(card.hint):
                raise RuleError(f"Card {number} has an empty hint")
            normalized_answer = _normalized(card.answer)
            if normalized_answer in seen:
                raise RuleError(f"Duplicate answer: {card.answer}")
            normalized_hint = _normalized(card.hint)
            if normalized_answer in normalized_hint:
                raise RuleError(f"Hint reveals answer: {card.answer}")
            if not isinstance(card.aliases, tuple) or any(
                not isinstance(alias, str) or not _normalized(alias) for alias in card.aliases
            ):
                raise RuleError(f"Card {number} has invalid aliases")
            if any(_normalized(alias) in normalized_hint for alias in card.aliases):
                raise RuleError(f"Hint reveals an answer alias: {card.answer}")
            seen.add(normalized_answer)
            validated.append(card)
        self._cards = tuple(validated)

    @property
    def cards(self) -> tuple[WordCard, ...]:
        """Read-only tuple of all cards."""
        return self._cards

    def __len__(self) -> int:
        return len(self._cards)

    @classmethod
    def from_records(cls, records: Sequence[Mapping[str, object]]) -> WordBank:
        """Validate decoded question records without file I/O or retaining mutable input."""
        if isinstance(records, (str, bytes)) or not isinstance(records, Sequence):
            raise RuleError("Word bank records must be a sequence")
        cards: list[WordCard] = []
        for index, item in enumerate(records):
            if not isinstance(item, Mapping) or set(item) - {"answer", "hint", "aliases"}:
                raise RuleError(f"Invalid card object at index {index}")
            answer, hint = item.get("answer"), item.get("hint")
            if not isinstance(answer, str) or not isinstance(hint, str):
                raise RuleError(f"Card {index} requires string answer and hint")
            aliases = item.get("aliases", [])
            if not isinstance(aliases, (list, tuple)) or any(
                not isinstance(alias, str) for alias in aliases
            ):
                raise RuleError(f"aliases at index {index} must be an array of strings")
            cards.append(WordCard(answer=answer, hint=hint, aliases=tuple(aliases)))
        return cls(cards)

    @classmethod
    def from_json(cls, path: Path) -> WordBank:
        """Legacy file loader; runtime integrations should inject decoded records."""
        try:
            with Path(path).open("r", encoding="utf-8") as stream:
                raw = json.load(stream)
        except (OSError, ValueError, UnicodeError) as exc:
            raise RuleError(f"Cannot read word bank: {path}") from exc
        if not isinstance(raw, list):
            raise RuleError("Word bank JSON root must be a list")
        return cls.from_records(raw)

    @classmethod
    def default(cls) -> WordBank:
        """Load the bundled core/words.json (available when installed as a package)."""
        return cls.from_json(Path(__file__).with_name("words.json"))

    def draw(
        self, rng: random.Random, used: set[str], *, last_answer: str | None = None
    ) -> WordCard:
        """Draw without repetition within a cycle, optionally avoiding the prior answer.

        The caller owns the per-match used set and the last issued answer. Pass
        last_answer to avoid a repeat across cycle boundaries when possible.
        A one-card bank must repeat. Omitting last_answer preserves legacy behavior.
        The used set is updated only after a successful random choice.
        """
        if not isinstance(used, set):
            raise RuleError("used must be a mutable set of answers")
        if last_answer is not None and (
            not isinstance(last_answer, str) or not _normalized(last_answer)
        ):
            raise RuleError("last_answer must be a nonempty string or None")
        normalized_used = {_normalized(item) for item in used if isinstance(item, str)}
        available = [
            card for card in self._cards if _normalized(card.answer) not in normalized_used
        ]
        exhausted = not available
        if exhausted:
            available = list(self._cards)
            if last_answer is not None and len(available) > 1:
                previous = _normalized(last_answer)
                available = [card for card in available if _normalized(card.answer) != previous]
        card = rng.choice(available)
        if exhausted:
            used.clear()
        used.add(card.answer)
        return card
