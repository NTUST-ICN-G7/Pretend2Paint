"""Secret per-attempt identity mappings. Keep this ENTIRE object referee-private."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Mapping, Sequence
from .types import DrawingId, PlayerId, RuleError


@dataclass(frozen=True)
class PublicDrawing:
    """Data safe to send ONLY after drawing contents are approved for the current phase."""
    label: str                  # D1 ... Dn, deliberately no author field
    safe_reference: bool = False


@dataclass(frozen=True)
class SecretAnonymityMap:
    """Never JSON-serialize/broadcast this object to player clients."""
    player_labels: Mapping[PlayerId, str]
    drawing_labels: Mapping[DrawingId, str]
    drawing_authors: Mapping[DrawingId, PlayerId]

    def author_for_label(self, public_label: str) -> PlayerId:
        matches = [d for d, label in self.drawing_labels.items() if label == public_label]
        if len(matches) != 1:
            raise RuleError("Unknown or ambiguous public drawing label")
        return self.drawing_authors[matches[0]]

    def drawing_id_for_label(self, public_label: str) -> DrawingId:
        matches = [d for d, label in self.drawing_labels.items() if label == public_label]
        if len(matches) != 1:
            raise RuleError("Unknown public drawing label")
        return matches[0]

    def public_review_order(self, rng: random.Random) -> tuple[str, ...]:
        labels = list(self.drawing_labels.values())
        rng.shuffle(labels)
        return tuple(labels)

    def public_gallery(self, marked_drawing: DrawingId | None = None) -> tuple[PublicDrawing, ...]:
        """Return label & safe marker ONLY. No author map or player IDs."""
        if marked_drawing is not None and marked_drawing not in self.drawing_labels:
            raise RuleError("Unknown marked drawing")
        return tuple(PublicDrawing(label=f"D{i}", safe_reference=(marked_drawing is not None and self.drawing_labels[marked_drawing] == f"D{i}"))
                     for i in range(1, len(self.drawing_labels) + 1))


def build_anonymity_map(
    players: Sequence[PlayerId],
    drawing_authors: Mapping[DrawingId, PlayerId],
    rng: random.Random,
) -> SecretAnonymityMap:
    """Independently shuffle public player numbers and public drawing numbers."""
    people = tuple(players)
    if len(people) != len(set(people)) or not 4 <= len(people) <= 7 or any(not isinstance(p,str) or not p for p in people):
        raise RuleError("Expected 4–7 distinct nonempty player IDs")
    if not isinstance(drawing_authors, Mapping) or len(drawing_authors) != len(people):
        raise RuleError("Expected one drawing per active player")
    if len(set(drawing_authors.values())) != len(people) or set(drawing_authors.values()) != set(people):
        raise RuleError("Each player must own exactly one drawing")
    if any(not isinstance(d,str) or not d.strip() for d in drawing_authors):
        raise RuleError("Drawing IDs must be nonempty strings")
    player_order = list(people)
    drawing_order = list(drawing_authors)
    rng.shuffle(player_order)
    rng.shuffle(drawing_order)
    return SecretAnonymityMap(
        {p:f"P{i}" for i,p in enumerate(player_order,1)},
        {d:f"D{i}" for i,d in enumerate(drawing_order,1)},
        dict(drawing_authors),
    )


def decode_public_votes(
    ballot_by_player: Mapping[PlayerId,str], identities: SecretAnonymityMap,
) -> dict[PlayerId, PlayerId]:
    """Translate drawing label votes into internal player IDs; NEVER trust client authors."""
    if not isinstance(ballot_by_player, Mapping) or not isinstance(identities,SecretAnonymityMap):
        raise RuleError("Invalid public ballots / mapping")
    return {voter:identities.author_for_label(label) for voter,label in ballot_by_player.items()}
