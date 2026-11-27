"""Round Result 畫面的顯示邏輯（成員 D）。

這裡只把 Core 給的 ``PlayerView`` 轉成「畫面上要顯示什麼」，不碰 tkinter，方便測試。
tkinter 畫面在 ``tk_screens.py``。

讀取的欄位（Core PR #16，``core/flow/views.py``，尚未合併）：
``reveal``（RevealInfo）、``last_round``（RoundSummary）、``players``、
``round_no``、``total_rounds``、``ranking``、``game_over``。

UI 不判斷勝負、不計分：標題用 Core 給的結果，分數用 Core 算好的數字。
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

VOID_STATUSES = frozenset({"void_reference", "void_disconnect"})

# 結果類型 → 標題。outcome / guess_correct 目前 Core 的 RevealInfo 還沒有，
# 已請 Core 補上（Streaming PR #17 的 ROUND_RESULT 已有同名欄位）。
_TITLES: dict[tuple[str, bool | None], str] = {
    ("escaped", None): "間諜成功潛伏！",
    ("caught", True): "間諜被抓到了，但猜中答案！",
    ("caught", False): "間諜被抓到了！",
    ("tie", True): "平票！間諜猜中答案",
    ("tie", False): "平票！間諜沒猜中",
}
_VOID_TITLES = {
    "void_reference": "本局作廢！參考圖違規，重新開局",
    "void_disconnect": "本局作廢！有玩家斷線，重新開局",
}


@dataclass(frozen=True, slots=True)
class DrawingRow:
    """畫作表的一列。"""

    label: str
    author: str
    votes: int
    note: str
    """備註，例如「間諜」「參考圖」「違規」，用「、」連接。"""


@dataclass(frozen=True, slots=True)
class ScoreRow:
    """分數表的一列。"""

    name: str
    delta: int
    total: int
    removed: bool


@dataclass(frozen=True, slots=True)
class RoundResultModel:
    """Round Result 畫面要顯示的內容。"""

    heading: str
    """例如「第 1 / 5 回合結果」。"""
    title: str
    is_void: bool
    spy_name: str | None
    answer: str | None
    hint: str | None
    spy_guess: str | None
    guess_correct: bool | None
    drawings: tuple[DrawingRow, ...]
    scores: tuple[ScoreRow, ...]
    removed_names: tuple[str, ...]
    is_game_over: bool
    ranking: tuple[tuple[int, str, int], ...]
    """(名次, 名字, 分數)，只在遊戲結束時有內容。"""


def _nicknames(view: Any) -> dict[str, str]:
    return {p.id: p.nickname for p in getattr(view, "players", ())}


def _totals(view: Any) -> dict[str, int]:
    return {p.id: p.score for p in getattr(view, "players", ())}


def _heading(view: Any) -> str:
    round_no = getattr(view, "round_no", 0)
    total = getattr(view, "total_rounds", 0)
    if round_no and total:
        return f"第 {round_no} / {total} 回合結果"
    if round_no:
        return f"第 {round_no} 回合結果"
    return "回合結果"


def _title(status: str | None, outcome: str | None, guess_correct: bool | None) -> str:
    if status in _VOID_TITLES:
        return _VOID_TITLES[status]
    if outcome == "escaped":
        return _TITLES[("escaped", None)]
    if outcome is not None and guess_correct is not None:
        return _TITLES.get((outcome, guess_correct), "回合結束")
    # Core 還沒給 outcome 時的保守寫法：不自己判斷勝負。
    return "回合結束"


def _drawing_rows(reveal: Any) -> tuple[DrawingRow, ...]:
    rows = []
    for item in getattr(reveal, "items", ()):
        notes = []
        if getattr(item, "is_spy", False):
            notes.append("間諜")
        if getattr(item, "is_reference", False):
            notes.append("參考圖")
        if getattr(item, "flagged", False):
            notes.append("違規")
        rows.append(
            DrawingRow(
                label=item.label,
                author=item.nickname,
                votes=item.votes,
                note="、".join(notes),
            )
        )
    return tuple(rows)


def _score_rows(view: Any, names: Mapping[str, str]) -> tuple[ScoreRow, ...]:
    summary = getattr(view, "last_round", None)
    if summary is None:
        return ()
    deltas: Mapping[str, int] = summary.total_delta
    removed = set(getattr(summary, "removed", ()))
    totals = _totals(view)
    player_ids = list(names) or list(deltas)
    for pid in [*deltas, *removed]:
        if pid not in player_ids:
            player_ids.append(pid)
    return tuple(
        ScoreRow(
            name=names.get(pid, pid),
            delta=deltas.get(pid, 0),
            total=totals.get(pid, 0),
            removed=pid in removed,
        )
        for pid in player_ids
    )


def round_result_model(view: Any) -> RoundResultModel:
    """把 ``PlayerView`` 轉成 Round Result 畫面的內容。"""
    names = _nicknames(view)
    reveal = getattr(view, "reveal", None)
    summary = getattr(view, "last_round", None)

    status = getattr(reveal, "status", None) or getattr(summary, "status", None)
    is_void = status in VOID_STATUSES
    outcome = getattr(reveal, "outcome", None)
    guess_correct = getattr(reveal, "guess_correct", None)

    spy_id = None if is_void else getattr(reveal, "spy", None)
    spy_name = None if spy_id is None else names.get(spy_id, spy_id)

    removed_ids = tuple(getattr(summary, "removed", ()))
    ranking = ()
    game_over = getattr(view, "game_over", None)
    if game_over is not None:
        ranking = tuple(
            (rank, names.get(pid, pid), score) for pid, score, rank in getattr(view, "ranking", ())
        )

    return RoundResultModel(
        heading=_heading(view),
        title=_title(status, outcome, guess_correct),
        is_void=is_void,
        spy_name=spy_name,
        # 作廢時不公開答案與提示（依 Streaming PR #17 的 ROUND_RESULT 規則）。
        answer=None if is_void else getattr(reveal, "answer", None),
        hint=None if is_void else getattr(reveal, "hint", None),
        spy_guess=None if is_void else getattr(reveal, "spy_guess", None),
        guess_correct=None if is_void else guess_correct,
        drawings=() if is_void else _drawing_rows(reveal),
        scores=_score_rows(view, names),
        removed_names=tuple(names.get(pid, pid) for pid in removed_ids),
        is_game_over=game_over is not None,
        ranking=ranking,
    )


def format_delta(delta: int) -> str:
    """分數變化加上正負號，例如 ``+8``、``-3``、``+0``。"""
    return f"{delta:+d}"
