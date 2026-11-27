"""伺服器計時器的識別碼（DESIGN.md 第 6.2 節）。"""

from dataclasses import dataclass
from enum import StrEnum

from pretend2paint.common.types import Phase


class TimerKind(StrEnum):
    """計時器的用途。"""

    PHASE_END = "phase_end"
    """一般階段結束（DEAL、VOTING、SPY_GUESS、REVEAL、ROUND_END）。"""
    SUBMIT_CLOSE = "submit_close"
    """DRAWING / SPY_ACTION：秒數＋寬限到期，定稿。"""
    REVIEW_ITEM = "review_item"
    """REVIEW：第 step 張播完。"""


@dataclass(frozen=True, slots=True)
class TimerId:
    """一個計時器。伺服器同一時間只認一個 active timer，其他到期事件一律忽略。"""

    token: int
    """伺服器每開一個計時器就 +1，全場唯一。"""
    attempt_id: int
    phase: Phase
    kind: TimerKind
    step: int = 0
    """REVIEW 第幾張；其他為 0。"""
