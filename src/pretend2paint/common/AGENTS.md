# common — 跨模組共用型別

負責人：team leader（banahaker）

> 先讀根目錄的 `AGENTS.md`。這份檔案只補充本模組的規則；兩者衝突時以根目錄為準，並告訴使用者。
> 對外 API 說明寫在同目錄的 `README.md`（使用 `module-api-doc` skill）。

## 職責
放所有模組都會用到的型別與事件定義：`PlayerId`、`Phase`、`Role`，以及之後的事件 dataclass。這裡是**模組之間的契約**。

## 規則
- **只放型別與常數，不放任何邏輯**，也不 import 專案內其他模組（common 是最底層）。
- 修改既有型別會影響所有模組：**一定要先告訴使用者**，由 team leader 決定，並在 PR 中標註所有受影響的模組。
- 新增型別可以，但要有 docstring，並在 PR 說明誰會用到。
- `Phase` 必須與 `docs/game-rules.md` 的流程一致。
- 測試：`tests/common/`

## 完成前
`uv run ruff check . && uv run ruff format --check . && uv run lint-imports && uv run pytest`
