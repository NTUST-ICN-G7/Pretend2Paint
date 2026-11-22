# core — 遊戲核心邏輯

負責人：張瀚元、鄒聿銘

> 先讀根目錄的 `AGENTS.md`。這份檔案只補充本模組的規則；兩者衝突時以根目錄為準，並告訴使用者。
> 對外 API 說明寫在同目錄的 `README.md`（使用 `module-api-doc` skill）。

## 職責
- 遊戲狀態機（`common.types.Phase`）：依 `docs/game-rules.md` 推進回合。
- 房主邏輯：出題、指定間諜、收畫作、收票、計分（`docs/decisions/0003-host-authority.md`）。
- 決定每個訊息要送給誰。

## 規則
- **純邏輯，不做 I/O**：不直接開 socket、不碰 UI、不讀寫檔案（題庫可以由外部傳入）。輸入是事件，輸出是「要送出的訊息 + 對象」與「狀態變化」。
- 可以 import `streaming`、`p2p`、`common`；**不可 import `ui`**。要通知 UI 就發事件 / 呼叫註冊的 callback。
- **機密規則**：答案、提示、間諜身分只能單播；`Phase.REVEAL` 前不能把畫作發給房主以外的人（`docs/decisions/0005-secret-information.md`）。
- 隨機性（選間諜、出題）要能注入 `random.Random` 實例，讓測試可以固定結果。
- 規則有不清楚的地方（平票、一般玩家計分等），**不要自己發明**：先問使用者，決定後更新 `docs/game-rules.md`。
- 每個階段轉換與計分情況都要有測試：`tests/core/`

## 完成前
`uv run ruff check . && uv run ruff format --check . && uv run lint-imports && uv run pytest`
