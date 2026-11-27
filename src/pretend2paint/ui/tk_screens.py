"""成員 D 的 tkinter 畫面：Spy Guess、Round Result（骨架）。

每個畫面都是一個 ``tk.Frame``，對外只有兩件事：

- ``show(view)``：收到 Core 的新 ``PlayerView`` 時呼叫，重畫畫面。
- 建構時傳入的 callback：玩家操作時呼叫，由 UI 主程式轉成 Core 的指令放進 queue。

畫面本身不碰 queue、不碰網路，也不判斷規則（ADR 0004、ui/AGENTS.md）。
顯示內容由 ``spy_guess.py``、``round_result.py`` 決定，這裡只負責排版。

預覽（用假資料，不需要連線）::

    uv run python -m pretend2paint.ui.tk_screens
"""

import tkinter as tk
from collections.abc import Callable
from typing import Any

from pretend2paint.ui.round_result import format_delta, round_result_model
from pretend2paint.ui.spy_guess import normalize_guess, spy_guess_model

PAD = 12
TITLE_FONT = ("TkDefaultFont", 20, "bold")
HEADING_FONT = ("TkDefaultFont", 14, "bold")


class SpyGuessScreen(tk.Frame):
    """Spy Guess 畫面。

    :param on_guess: 間諜按下送出時呼叫，參數是整理過的答案文字。
        UI 主程式負責轉成 Core 的 ``GuessWord(text=...)`` 放進 queue。
    """

    def __init__(self, master: tk.Misc, on_guess: Callable[[str], None]) -> None:
        super().__init__(master, padx=PAD, pady=PAD)
        self._on_guess = on_guess
        self._submitted = False
        self._view: Any = None

        self._message = tk.Label(self, font=HEADING_FONT, wraplength=480, justify="center")
        self._hint = tk.Label(self)
        self._timer = tk.Label(self)
        self._entry_var = tk.StringVar()
        self._entry_var.trace_add("write", lambda *_: self._refresh_button())
        self._entry = tk.Entry(self, textvariable=self._entry_var, width=24)
        self._entry.bind("<Return>", lambda _event: self._submit())
        self._button = tk.Button(self, text="送出答案", command=self._submit)

        for widget in (self._message, self._hint, self._timer, self._entry, self._button):
            widget.pack(pady=4)

    def show(self, view: Any) -> None:
        """依照新的 ``PlayerView`` 重畫。"""
        self._view = view
        model = spy_guess_model(view, submitted=self._submitted)
        self._message.config(text=model.message)
        self._hint.config(text=f"你的提示：{model.hint}" if model.hint else "")
        self._timer.config(
            text="" if model.seconds_left is None else f"剩餘時間：{model.seconds_left}s"
        )
        state = "normal" if model.can_guess else "disabled"
        self._entry.config(state=state)
        if model.hint is None:
            self._entry.pack_forget()
            self._button.pack_forget()
        else:
            self._entry.pack(pady=4)
            self._button.pack(pady=4)
        self._refresh_button()

    def reset(self) -> None:
        """新回合開始時呼叫，清掉上一回合的輸入與送出狀態。"""
        self._submitted = False
        self._entry_var.set("")

    def _refresh_button(self) -> None:
        can_guess = (
            self._view is not None
            and spy_guess_model(self._view, submitted=self._submitted).can_guess
        )
        has_text = normalize_guess(self._entry_var.get()) is not None
        self._button.config(state="normal" if can_guess and has_text else "disabled")

    def _submit(self) -> None:
        guess = normalize_guess(self._entry_var.get())
        if guess is None or self._submitted or self._view is None:
            return
        if not spy_guess_model(self._view).can_guess:
            return
        self._submitted = True
        self._on_guess(guess)
        self.show(self._view)


class RoundResultScreen(tk.Frame):
    """Round Result 畫面（含作廢局與遊戲結束的排名）。

    :param on_leave: 玩家按「離開房間」時呼叫。
    """

    def __init__(self, master: tk.Misc, on_leave: Callable[[], None]) -> None:
        super().__init__(master, padx=PAD, pady=PAD)
        self._on_leave = on_leave
        self._body = tk.Frame(self)
        self._body.pack(fill="both", expand=True)
        tk.Button(self, text="離開房間", command=self._on_leave).pack(pady=(PAD, 0))

    def show(self, view: Any) -> None:
        """依照新的 ``PlayerView`` 重畫。"""
        for child in self._body.winfo_children():
            child.destroy()
        model = round_result_model(view)
        body = self._body

        tk.Label(body, text=model.heading).pack()
        tk.Label(body, text=model.title, font=TITLE_FONT).pack(pady=(4, PAD))

        if not model.is_void:
            if model.spy_name:
                tk.Label(body, text=f"間諜是：{model.spy_name}").pack()
            if model.answer:
                tk.Label(body, text=f"答案：{model.answer}　　間諜拿到的提示：{model.hint}").pack()
            if model.spy_guess is not None:
                verdict = {True: "正確", False: "錯誤"}.get(model.guess_correct, "")
                tk.Label(body, text=f"間諜猜：{model.spy_guess}（{verdict}）").pack()
            if model.drawings:
                self._table(
                    body,
                    "畫作",
                    ("畫作", "作者", "得票", "備註"),
                    [(d.label, d.author, str(d.votes), d.note) for d in model.drawings],
                )

        if model.scores:
            self._table(
                body,
                "分數",
                ("玩家", "本回合", "總分"),
                [
                    (
                        s.name + ("（已移出）" if s.removed else ""),
                        format_delta(s.delta),
                        str(s.total),
                    )
                    for s in model.scores
                ],
            )

        for name in model.removed_names:
            tk.Label(body, text=f"{name} 已被移出本場遊戲", fg="red").pack()

        if model.is_game_over:
            self._table(
                body,
                "最終排名",
                ("名次", "玩家", "分數"),
                [(str(rank), name, str(score)) for rank, name, score in model.ranking],
            )
        else:
            tk.Label(body, text="即將進入下一回合……").pack(pady=(PAD, 0))

    @staticmethod
    def _table(
        master: tk.Misc, title: str, header: tuple[str, ...], rows: list[tuple[str, ...]]
    ) -> None:
        tk.Label(master, text=title, font=HEADING_FONT).pack(pady=(PAD, 2))
        grid = tk.Frame(master)
        grid.pack()
        for col, text in enumerate(header):
            tk.Label(grid, text=text, font=("TkDefaultFont", 12, "bold"), padx=8).grid(
                row=0, column=col
            )
        for row_no, row in enumerate(rows, start=1):
            for col, text in enumerate(row):
                tk.Label(grid, text=text, padx=8).grid(row=row_no, column=col)


def _demo() -> None:
    """用假資料預覽兩個畫面（不連線）。"""
    from types import SimpleNamespace as NS

    players = (
        NS(id="p1", nickname="Alice", score=8),
        NS(id="p2", nickname="Bob", score=0),
        NS(id="p3", nickname="Charlie", score=-3),
        NS(id="p4", nickname="Dave", score=0),
    )
    guess_view = NS(must_guess=True, my_text="兩個字的水果", seconds_left=15.0)
    result_view = NS(
        players=players,
        round_no=1,
        total_rounds=5,
        reveal=NS(
            status="scored",
            outcome="caught",
            guess_correct=False,
            spy_guess="哈密瓜",
            spy="p3",
            answer="西瓜",
            hint="兩個字的水果",
            items=(
                NS(
                    label="#1",
                    nickname="Alice",
                    votes=0,
                    is_spy=False,
                    is_reference=False,
                    flagged=False,
                ),
                NS(
                    label="#2",
                    nickname="Bob",
                    votes=0,
                    is_spy=False,
                    is_reference=True,
                    flagged=False,
                ),
                NS(
                    label="#3",
                    nickname="Charlie",
                    votes=2,
                    is_spy=True,
                    is_reference=False,
                    flagged=False,
                ),
                NS(
                    label="#4",
                    nickname="Dave",
                    votes=1,
                    is_spy=False,
                    is_reference=False,
                    flagged=False,
                ),
            ),
        ),
        last_round=NS(status="scored", total_delta={"p1": 8, "p3": -3}, removed=()),
        game_over=None,
        ranking=(),
    )

    root = tk.Tk()
    root.title("成員 D 畫面預覽")
    guess = SpyGuessScreen(root, on_guess=lambda text: print("GuessWord:", text))
    guess.pack(side="left", fill="y")
    tk.Frame(root, width=2, bg="gray").pack(side="left", fill="y")
    result = RoundResultScreen(root, on_leave=lambda: print("LeaveRoom"))
    result.pack(side="left", fill="both", expand=True)
    guess.show(guess_view)
    result.show(result_view)
    root.mainloop()


if __name__ == "__main__":
    _demo()
