"""輸出動作：handle() 回傳的「要做的事」，由 runtime 執行（DESIGN.md 第 6.2 節）。"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pretend2paint.common.types import PlayerId
from pretend2paint.core.flow.messages import SECRET_MESSAGES, MessageType
from pretend2paint.core.flow.timers import TimerId
from pretend2paint.core.flow.views import PlayerView


@dataclass(frozen=True, slots=True)
class Unicast:
    """只送給一個人。機密一律用這個；to 可以是本機（runtime 在本機轉交）。"""

    to: PlayerId
    message_type: MessageType
    payload: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class Broadcast:
    """送給房間所有人，不可含機密。"""

    message_type: MessageType
    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.message_type in SECRET_MESSAGES:
            raise ValueError(f"{self.message_type} 是機密訊息，只能用 Unicast")


@dataclass(frozen=True, slots=True)
class StartTimer:
    """請 runtime 在 seconds 秒後送回 TimerFired(timer)。"""

    timer: TimerId
    seconds: float


@dataclass(frozen=True, slots=True)
class CancelTimer:
    """取消計時器。"""

    timer: TimerId


@dataclass(frozen=True, slots=True)
class ViewChanged:
    """畫面狀態改變；runtime 放進 ui_queue。只由 PlayerEngine 產生。"""

    view: PlayerView


class GameOverReason(StrEnum):
    """遊戲結束原因。"""

    FINISHED = "finished"
    HOST_LEFT = "host_left"
    NOT_ENOUGH_PLAYERS = "not_enough_players"


@dataclass(frozen=True, slots=True)
class GameOver:
    """遊戲結束。"""

    reason: GameOverReason


type Effect = Unicast | Broadcast | StartTimer | CancelTimer | ViewChanged | GameOver
"""所有輸出動作。"""
