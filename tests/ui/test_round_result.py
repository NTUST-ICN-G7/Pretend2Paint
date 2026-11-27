from types import SimpleNamespace as NS

from pretend2paint.ui.round_result import format_delta, round_result_model

PLAYERS = (
    NS(id="p1", nickname="Alice", score=8),
    NS(id="p2", nickname="Bob", score=0),
    NS(id="p3", nickname="Charlie", score=-3),
    NS(id="p4", nickname="Dave", score=0),
)


def _item(label, nickname, votes, *, spy=False, ref=False, flagged=False):
    return NS(
        label=label,
        nickname=nickname,
        votes=votes,
        is_spy=spy,
        is_reference=ref,
        flagged=flagged,
    )


def _view(**reveal_overrides):
    reveal = dict(
        status="scored",
        spy="p3",
        answer="西瓜",
        hint="兩個字的水果",
        items=(
            _item("#1", "Alice", 0),
            _item("#2", "Bob", 0, ref=True),
            _item("#3", "Charlie", 2, spy=True),
            _item("#4", "Dave", 1),
        ),
    )
    reveal.update(reveal_overrides)
    return NS(
        players=PLAYERS,
        round_no=1,
        total_rounds=5,
        reveal=NS(**reveal),
        last_round=NS(status="scored", total_delta={"p1": 8, "p3": -3}, removed=()),
        game_over=None,
        ranking=(),
    )


def test_caught_and_wrong_guess() -> None:
    model = round_result_model(_view(outcome="caught", guess_correct=False, spy_guess="哈密瓜"))
    assert model.heading == "第 1 / 5 回合結果"
    assert model.title == "間諜被抓到了！"
    assert model.spy_name == "Charlie"
    assert model.answer == "西瓜"
    assert model.spy_guess == "哈密瓜"
    assert model.guess_correct is False


def test_titles_for_each_outcome() -> None:
    cases = {
        ("escaped", None): "間諜成功潛伏！",
        ("caught", True): "間諜被抓到了，但猜中答案！",
        ("tie", True): "平票！間諜猜中答案",
        ("tie", False): "平票！間諜沒猜中",
    }
    for (outcome, correct), title in cases.items():
        assert round_result_model(_view(outcome=outcome, guess_correct=correct)).title == title


def test_without_outcome_ui_does_not_guess_the_result() -> None:
    # Core 的 RevealInfo 目前沒有 outcome，UI 不自己用票數判斷勝負。
    assert round_result_model(_view()).title == "回合結束"


def test_drawing_rows_mark_spy_and_reference() -> None:
    rows = {row.label: row for row in round_result_model(_view()).drawings}
    assert rows["#3"].note == "間諜"
    assert rows["#2"].note == "參考圖"
    assert rows["#1"].note == ""
    assert rows["#3"].votes == 2


def test_scores_use_core_numbers_for_every_player() -> None:
    scores = {s.name: s for s in round_result_model(_view()).scores}
    assert set(scores) == {"Alice", "Bob", "Charlie", "Dave"}
    assert (scores["Alice"].delta, scores["Alice"].total) == (8, 8)
    assert (scores["Bob"].delta, scores["Bob"].total) == (0, 0)
    assert scores["Charlie"].delta == -3


def test_void_round_hides_answer_spy_and_drawings() -> None:
    view = _view(status="void_reference")
    view.last_round = NS(status="void_reference", total_delta={"p2": -15}, removed=())
    model = round_result_model(view)
    assert model.is_void
    assert model.title == "本局作廢！參考圖違規，重新開局"
    assert model.spy_name is None
    assert model.answer is None
    assert model.hint is None
    assert model.drawings == ()
    assert {s.name: s.delta for s in model.scores}["Bob"] == -15


def test_removed_player_is_listed() -> None:
    view = _view()
    view.last_round = NS(status="scored", total_delta={"p2": -15}, removed=("p2",))
    model = round_result_model(view)
    assert model.removed_names == ("Bob",)
    assert {s.name: s.removed for s in model.scores}["Bob"] is True


def test_game_over_shows_ranking() -> None:
    view = _view()
    view.game_over = "completed"
    view.ranking = (("p1", 20, 1), ("p3", 5, 2))
    model = round_result_model(view)
    assert model.is_game_over
    assert model.ranking == ((1, "Alice", 20), (2, "Charlie", 5))


def test_format_delta() -> None:
    assert format_delta(8) == "+8"
    assert format_delta(-3) == "-3"
    assert format_delta(0) == "+0"
