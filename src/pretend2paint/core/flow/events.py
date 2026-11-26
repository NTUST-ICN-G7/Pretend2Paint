"""輸入事件：GameServer / PlayerEngine.handle() 只接受這些（DESIGN.md 第 6.1 節）。"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pretend2paint.common.types import Drawing, PlayerId
from pretend2paint.core.flow.messages import MessageType
from pretend2paint.core.flow.timers import TimerId

# ---- 來自 p2p（由 runtime 轉成事件）----


@dataclass(frozen=True, slots=True)
class PeerJoined:
    """有節點連上。"""

    player: PlayerId


@dataclass(frozen=True, slots=True)
class PeerLeft:
    """有節點斷線（心跳逾時）。"""

    player: PlayerId


# ---- 來自 streaming（由 runtime 轉成事件）----


@dataclass(frozen=True, slots=True)
class MessageReceived:
    """收到一則訊息。sender 來自連線身分，不信任 payload 自稱的身分。"""

    sender: PlayerId
    message_type: MessageType
    payload: Mapping[str, Any]


# ---- 來自 runtime 的計時器 ----


@dataclass(frozen=True, slots=True)
class TimerFired:
    """計時器到期。"""

    timer: TimerId


# ---- 來自 UI（玩家操作，只交給 PlayerEngine）----


@dataclass(frozen=True, slots=True)
class JoinRoom:
    """輸入暱稱加入房間。"""

    nickname: str


@dataclass(frozen=True, slots=True)
class UpdateConfig:
    """開房者在大廳修改設定。settings 由伺服器用 GameConfig.from_payload 驗證。"""

    settings: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class StartGame:
    """開房者按下開始。"""


@dataclass(frozen=True, slots=True)
class SubmitDrawing:
    """交畫；可重複，時間到 UI 會自動送最後一次。"""

    drawing: Drawing


@dataclass(frozen=True, slots=True)
class FlagDrawing:
    """審查時檢舉目前這張畫。"""

    label: str


@dataclass(frozen=True, slots=True)
class CastVote:
    """投票。label 為 None 表示主動棄票並鎖定。"""

    label: str | None


@dataclass(frozen=True, slots=True)
class GuessWord:
    """間諜猜答案。"""

    text: str


type UiCommand = (
    JoinRoom | UpdateConfig | StartGame | SubmitDrawing | FlagDrawing | CastVote | GuessWord
)
"""UI 送給 PlayerEngine 的操作。"""

type Event = PeerJoined | PeerLeft | MessageReceived | TimerFired | UiCommand
"""所有輸入事件。"""
