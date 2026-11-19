"""跨模組共用的基本型別。

這個檔案是各模組之間的契約，修改前請先開 PR 並通知所有模組負責人。
"""

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
    """間諜盲選一張參考圖並畫圖。"""
    REVEAL = "reveal"
    """公開所有畫作，標記被間諜選中的畫作。"""
    VOTING = "voting"
    """投票找出間諜。"""
    SPY_GUESS = "spy_guess"
    """間諜被票出時，猜一次答案。"""
    ROUND_END = "round_end"
    """結算分數，回合結束。"""


class Role(StrEnum):
    """玩家在一回合中的角色。"""

    CIVILIAN = "civilian"
    SPY = "spy"
