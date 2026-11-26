"""給 UI 的畫面狀態（DESIGN.md 第 6.4 節）。

PlayerView 只包含這位玩家有權看到的東西；UI 只依它顯示，不自己判斷規則。
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pretend2paint.common.types import Drawing, Phase, PlayerId, Role


class VoteState(StrEnum):
    """這位玩家的投票狀態。只有 OPEN 時投票鍵可以按。"""

    NOT_ELIGIBLE = "not_eligible"
    """間諜，或不是投票階段。"""
    OPEN = "open"
    VOTED = "voted"
    ABSTAINED = "abstained"


@dataclass(frozen=True, slots=True)
class PlayerInfo:
    """名單上的一位玩家。"""

    id: PlayerId
    nickname: str
    online: bool = True
    score: int = 0


@dataclass(frozen=True, slots=True)
class ReviewItem:
    """審查時目前播放的那一張。"""

    label: str
    drawing: Drawing
    index: int
    """第幾張（從 1 開始）。"""
    total: int


@dataclass(frozen=True, slots=True)
class GalleryItem:
    """投票或猜詞時看到的一張畫（只有編號、沒有作者）。"""

    label: str
    drawing: Drawing


@dataclass(frozen=True, slots=True)
class RevealItem:
    """公開時的一張畫。"""

    label: str
    author: PlayerId
    nickname: str
    drawing: Drawing
    flagged: bool
    is_spy: bool
    is_reference: bool
    votes: int


@dataclass(frozen=True, slots=True)
class RevealInfo:
    """公開畫面。"""

    status: str
    """結算狀態，例如 "scored"、"void_reference"、"void_disconnect"。"""
    spy: PlayerId
    answer: str
    hint: str
    items: tuple[RevealItem, ...]


@dataclass(frozen=True, slots=True)
class RoundSummary:
    """分數畫面：本局加減分。"""

    status: str
    normal_delta: Mapping[PlayerId, int]
    disciplinary_delta: Mapping[PlayerId, int]
    total_delta: Mapping[PlayerId, int]
    removed: tuple[PlayerId, ...] = ()


@dataclass(frozen=True, slots=True)
class PlayerView:
    """一位玩家目前的畫面狀態。"""

    phase: Phase = Phase.LOBBY
    attempt_id: int | None = None
    round_no: int = 0
    """伺服器在 DEAL 時固定；作廢補局沿用。"""
    total_rounds: int = 0
    seconds_left: float | None = None
    players: tuple[PlayerInfo, ...] = ()
    is_owner: bool = False
    can_start: bool = False
    settings: Mapping[str, Any] | None = None

    my_role: Role | None = None
    my_text: str | None = None
    """一般玩家＝答案；間諜＝提示。"""
    waiting: bool = False
    """這階段我沒事做，顯示等待畫面。"""

    my_submitted: bool = False
    reference: Drawing | None = None
    """間諜的參考圖。"""

    review_item: ReviewItem | None = None
    flags_left: int = 0
    can_flag: bool = False
    my_flags: frozenset[str] = frozenset()

    gallery: tuple[GalleryItem, ...] = ()
    safe_label: str | None = None
    vote_options: frozenset[str] = frozenset()
    vote_state: VoteState = VoteState.NOT_ELIGIBLE
    my_vote: str | None = None
    must_guess: bool = False

    reveal: RevealInfo | None = None
    last_round: RoundSummary | None = None
    game_over: str | None = None
    """GameOverReason 的值；None＝遊戲進行中。"""
    ranking: tuple[tuple[PlayerId, int, int], ...] = ()
    """(玩家, 分數, 名次)，只含在場玩家。"""
    departed: tuple[tuple[PlayerId, int, str], ...] = ()
    """(玩家, 分數, 原因)，已離開或被移出的人。"""
    snapshot_round: int | None = None
    """分數快照截至第幾回合；None＝尚無分數。"""
    errors: tuple[str, ...] = field(default=())
    """要顯示給玩家的提示，例如「暱稱不可空白」。"""
