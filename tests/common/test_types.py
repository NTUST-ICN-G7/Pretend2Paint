from pretend2paint.common.types import Phase, Role


def test_phase_values_are_unique() -> None:
    assert len({p.value for p in Phase}) == len(Phase)


def test_role_values() -> None:
    assert {r.value for r in Role} == {"civilian", "spy"}
