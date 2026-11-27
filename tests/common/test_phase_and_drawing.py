from dataclasses import FrozenInstanceError

import pytest

from pretend2paint.common.types import BLANK_DRAWING, Drawing, Phase, Role, Stroke


def test_phase_order_matches_game_rules() -> None:
    assert list(Phase) == [
        Phase.LOBBY,
        Phase.DEAL,
        Phase.DRAWING,
        Phase.SPY_ACTION,
        Phase.REVIEW,
        Phase.VOTING,
        Phase.SPY_GUESS,
        Phase.REVEAL,
        Phase.ROUND_END,
    ]


def test_phase_and_role_values_are_lowercase() -> None:
    assert all(p.value == p.value.lower() for p in Phase)
    assert {r.value for r in Role} == {"civilian", "spy"}


def test_blank_drawing_has_no_strokes() -> None:
    assert BLANK_DRAWING.is_blank
    assert Drawing() == BLANK_DRAWING


def test_drawings_compare_by_value() -> None:
    stroke = Stroke(color="#000000", width=0.01, points=((0.1, 0.2), (0.3, 0.4)))
    assert Drawing((stroke,)) == Drawing((stroke,))
    assert not Drawing((stroke,)).is_blank


def test_drawing_is_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        BLANK_DRAWING.strokes = ()  # type: ignore[misc]
