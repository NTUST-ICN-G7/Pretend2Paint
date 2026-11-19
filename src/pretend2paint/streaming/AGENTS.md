# streaming — 通訊協定

負責人：李昇原、黃佑竣

> 先讀根目錄的 `AGENTS.md`。這份檔案只補充本模組的規則；兩者衝突時以根目錄為準，並告訴使用者。
> 對外 API 說明寫在同目錄的 `README.md`（使用 `module-api-doc` skill）。

## 職責
- 封包格式、framing（處理黏包 / 半包）、編解碼。
- 依封包類型分發給上層（core）註冊的 handler。
- 呼叫 p2p 的介面把 bytes 送出去。

## 規則
- **`docs/protocol.md` 是封包格式的唯一來源。** 新增 / 修改封包時使用 `add-packet-type` skill，同一個 PR 內更新文件、`protocol.py`、兩端測試。
- 已發布的 Type 編號**不可重新分配**給別的用途。
- 分發給上層用 callback / handler 註冊，**不可 import `core` 或 `ui`**。
- 不做遊戲規則判斷（例如「誰可以收這個封包」由 core 決定，streaming 只負責照指定的對象送出）。
- 但要遵守機密規則：答案、提示、間諜身分永遠不能用廣播送出。
- 解碼時要能承受壞資料：不可因為一個壞封包讓整條連線或程式掛掉。
- 測試：`tests/streaming/`

## 已知待處理（見 `docs/protocol.md` 待決問題）
- `SPY_SELECT_REF` 盲選應改用 index 而非作者。
- `DRAW_STROKE` / `CANVAS_SNAPSHOT` 在畫圖階段不能廣播。
- Magic 不符時清空整個 buffer、Length 沒有上限。
- `_dispatch_packet` 還沒接到上層 handler。

## 完成前
`uv run ruff check . && uv run ruff format --check . && uv run lint-imports && uv run pytest`
