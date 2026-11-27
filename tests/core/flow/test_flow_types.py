import json
from dataclasses import FrozenInstanceError

import pytest

from pretend2paint.common.types import BLANK_DRAWING, Drawing, Phase, Stroke
from pretend2paint.core.flow import (
    SECRET_MESSAGES,
    Broadcast,
    CastVote,
    Direction,
    MessageType,
    PayloadError,
    PlayerView,
    TimerId,
    TimerKind,
    Unicast,
    VoteState,
    drawing_from_payload,
    drawing_to_payload,
)

SAMPLE = Drawing(
    (
        Stroke("#FF0000", 0.01, ((0.0, 0.0), (0.5, 0.5))),
        Stroke("#00ff00", 0.02, ((1.0, 1.0),)),
    )
)


# ---- messages ----


def test_every_message_has_a_direction() -> None:
    to_server = {m for m in MessageType if m.direction is Direction.TO_SERVER}
    assert to_server == {
        MessageType.JOIN_ROOM,
        MessageType.UPDATE_CONFIG,
        MessageType.START_GAME,
        MessageType.CANVAS_SNAPSHOT,
        MessageType.REVIEW_FLAG,
        MessageType.VOTE,
        MessageType.SPY_GUESS,
    }


def test_secret_messages_are_server_to_player() -> None:
    assert all(m.direction is Direction.TO_PLAYER for m in SECRET_MESSAGES)


@pytest.mark.parametrize("secret", sorted(SECRET_MESSAGES))
def test_secret_message_cannot_be_broadcast(secret: MessageType) -> None:
    with pytest.raises(ValueError):
        Broadcast(secret, {})
    Unicast("p1", secret, {})  # 單播可以


def test_public_message_can_be_broadcast() -> None:
    Broadcast(MessageType.REVEAL_ALL, {"attempt_id": 1})


# ---- timers ----


def test_timer_ids_compare_by_value() -> None:
    a = TimerId(1, 3, Phase.REVIEW, TimerKind.REVIEW_ITEM, step=2)
    assert a == TimerId(1, 3, Phase.REVIEW, TimerKind.REVIEW_ITEM, step=2)
    assert a != TimerId(2, 3, Phase.REVIEW, TimerKind.REVIEW_ITEM, step=2)


# ---- events / views ----


def test_cast_vote_none_means_abstain() -> None:
    assert CastVote(None).label is None


def test_default_player_view_is_lobby_and_cannot_vote() -> None:
    view = PlayerView()
    assert view.phase is Phase.LOBBY
    assert view.vote_state is VoteState.NOT_ELIGIBLE
    assert view.snapshot_round is None


def test_views_are_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        PlayerView().phase = Phase.DEAL  # type: ignore[misc]


# ---- drawing codec ----


def test_drawing_round_trip_through_json() -> None:
    text = json.dumps(drawing_to_payload(SAMPLE))
    assert drawing_from_payload(json.loads(text)) == SAMPLE


def test_blank_drawing_round_trip() -> None:
    assert drawing_from_payload(drawing_to_payload(BLANK_DRAWING)) == BLANK_DRAWING


@pytest.mark.parametrize(
    "bad",
    [
        None,
        [],
        {"strokes": "x"},
        {"strokes": [1]},
        {"strokes": [{"color": "red", "width": 0.1, "points": [[0, 0]]}]},
        {"strokes": [{"color": "#000000", "width": 0, "points": [[0, 0]]}]},
        {"strokes": [{"color": "#000000", "width": 0.1, "points": []}]},
        {"strokes": [{"color": "#000000", "width": 0.1, "points": [[0, 1.5]]}]},
        {"strokes": [{"color": "#000000", "width": 0.1, "points": [[0]]}]},
        {"strokes": [{"color": "#000000", "width": 0.1, "points": [[True, 0]]}]},
        {"strokes": [{"color": "#000000", "width": 0.1, "points": [[float("nan"), 0]]}]},
    ],
)
def test_bad_drawing_payload_rejected(bad: object) -> None:
    with pytest.raises(PayloadError):
        drawing_from_payload(bad)


def test_too_many_points_rejected() -> None:
    big = {"strokes": [{"color": "#000000", "width": 0.1, "points": [[0.5, 0.5]] * 5001}]}
    with pytest.raises(PayloadError):
        drawing_from_payload(big)
