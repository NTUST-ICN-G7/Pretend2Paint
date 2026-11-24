# core — 遊戲核心邏輯 / Game Core

負責人：張瀚元、鄒聿銘。

## 概觀 / Overview

目前這個 PR **只提交 Part B v1.2.0 候選規則函式庫供審查**，尚未連接團隊的 Host/Streaming/UI。模組為純邏輯、沒有網路 I/O；僅依賴 Python 標準函式庫。

This PR contributes a **review-only Part B v1.2.0 rule package**. It is not yet connected to the team Host/Streaming/UI engines, and it performs no network I/O.

**整合阻礙 / Decision conflict:** `docs/decisions/0003-host-authority.md` 確立真人 Host 為權威節點，但 v1.2.0 的設計假定所有真人都參賽，另由自動裁判管理秘密。**請組長與 Core A 負責人確認正式架構後再合併／串接。**

## 公開 API / Public API

The complete provisional public interface is exported in `pretend2paint.core.part_b.__init__` without modifying `common/types.py` or other modules.

```python
from pretend2paint.core.part_b import (
    GameConfig,
    ScoreRules,
    WordBank,
    choose_spy,
    build_anonymity_map,
    ModerationLedger,
    review_round,
    RoundProgress,
    settle_round,
    RoundStatus,
)
```

`GameConfig` controls rounds/timing, `WordBank` supplies vetted answer/hint pairs, `choose_spy` implements weighted random spy assignment, `build_anonymity_map` creates private labels, `review_round` resolves limited civilian-only violation votes, and `settle_round` applies void/scored outcomes with completed-round accounting.

詳細簽名、參數、錯誤、可見性與呼叫順序：[`part_b_docs/INTEGRATION.md`](part_b_docs/INTEGRATION.md)。本資料夾原有 A 模組程式不在此 PR 中實作或修改。

## 快速檢查 / Quick checks

```bash
uv run python -m pretend2paint.core.part_b.examples.rules_demo
uv run pytest tests/core/test_part_b_*.py
```

## 和其他模組約定 / Integration boundaries

- Part A must authenticate senders, own timers/state, and call rule functions.
- Part B does not transmit secrets or drawings. All private mappings and moderation records must stay on the authoritative process.
- Phase/Role representations in this proposal are **not** yet synchronized with `pretend2paint.common.types`; the current team protocol/ADR remains authoritative until reviewed.
- Production integration may require a separate agreed PR for `common/`, `docs/game-rules.md`, `docs/protocol.md`, and team ADRs. No such cross-module changes are proposed here.

## 尚未完成 / Not done

- [ ] Align host/referee model and phase/role enums with the approved team decisions.
- [ ] Agree on packet contracts with Streaming and state transitions with Core A.
- [ ] Run full project CI against Python 3.14, uv-managed dependencies, and real multiplayer integration.
