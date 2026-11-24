from __future__ import annotations

import json

import pytest

from pretend2paint.core.part_b import (
    GameConfig,
    Phase,
    RuleError,
    ScoreRules,
    default_phase_seconds,
)


def test_default_settings_current_contract() -> None:
    config = GameConfig()
    assert config.rounds == 5
    assert (config.min_players, config.max_players) == (4, 7)
    assert config.spy_pick_seconds == 10
    assert config.phase_seconds[Phase.DEAL] == 5
    assert config.phase_seconds[Phase.DRAWING] == 30
    assert config.phase_seconds[Phase.SPY_ACTION] == 30
    assert config.phase_seconds[Phase.REVEAL] == 5
    assert config.phase_seconds[Phase.REVIEW] == 5
    assert config.phase_seconds[Phase.VOTING] == 20
    assert config.phase_seconds[Phase.SPY_GUESS] == 15
    assert config.phase_seconds[Phase.ROUND_END] == 5
    assert Phase.LOBBY not in config.phase_seconds
    assert config.validate() == []


def test_default_score_table() -> None:
    assert ScoreRules() == ScoreRules(3, 1, -3, 5, 8)


def test_config_json_roundtrip() -> None:
    original = GameConfig(rounds=2, spy_pick_seconds=6)
    packet = json.loads(json.dumps(original.to_payload(), ensure_ascii=False))
    restored = GameConfig.from_payload(packet)
    assert restored.to_payload() == packet
    assert set(restored.phase_seconds) == set(default_phase_seconds())


@pytest.mark.parametrize("rounds", [0, -1, 101, 1.0, True, "5"])
def test_reject_invalid_rounds(rounds) -> None:
    assert GameConfig(rounds=rounds).validate()
    with pytest.raises(RuleError):
        GameConfig.from_payload({"rounds": rounds})


@pytest.mark.parametrize(
    "fields",
    [
        {"min_players": 3},
        {"max_players": 8},
        {"min_players": 7, "max_players": 4},
        {"min_players": True},
        {"max_players": "7"},
    ],
)
def test_reject_invalid_player_ranges(fields) -> None:
    assert GameConfig(**fields).validate()


@pytest.mark.parametrize("seconds", [0, -1, float("inf"), float("nan"), True, "30"])
def test_reject_invalid_seconds(seconds) -> None:
    assert GameConfig(spy_pick_seconds=seconds).validate()


def test_legacy_pick_timer_does_not_restrict_auto_pick() -> None:
    assert GameConfig(spy_pick_seconds=31).validate() == []


def test_missing_phase_is_rejected() -> None:
    values = default_phase_seconds()
    del values[Phase.REVEAL]
    assert GameConfig(phase_seconds=values).validate()


def test_unknown_phase_is_rejected_from_packet() -> None:
    with pytest.raises(RuleError):
        GameConfig.from_payload({"phase_seconds": {"NOPE": 10}})


def test_partial_phase_map_is_rejected() -> None:
    with pytest.raises(RuleError):
        GameConfig.from_payload({"phase_seconds": {"DEAL": 5}})


def test_unknown_config_field_is_rejected() -> None:
    with pytest.raises(RuleError):
        GameConfig.from_payload({"surprise": 42})


@pytest.mark.parametrize("bad_score", [{"invalid": 99}, {"spy_escape": 1.2}, {"spy_escape": True}])
def test_bad_score_is_rejected(bad_score) -> None:
    with pytest.raises(RuleError):
        GameConfig.from_payload({"score": bad_score})


def test_score_customization_and_serialization() -> None:
    score = ScoreRules(spy_escape=4, civilian_hit=3)
    payload = GameConfig(score=score).to_payload()
    assert GameConfig.from_payload(payload).score == score
