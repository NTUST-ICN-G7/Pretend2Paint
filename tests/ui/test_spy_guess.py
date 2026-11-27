from types import SimpleNamespace as NS

from pretend2paint.ui.spy_guess import (
    SUBMITTED_MESSAGE,
    WAITING_MESSAGE,
    normalize_guess,
    spy_guess_model,
)


def test_spy_who_must_guess_sees_hint_and_input() -> None:
    model = spy_guess_model(NS(must_guess=True, my_text="兩個字的水果", seconds_left=14.7))
    assert model.can_guess
    assert model.hint == "兩個字的水果"
    assert model.seconds_left == 14


def test_other_players_wait_and_never_see_hint() -> None:
    # 即使 view 帶了 my_text（一般玩家的答案），不用猜的人也不顯示任何提示或答案。
    model = spy_guess_model(NS(must_guess=False, my_text="西瓜", seconds_left=10))
    assert not model.can_guess
    assert model.hint is None
    assert model.message == WAITING_MESSAGE


def test_after_submit_input_is_locked() -> None:
    view = NS(must_guess=True, my_text="兩個字的水果", seconds_left=5)
    model = spy_guess_model(view, submitted=True)
    assert not model.can_guess
    assert model.message == SUBMITTED_MESSAGE


def test_missing_fields_fall_back_to_waiting() -> None:
    model = spy_guess_model(NS())
    assert not model.can_guess
    assert model.seconds_left is None


def test_negative_seconds_clamp_to_zero() -> None:
    assert spy_guess_model(NS(must_guess=True, my_text="x", seconds_left=-1)).seconds_left == 0


def test_normalize_guess() -> None:
    assert normalize_guess("  西瓜 ") == "西瓜"
    assert normalize_guess("   ") is None
    assert normalize_guess("") is None
