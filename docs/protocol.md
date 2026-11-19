# 通訊協定

> 這份文件是封包格式的**唯一來源**。新增或修改封包時，必須同一個 PR 內同步更新：
> 本文件、`streaming/protocol.py`、送出端與接收端的測試。（agent 請使用 `add-packet-type` skill）

負責模組：`streaming`（李昇原、黃佑竣）

## Framing

每個封包 = 7 bytes header + JSON payload（UTF-8）。整數皆為 network byte order（big-endian）。

| 欄位 | 大小 | 說明 |
| :--- | :--- | :--- |
| Magic | 2 bytes | 固定 `0x49 0x43`（`"IC"`） |
| Type | 1 byte | 封包類型，見下表 |
| Length | 4 bytes | payload 長度（bytes） |
| Payload | Length bytes | JSON 物件 |

## 封包類型

傳送方式：**廣播** = 發給房間所有人；**單播** = 只發給特定玩家；**→ 房主** = 只發給房主。

### 已實作

| Type | 名稱 | 方向 | 傳送方式 | Payload |
| :--- | :--- | :--- | :--- | :--- |
| `0x01` | `DRAW_STROKE` | 畫圖者 → 其他人 | 見待決 #2 | `{"x", "y", "color", ...}` |
| `0x02` | `SPY_SELECT_REF` | 間諜 → 房主 | → 房主 | `{"target_author"}`（見待決 #1） |
| `0x03` | `ROUND_STATE_SYNC` | 房主 → 所有人 | 廣播 | `{"state"}`，值為 `common.types.Phase` |
| `0x04` | `CANVAS_SNAPSHOT` | 畫圖者 → 房主；房主 → 所有人 | 見待決 #2 | 尚未定義 |

### 待實作（依遊戲規則需要）

| 建議 Type | 名稱 | 方向 | 傳送方式 | 用途 |
| :--- | :--- | :--- | :--- | :--- |
| `0x05` | `DEAL_WORD` | 房主 → 每位玩家 | **單播** | 發題：一般玩家收到答案，間諜收到提示 |
| `0x06` | `SPY_REFERENCE` | 房主 → 間諜 | **單播** | 把間諜選中的參考圖發給間諜 |
| `0x07` | `VOTE` | 玩家 → 房主 | → 房主 | 投票 |
| `0x08` | `SPY_GUESS` | 間諜 → 房主 | → 房主 | 間諜猜答案 |
| `0x09` | `ROUND_RESULT` | 房主 → 所有人 | 廣播 | 公布間諜、答案、得分 |

## 機密規則（[ADR 0005](decisions/0005-secret-information.md)）

- **答案、提示、間諜身分**：只能單播，任何時候都不能廣播。`DEAL_WORD` 的 payload 不可帶有「誰是間諜」的欄位。
- **畫作**：`Phase.REVEAL` 之前只能送給房主，不能讓間諜收到其他人的畫作。
- 答案只有在 `ROUND_RESULT` 才公開。

## 待決問題

1. **盲選的 payload**：「盲選」代表間諜不知道作者是誰，`SPY_SELECT_REF` 目前帶 `target_author` 不合理。建議改為帶「第幾張」（例如 `{"index": 2}`），由房主對應到作者。
2. **`DRAW_STROKE` 的對象**：畫圖階段的畫作不公開，所以筆畫不能即時廣播。建議畫圖階段只在本機畫，畫完用 `CANVAS_SNAPSHOT` 送給房主；或筆畫只送給房主。
3. **錯誤處理**：Magic 不符時目前會清空整個 buffer；Length 沒有上限。
