---
name: add-packet-type
description: 在 Pretend2Paint 新增或修改通訊封包類型（PacketType）。會同步更新 docs/protocol.md、streaming/protocol.py、送收兩端與測試。任何要新增訊息種類、改 payload 欄位、或改封包傳送對象的任務都要使用。
---

# 新增 / 修改封包

封包格式的唯一來源是 `docs/protocol.md`。以下步驟**必須在同一個 PR 內全部完成**。

## 0. 確認權限
封包屬於 `streaming` 模組（負責人：李昇原、黃佑竣）。如果使用者不是 streaming 負責人，先告訴使用者這會改到 streaming，建議請 streaming 組實作或 review。

## 1. 設計（先寫進文件）
在 `docs/protocol.md` 的封包表格新增或修改一列，寫清楚：
- **Type 編號**：取目前最大值 + 1。**不可重用**已發布或已刪除的編號。
- **名稱**：`UPPER_SNAKE_CASE`
- **方向**：誰送給誰（例如「房主 → 每位玩家」）
- **傳送方式**：廣播 / 單播 / → 房主
- **Payload**：每個欄位的名稱、型別、意義

### 機密檢查（必做）
對照 `docs/decisions/0005-secret-information.md`：
- payload 有答案、提示、間諜身分 → **必須單播**。
- payload 有 `Phase.REVEAL` 前的畫作 → **只能送給房主**。
- 廣播封包的 payload 不可包含上述任何資訊（也不可包含能推導出來的欄位，例如 `is_spy`）。

設計不確定時，先把表格給使用者確認再寫程式。

## 2. 實作
1. `src/pretend2paint/streaming/protocol.py`：在 `PacketType` 加常數。
2. `src/pretend2paint/streaming/manager.py`：
   - 加送出方法 `send_<name>(target_peers, ...)`，參數明確列出（不要只收一個 dict）。
   - 在分發處理加上新類型，交給上層註冊的 handler。
3. 如果 payload 的欄位會被其他模組使用，對應型別放在 `common/`（這會改到 common，要告訴使用者）。

## 3. 測試（`tests/streaming/`）
至少包含：
- 編碼 → 解碼後 payload 不變。
- 送出方法使用了正確的 type 與正確的對象（單播時 `targets` 不可為空）。
- 收到時有分發給對應的 handler。

## 4. 檢查
```bash
uv run ruff check . && uv run ruff format --check . && uv run lint-imports && uv run pytest
```

## 5. PR 說明
列出新封包的表格列，並 @ 會使用到這個封包的模組負責人（通常是 core）。
