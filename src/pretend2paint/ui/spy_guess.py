"""Spy Guess 畫面的顯示邏輯（成員 D）。

這裡只把 Core 給的 ``PlayerView`` 轉成「畫面上要顯示什麼」，不碰 tkinter，方便測試。
tkinter 畫面在 ``tk_screens.py``。

``PlayerView`` 由 Core 定義（PR #16，``core/flow/views.py``，尚未合併），
這裡只讀取需要的欄位，用 ``getattr`` 讀，Core 合併後不用改這個檔案。
"""

from dataclasses import dataclass
from typing import Any

WAITING_MESSAGE = "投票結束！間諜正在猜答案……"
SUBMITTED_MESSAGE = "已送出，等待結果……"


@dataclass(frozen=True, slots=True)
class SpyGuessModel:
    """Spy Guess 畫面要顯示的內容。"""

    can_guess: bool
    """True＝這位玩家是要猜答案的間諜，顯示輸入框。"""
    hint: str | None
    """間諜的提示；不是間諜時一律為 None（不可外洩給其他玩家）。"""
    message: str
    seconds_left: int | None
    """倒數秒數（無條件捨去）；Core 沒給時為 None。"""


def spy_guess_model(view: Any, *, submitted: bool = False) -> SpyGuessModel:
    """把 ``PlayerView`` 轉成 Spy Guess 畫面的內容。

    :param view: Core 的 ``PlayerView``（需要 ``must_guess``、``my_text``、``seconds_left``）
    :param submitted: UI 這邊是否已經按過送出（送出後鎖住，等 Core 結算）
    """
    must_guess = bool(getattr(view, "must_guess", False))
    seconds = getattr(view, "seconds_left", None)
    seconds_left = None if seconds is None else max(0, int(seconds))

    if not must_guess:
        return SpyGuessModel(
            can_guess=False, hint=None, message=WAITING_MESSAGE, seconds_left=seconds_left
        )

    hint = getattr(view, "my_text", None)
    if submitted:
        return SpyGuessModel(
            can_guess=False, hint=hint, message=SUBMITTED_MESSAGE, seconds_left=seconds_left
        )
    return SpyGuessModel(
        can_guess=True,
        hint=hint,
        message="你的畫作在最高票中！猜猜看一般玩家的答案是什麼？（只有一次機會）",
        seconds_left=seconds_left,
    )


def normalize_guess(text: str) -> str | None:
    """整理輸入框的文字；空白回傳 None（送出按鈕不能按）。

    只去掉前後空白，猜對猜錯由 Core 判斷，UI 不比對答案。
    """
    cleaned = text.strip()
    return cleaned or None
