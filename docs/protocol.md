# 通訊協定

> 這份文件是封包格式的**唯一來源**。新增或修改封包時，必須同一個 PR 內同步更新：
> 本文件、`streaming/protocol.py`、送出端與接收端的測試。（agent 請使用 `add-packet-type` skill）

負責模組：`streaming`（李昇原、黃佑竣）

## Framing

每個封包 = 7 bytes header + JSON payload（UTF-8，頂層必須是 JSON 物件）。整數皆為 network byte order（big-endian）。

| 欄位 | 大小 | 說明 |
| :--- | :--- | :--- |
| Magic | 2 bytes | 固定 `0x49 0x43`（`"IC"`） |
| Type | 1 byte | 封包類型，見下表 |
| Length | 4 bytes | payload 長度（bytes），上限 4 MiB（`MAX_PAYLOAD_SIZE`） |
| Payload | Length bytes | JSON 物件 |

## 封包類型

傳送方式：**廣播** = 發給房間所有人；**單播** = 只發給特定玩家；**→ 房主** = 只發給房主。
streaming 的程式只允許 `ROUND_STATE_SYNC` 與 `ROUND_RESULT` 廣播，其餘一律要明確指定對象。

| Type | 名稱 | 方向 | 傳送方式 | Payload |
| :--- | :--- | :--- | :--- | :--- |
| `0x01` | `DRAW_STROKE` | 畫圖者 → 指定對象 | 單播（見待決 #1） | `{"x", "y", "color", ...}`，欄位由 Canvas 決定，streaming 不檢查 |
| `0x02` | `SPY_SELECT_REF` | 間諜 → 房主 | → 房主 | `{"index": int}`：盲選第幾張，由房主對應到作者 |
| `0x03` | `ROUND_STATE_SYNC` | 房主 → 所有人 | 廣播 | `{"state": str}`，值為 `common.types.Phase` 的值 |
| `0x04` | `CANVAS_SNAPSHOT` | 畫圖者 → 房主；房主 → 所有人（`REVEAL` 時） | 單播（房主公開時逐一送給每位玩家） | `{"image": str}`；公開時房主可加 `"author": PlayerId`、`"index": int`、`"marked": bool`。`image` 為 base64 PNG（暫定，見待決 #2） |
| `0x05` | `DEAL_WORD` | 房主 → 每位玩家 | **單播，一次一人** | `{"text": str}`：一般玩家是答案，間諜是提示 |
| `0x06` | `SPY_REFERENCE` | 房主 → 間諜 | **單播，一次一人** | `{"image": str}`：間諜選中的參考圖，**不含作者** |
| `0x07` | `VOTE` | 玩家 → 房主 | → 房主 | `{"target": PlayerId}` |
| `0x08` | `SPY_GUESS` | 間諜 → 房主 | → 房主 | `{"guess": str}` |
| `0x09` | `ROUND_RESULT` | 房主 → 所有人 | 廣播 | `{"spy": PlayerId, "answer": str, "scores": {PlayerId: int}}` |

### 接收端會丟棄的封包

下列情況 streaming 只會記錄 log 並丟棄，**不會**交給上層，也不會中斷連線：

- Magic 不符、未知 Type、Length 超過上限
- payload 不是合法的 UTF-8 / JSON，或頂層不是 JSON 物件
- 缺少上表標示的必備欄位（`DRAW_STROKE` 沒有必備欄位）
- `ROUND_STATE_SYNC` 的 `state` 不是合法的 `common.types.Phase` 值

## 機密規則（[ADR 0005](decisions/0005-secret-information.md)）

- **答案、提示、間諜身分**：只能單播，任何時候都不能廣播。`DEAL_WORD` 的 payload 不可帶有「誰是間諜」的欄位。
- **畫作**：`Phase.REVEAL` 之前只能送給房主，不能讓間諜收到其他人的畫作。`SPY_REFERENCE` 不可帶作者。
- 答案只有在 `ROUND_RESULT` 才公開。
- streaming 在程式裡強制：`DEAL_WORD` / `SPY_REFERENCE` 一次只能送一個對象；除了 `ROUND_STATE_SYNC`、`ROUND_RESULT` 之外的封包無法廣播。「誰可以收」仍由 core 決定。

## 錯誤處理

- 解碼器遇到壞資料時，只丟掉壞的部分，並往後找下一個 Magic 重新對齊；不會清空整個 buffer，也不會丟例外。
- 上層 handler 丟出的例外會被記錄，不會影響其他 handler 或連線。
- peer 斷線時，上層（或 p2p）要呼叫 `StreamManager.remove_peer(peer_id)` 清掉該 peer 的接收 buffer。

## 待決問題

1. **`DRAW_STROKE` 要不要用**：畫圖階段畫作不公開，所以筆畫不能廣播。建議畫圖階段只在本機畫，畫完用 `CANVAS_SNAPSHOT` 送給房主；若採用，`DRAW_STROKE` 可能用不到。（Canvas / Core 決定）
2. **`CANVAS_SNAPSHOT` 的圖片格式**：目前暫定 base64 PNG，單個封包上限 4 MiB。需要 Canvas 確認畫布輸出格式與大小。
3. **`DEAL_WORD` 沒有帶角色欄位**：UI 要如何知道自己是間諜（影響畫面顯示）？由 Core 決定是否額外單播一個欄位，或由 UI 從 Core 的狀態取得。
4. **大廳相關封包**（加入房間、公告誰是房主、玩家名單）：權威節點改為「所有人都下場玩，裁判邏輯放在開房者的程式裡」，之後會發 ADR。這些封包**不在這個 PR**，由 issue #7 處理。
5. **房主自己也是玩家**：p2p 的連線清單不包含自己，所以 `send_*` 對自己的 peer id 會失敗、`broadcast_*` 也不會送給自己；房主自己的發題、階段同步、投票都需要「本機直接送到自己的 handler」的機制。放在 `StreamManager`（傳入自己的 peer id，送給自己時直接分發）還是由 Core / `__main__` 處理，在 issue #7 一起討論。
