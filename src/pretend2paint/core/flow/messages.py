"""Core 使用的訊息種類與傳送方向（DESIGN.md 第 7 節）。

core 只用這裡的名稱；對應到 streaming 的封包編號由 runtime 負責。
"""

from enum import StrEnum


class Direction(StrEnum):
    """訊息方向。"""

    TO_SERVER = "to_server"
    """玩家（PlayerEngine）→ 伺服器（GameServer）。"""
    TO_PLAYER = "to_player"
    """伺服器（GameServer）→ 玩家（PlayerEngine）。"""


class MessageType(StrEnum):
    """遊戲訊息種類。"""

    # 玩家 → 伺服器
    JOIN_ROOM = "join_room"
    UPDATE_CONFIG = "update_config"
    START_GAME = "start_game"
    CANVAS_SNAPSHOT = "canvas_snapshot"
    REVIEW_FLAG = "review_flag"
    VOTE = "vote"
    SPY_GUESS = "spy_guess"

    # 伺服器 → 玩家
    ROOM_STATE = "room_state"
    ROUND_STATE_SYNC = "round_state_sync"
    DEAL_WORD = "deal_word"
    SPY_REFERENCE = "spy_reference"
    REVIEW_ITEM = "review_item"
    GALLERY = "gallery"
    VOTE_RESULT = "vote_result"
    SPY_GALLERY = "spy_gallery"
    REVEAL_ALL = "reveal_all"
    ROUND_RESULT = "round_result"
    GAME_OVER = "game_over"

    @property
    def direction(self) -> Direction:
        """這種訊息的方向；runtime 依此把收到的訊息交給 GameServer 或 PlayerEngine。"""
        return Direction.TO_SERVER if self in _TO_SERVER else Direction.TO_PLAYER


_TO_SERVER = frozenset(
    {
        MessageType.JOIN_ROOM,
        MessageType.UPDATE_CONFIG,
        MessageType.START_GAME,
        MessageType.CANVAS_SNAPSHOT,
        MessageType.REVIEW_FLAG,
        MessageType.VOTE,
        MessageType.SPY_GUESS,
    }
)

SECRET_MESSAGES = frozenset(
    {
        MessageType.DEAL_WORD,
        MessageType.SPY_REFERENCE,
        MessageType.REVIEW_ITEM,
        MessageType.GALLERY,
        MessageType.SPY_GALLERY,
    }
)
"""只能單播、絕不能廣播的訊息（ADR 0008 機密規則 A、B 類）。"""
