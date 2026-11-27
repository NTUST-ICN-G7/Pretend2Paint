"""跨模組共用的基本型別。

這個檔案是各模組之間的契約，修改前請先開 PR 並通知所有模組負責人。
"""

from dataclasses import dataclass
from enum import StrEnum

type PlayerId = str
"""玩家（節點）的唯一識別碼。"""


class Phase(StrEnum):
    """回合階段，對應 docs/game-rules.md 的流程。"""

    LOBBY = "lobby"
    """局外 Landing space：發現節點、加入房間。"""
    DEAL = "deal"
    """發題：一般玩家拿答案、間諜拿提示。"""
    DRAWING = "drawing"
    """一般玩家畫圖，畫作尚未公開。"""
    SPY_ACTION = "spy_action"
    """伺服器自動抽一張一般玩家的畫給間諜參考，間諜畫圖。"""
    REVIEW = "review"
    """審查：所有畫作以匿名編號逐張給一般玩家看，可檢舉含文字的畫。"""
    VOTING = "voting"
    """一般玩家匿名投票找出間諜。"""
    SPY_GUESS = "spy_guess"
    """間諜被票出或平票時，猜一次答案。"""
    REVEAL = "reveal"
    """結果確定後，公開所有畫作、作者、答案與間諜。"""
    ROUND_END = "round_end"
    """結算分數，回合結束。"""


class Role(StrEnum):
    """玩家在一回合中的角色。"""

    CIVILIAN = "civilian"
    SPY = "spy"


@dataclass(frozen=True, slots=True)
class Stroke:
    """畫布上的一筆。

    座標與粗細都用相對畫布大小的比例（0～1），不同螢幕大小都能正確顯示。
    """

    color: str
    """顏色，格式為 "#RRGGBB"。"""
    width: float
    """筆畫粗細，為畫布寬度的比例，例如 0.01。"""
    points: tuple[tuple[float, float], ...]
    """依序經過的點 (x, y)，0 ≤ x, y ≤ 1。"""


@dataclass(frozen=True, slots=True)
class Drawing:
    """一張畫作，由多個筆畫組成。"""

    strokes: tuple[Stroke, ...] = ()

    @property
    def is_blank(self) -> bool:
        """沒有任何筆畫時為 True。"""
        return not self.strokes


BLANK_DRAWING = Drawing()
"""空白畫作；玩家沒交畫時使用。"""
