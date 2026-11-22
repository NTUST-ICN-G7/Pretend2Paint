"""Word cards and a JSON-backed question bank (Part B)."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

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
                not isinstance(alias, str) or not _normalized(alias)
                for alias in card.aliases
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
    def from_json(cls, path: Path) -> "WordBank":
        """Read a local JSON list of {answer, hint, aliases?}."""
        try:
            with Path(path).open("r", encoding="utf-8") as stream:
                raw = json.load(stream)
        except (OSError, ValueError, UnicodeError) as exc:
            raise RuleError(f"Cannot read word bank: {path}") from exc
        if not isinstance(raw, list):
            raise RuleError("Word bank JSON root must be a list")
        cards: list[WordCard] = []
        for index, item in enumerate(raw):
            if not isinstance(item, dict) or set(item) - {"answer", "hint", "aliases"}:
                raise RuleError(f"Invalid card object at index {index}")
            aliases = item.get("aliases", [])
            if not isinstance(aliases, list):
                raise RuleError(f"aliases at index {index} must be an array")
            cards.append(WordCard(
                answer=item.get("answer"),
                hint=item.get("hint"),
                aliases=tuple(aliases),
            ))
        return cls(cards)

    @classmethod
    def default(cls) -> "WordBank":
        """Load the bundled core/words.json (available when installed as a package)."""
        return cls.from_json(Path(__file__).with_name("words.json"))

    def draw(self, rng: random.Random, used: set[str]) -> WordCard:
        """Choose an unused card, record it in `used`, reset at exhaustion.

        The only side effect is updating the caller-provided `used` set. This
        ensures every question appears once per cycle; the host keeps that set.
        """
        if not isinstance(used, set):
            raise RuleError("used must be a mutable set of answers")
        normalized_used = {_normalized(item) for item in used if isinstance(item, str)}
        available = [card for card in self._cards if _normalized(card.answer) not in normalized_used]
        if not available:
            used.clear()
            available = list(self._cards)
        card = rng.choice(available)
        used.add(card.answer)
        return card
