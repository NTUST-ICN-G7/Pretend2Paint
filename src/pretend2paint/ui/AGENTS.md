# ui — Canvas / UI

負責人：錢呈恩、李愷哲、石凡可、簡國行

> 先讀根目錄的 `AGENTS.md`。這份檔案只補充本模組的規則；兩者衝突時以根目錄為準，並告訴使用者。
> 對外 API 說明寫在同目錄的 `README.md`（使用 `module-api-doc` skill）。

## 職責
- 遊戲畫面：Landing、等待、畫圖、間諜選圖、公開、投票、結算。
- 畫布：筆畫輸入、顯示畫作。

## 規則
- **UI 框架使用 tkinter**（`docs/decisions/0006-ui-framework.md`）。tkinter 是 Python 內建，**不要 `uv add` 任何 GUI 套件**；需要其他套件先經 team leader 同意。
- 在主執行緒跑 `mainloop()`，用 `root.after()` 定時輪詢 `ui_queue`。
- UI 跑在主執行緒；與網路 / 遊戲邏輯只透過 `queue.Queue` 交換事件（`docs/decisions/0004-threading-model.md`）。**不要在 UI 執行緒做網路 I/O 或任何會阻塞的事**。
- **不做遊戲規則判斷**：UI 只顯示 core 給的狀態、把使用者動作交給 core。
- 可以 import `core`、`common`；不要直接 import `streaming` / `p2p`。
- 畫面上不可顯示玩家不該知道的資訊（例如間諜畫面不能出現答案）。
- 測試：`tests/ui/`（至少測與框架無關的邏輯）

## 完成前
`uv run ruff check . && uv run ruff format --check . && uv run lint-imports && uv run pytest`
