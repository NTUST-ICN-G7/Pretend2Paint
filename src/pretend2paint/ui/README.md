# ui — Canvas / UI

負責人：錢呈恩、李愷哲、石凡可、簡國行

> 本文件為 UI 組的**畫面規劃與 API 草稿（規劃中）**，尚未有對應程式碼。
> 封包名稱、Type、方向、傳送方式一律以 [`docs/protocol.md`](../../../docs/protocol.md) 為準；
> 下文的 UI ↔ Core 事件是 `queue.Queue` 內的**規劃格式**，不是網路封包，名稱與欄位仍需和 Core 組確認。

## 概觀

UI 模組負責在主執行緒顯示遊戲畫面、呈現 Core 提供的狀態，並將玩家操作轉成事件。UI 與 Core 透過 thread-safe 的 `queue.Queue` 傳遞事件；UI 不直接操作網路，也不判斷遊戲規則。

目前 UI 框架尚未決定（[ADR 0006](../../../docs/decisions/0006-ui-framework.md)），因此先以框架無關的方式規劃畫面流程與資料。

## 畫面總覽

| # | 畫面 | 遊戲階段 | 負責 |
| :--- | :--- | :--- | :--- |
| 1 | Landing | `LOBBY` | 成員 A |
| 2 | Waiting / Lobby | `LOBBY` | 成員 A |
| 3 | Role & Prompt | `DEAL` | 成員 A |
| 4 | Drawing | `DRAWING` | 成員 B |
| 5 | Spy Reference | `SPY_ACTION` | 成員 B |
| 6 | Spy Drawing | `SPY_ACTION` | 成員 B |
| 7 | Reveal | `REVEAL` | 成員 C |
| 8 | Voting | `VOTING` | 成員 C |
| 9 | Spy Guess | `SPY_GUESS` | 成員 D |
| 10 | Round Result | `ROUND_END` | 成員 D |

## 整體切換流程

畫面切換由 Core 提供的狀態或操作結果觸發，UI 不自行判斷遊戲規則：

```text
Landing
  └─ 建立／加入房間成功 → Waiting / Lobby
       └─ DEAL → Role & Prompt
            └─ DRAWING → Drawing（一般玩家畫圖；間諜等待）
                 └─ SPY_ACTION → Spy Reference（間諜盲選）→ Spy Drawing（間諜畫圖）
                      └─ REVEAL → Reveal（公開畫廊）
                           └─ VOTING → Voting（同一畫面，啟用投票）
                                ├─ SPY_GUESS（間諜被票出）→ Spy Guess → ROUND_END
                                └─ ROUND_END（間諜沒被票出）→ Round Result
                                     └─ 下一回合 → Role & Prompt／遊戲結束（待定）
```

## 共通規則

### 執行緒（[ADR 0004](../../../docs/decisions/0004-threading-model.md)）

- Core → UI 的事件走 `ui_queue`；UI → Core 的動作走 `net_queue`。
- UI 在主執行緒定時輪詢 `ui_queue`；**不做網路 I/O、不做任何阻塞操作**。

### 保密規則（[ADR 0005](../../../docs/decisions/0005-secret-information.md)）

- 答案、提示、間諜身分只能由 Core 提供給**當事人**；UI 不可顯示玩家不該知道的資訊。
- 間諜的畫面在任何階段都**不可出現答案**。
- 進入 `REVEAL` 之前，畫作只送給房主，不可讓其他玩家（包含間諜）看到。
- 答案與間諜身分只在 `ROUND_RESULT`（畫面 10）才公開。

---

## 畫面 1～3：Landing、Lobby、Role & Prompt（成員 A）

| 畫面 | 遊戲階段 | 顯示內容 |
| :--- | :--- | :--- |
| Landing | `LOBBY` | 建立房間、輸入玩家名稱、輸入房間資訊並加入房間 |
| Waiting / Lobby | `LOBBY` | 房間資訊、玩家列表、房主標記；房主顯示開始遊戲按鈕，其他玩家顯示等待狀態 |
| Role & Prompt | `DEAL` | 回合資訊與 Core 提供的個人角色資料；一般玩家顯示答案，間諜顯示提示 |

```text
Landing
  └─ Core 回報建立或加入房間成功 → Waiting / Lobby
       └─ Core 回報進入 DEAL → Role & Prompt
            └─ Core 回報進入 DRAWING → Drawing（成員 B）
```

### UI → Core

| 事件 | 使用時機 | Payload |
| :--- | :--- | :--- |
| `CREATE_ROOM` | 玩家按下建立房間 | `{"player_name": str}` |
| `JOIN_ROOM` | 玩家選擇房間並加入 | `{"player_name": str, "room_id": str}` |
| `START_GAME` | 房主按下開始遊戲 | `{}` |

例如建立房間的事件資料：

```python
{
    "event": "CREATE_ROOM",
    "payload": {"player_name": "Alice"},
}
```

### Core → UI

| 事件 | 使用時機 | Payload |
| :--- | :--- | :--- |
| `LOBBY_UPDATED` | 房間建立／加入成功，或玩家名單更新 | 房間 ID、房主 ID、玩家清單 |
| `DEAL_INFO` | Core 提供目前玩家本回合的角色資料 | 依玩家角色提供答案或提示 |

`DEAL_INFO` 的資料依角色不同，兩種格式擇一：

- 一般玩家：`{"round_number": 1, "role": "civilian", "answer": "西瓜"}`
- 間諜：`{"round_number": 1, "role": "spy", "hint": "兩個字的水果"}`

`DEAL_INFO` 只能包含目前玩家自己的角色資料：一般玩家收到答案，間諜收到提示；不可把所有人的角色一起傳送，也不可讓間諜收到答案。

### Prototype（草圖）

Landing

    玩家名稱：[____________]

    建立房間
    [建立房間]

    加入房間
    房間：[從清單選擇房間／輸入房間代碼]（方式待確認）
    [加入房間]

    狀態／錯誤訊息（由 Core 回報）：...（例如「正在加入……」或「加入失敗，請重試」）

Waiting / Lobby

    房間：...
    玩家：
    - Alice（房主）
    - Bob

    房主看到：[開始遊戲]
    其他玩家看到：等待房主開始

Role & Prompt — 一般玩家

    回合：1
    身分：一般玩家
    答案：西瓜
    等待 Core 通知進入畫圖階段

Role & Prompt — 間諜

    回合：1
    身分：間諜
    提示：兩個字的水果
    等待 Core 通知進入畫圖階段

---

## 畫面 4～6：Drawing、Spy Reference、Spy Drawing（成員 B）

| 畫面 | 遊戲階段 | 顯示內容 |
| :--- | :--- | :--- |
| Drawing | `DRAWING` | 題目答案、剩餘時間、空白畫布、繪圖工具列（顏色、粗細、橡皮擦、清空）、送出按鈕；送出後顯示等待狀態（間諜此階段等待） |
| Spy Reference | `SPY_ACTION` | 間諜提示字、可盲選的匿名畫作選項（不顯示作者與答案）、確認選擇按鈕（一般玩家此階段等待） |
| Spy Drawing | `SPY_ACTION` | 間諜提示字、選中的參考畫作（唯讀、不顯示原作者）、剩餘時間、空白畫布、繪圖工具列、送出按鈕 |

```text
Role & Prompt（成員 A）
  └─ Core 回報進入 DRAWING → Drawing（一般玩家畫圖；間諜等待）
       └─ Core 回報進入 SPY_ACTION → Spy Reference（間諜盲選參考圖；一般玩家等待）
            └─ Core 回報參考圖資料 → Spy Drawing（間諜看著參考圖畫圖）
                 └─ Core 回報進入 REVEAL → Reveal（成員 C）
```

### UI → Core

| 事件 | 使用時機 | Payload |
| :--- | :--- | :--- |
| `SUBMIT_DRAWING` | 一般玩家或間諜按下送出畫作 | `{"drawing_data": DrawingPayload}` |
| `SELECT_REFERENCE` | 間諜選擇 1 張匿名畫作並按下確認 | `{"reference_id": str}` |

### Core → UI

| 事件 | 使用時機 | Payload |
| :--- | :--- | :--- |
| `DRAWING_START` | Core 通知進入 `DRAWING` 階段 | 一般玩家：`{"answer": str, "time_limit": int}`；間諜：`{"hint": str, "waiting": bool}` |
| `SPY_REFERENCE_OPTIONS` | Core 通知間諜進入 `SPY_ACTION` 盲選參考圖 | `{"hint": str, "candidate_ids": list[str]}` |
| `SPY_REFERENCE_RECEIVED` | Core 回傳間諜選中的參考畫作 | `{"hint": str, "reference_id": str, "reference_drawing": DrawingPayload, "time_limit": int}` |

保密規則：

- 間諜畫面只能收到 `hint` 與盲選後的 `reference_drawing`，不可顯示真實答案，也不可顯示參考圖原作者。
- 進入 `REVEAL` 之前，玩家畫作僅由 Core 送給房主，不可廣播給其他玩家。

### 共用畫布操作介面

`Drawing` 與 `Spy Drawing` 共用同一組畫布操作（不綁定特定 GUI 框架）：

- 切換顏色（`set_color`）、切換筆刷粗細（`set_brush_size`）、切換畫筆／橡皮擦（`set_tool`）、清空畫布（`clear_canvas`）
- 按下送出後鎖定畫布防止重複送出，並透過 `SUBMIT_DRAWING` 送進 `net_queue`
- 參考圖預覽區僅做唯讀顯示，不可編輯

### Prototype（草圖）

Drawing — 一般玩家

    題目：西瓜　　　　　　剩餘時間：60s

    [ 空白畫布區域 ]

    [顏色] [粗細] [橡皮擦] [清空]　　　[送出畫作]

    送出後狀態：已送出，等待其他玩家……

Spy Reference — 間諜

    身分：間諜　　提示：兩個字的水果
    請盲選一張畫作作為參考（不顯示作者）：

    [ 畫作 #1 ]　[ 畫作 #2 ]　[ 畫作 #3 ]

    [確認選擇]

Spy Drawing — 間諜

    提示：兩個字的水果　　剩餘時間：60s

    [ 參考畫作（唯讀） ]　|　[ 空白畫布區域 ]

    [顏色] [粗細] [橡皮擦] [清空]　　　[送出畫作]

    送出後狀態：已送出，準備進入公開階段……

---

## 畫面 7～8：Reveal & Voting（成員 C）

本畫面負責 `REVEAL`（公開）與 `VOTING`（投票）兩個階段，以**同一個畫面、兩種狀態**呈現，讓玩家看著畫作投票。

- 只跟 `core` 往來，不 import `streaming` / `p2p`。
- 不判斷遊戲規則（誰被票出、要不要進入猜答案），只依 core 送來的階段狀態顯示。
- 不顯示答案、不顯示間諜身分。

| 狀態 | 遊戲階段 | 顯示內容 |
| :--- | :--- | :--- |
| 狀態 1（公開） | `REVEAL` | 所有玩家的畫作畫廊（含作者名稱）；被間諜選為參考的畫作加上標記（代表該作者一定不是間諜）；不顯示答案，也不顯示間諜身分。 |
| 狀態 2（投票） | `VOTING` | 保留同一份畫廊，加上可投票的玩家名單、選取可疑對象、送出投票按鈕；送出後顯示等待狀態。 |

### 狀態切換

UI **只看 `ROUND_STATE_SYNC` 的 `state`**，不自行推斷：

```text
Spy Drawing（成員 B）
  └─ ROUND_STATE_SYNC {"state": "reveal"}  → 狀態 1：公開畫廊，投票控制停用
       └─ ROUND_STATE_SYNC {"state": "voting"} → 狀態 2：同一畫面，啟用投票
            └─ ROUND_STATE_SYNC {"state": "spy_guess"} 或 {"state": "round_end"}
                 → 本畫面結束，交給 Spy Guess／Round Result（成員 D）
```

`state` 的值就是 `common.types.Phase`。**core 仍須把 `REVEAL` 與 `VOTING` 視為兩個獨立階段、分別送 `ROUND_STATE_SYNC`**；UI 不合併、不省略事件，也不自行判斷何時切換狀態。

### 對應封包（依 `docs/protocol.md`）

UI → Core

| 封包 | Type | 方向 | 傳送方式 | Payload |
| :--- | :--- | :--- | :--- | :--- |
| `VOTE` | `0x07` | 玩家 → 房主 | → 房主（單播） | `{"suspect_id": PlayerId}`（欄位未定） |

送出時機：狀態 2 中玩家選好對象並按下送出。送出後鎖定，避免重複投票。

Core → UI

| 封包 | Type | 方向 | 傳送方式 | Payload | 用途 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ROUND_STATE_SYNC` | `0x03` | 房主 → 所有人 | 廣播 | `{"state": "reveal"}` | 進入公開狀態 |
| `CANVAS_SNAPSHOT` | `0x04` | 房主 → 所有人 | 廣播 | **尚未定義（protocol 待決 #2）** | 公開所有畫作與被標記的參考畫 |
| `ROUND_STATE_SYNC` | `0x03` | 房主 → 所有人 | 廣播 | `{"state": "voting"}` | 進入投票狀態 |
| `ROUND_STATE_SYNC` | `0x03` | 房主 → 所有人 | 廣播 | `{"state": "spy_guess"}` | 投票結束、進入猜答案（本畫面結束） |
| `ROUND_RESULT` | `0x09` | 房主 → 所有人 | 廣播 | 尚未定義 | 回合結果，交給結算畫面 |

### 保密規則

- `REVEAL` 與 `VOTING` 都**不可顯示答案**；答案依 protocol 只在 `ROUND_RESULT` 公開。
- **不可顯示間諜身分**。`ROUND_STATE_SYNC` 只帶 `state`，不帶「誰是間諜」。
- 被標記的畫作只代表「**作者一定不是間諜**」，不代表其他人是間諜。
- 畫作在 `REVEAL` 之前只能送給房主（ADR 0005）；本畫面收到的 `CANVAS_SNAPSHOT` 是房主在 `REVEAL` 之後才廣播的。

### 共用顯示元件（不綁定 GUI 框架）

- **畫作卡片**：顯示 `drawing` 與作者名稱；唯讀，不可編輯。
- **標記徽章**：被間諜選為參考的畫作附加「一定不是間諜」說明（欄位依 `CANVAS_SNAPSHOT` 的定義）。
- **投票清單**：列出候選人，一次只能選一個 `suspect_id`；收到 `{"state": "voting"}` 之前保持停用，收到後才啟用；按下送出後鎖定，避免重複投票，並透過 `VOTE` 送進 `net_queue`。
- **等待區**：送出投票後顯示「已投票，等待其他玩家……」；不自行假設投票成功。
- **切換狀態時保留畫廊與捲動位置**，不重建整個畫面。

### Prototype（草圖）

Reveal & Voting — 狀態 1：公開（唯讀，`REVEAL`）

    公開畫作                          回合：1

    [ Alice 的畫作 ]    [ Bob 的畫作（一定不是間諜） ]

    [ Charlie 的畫作 ]  [ Dave 的畫作 ]

    標記說明：被間諜選為參考的畫作，其作者一定不是間諜
    等待 core 通知進入投票階段……

Reveal & Voting — 狀態 2：投票（`VOTING`，同一畫面）

    （上方畫作畫廊保留不變，以下為新增的投票區）

    投票：你認為誰是間諜？

      ( ) Alice
      ( ) Bob（一定不是間諜）
      ( ) Charlie
      ( ) Dave

    [送出投票]

    送出後狀態：已投票，等待其他玩家……

---

## 畫面 9～10：Spy Guess、Round Result（成員 D）

| 畫面 | 遊戲階段 | 顯示內容 |
| :--- | :--- | :--- |
| Spy Guess | `SPY_GUESS` | 僅在間諜被票出時出現。間諜：被票出提示、自己的提示、答案輸入框、送出按鈕；其他玩家：被票出的玩家、「間諜正在猜答案……」等待狀態 |
| Round Result | `ROUND_END` | 間諜身分、正確答案、間諜的提示、間諜猜的答案與對錯（若有猜）、本回合結果、每位玩家本回合得分與總分；下一回合／離開按鈕 |

```text
Voting（成員 C）
  ├─ Core 回報進入 SPY_GUESS（間諜被票出）→ Spy Guess
  │    └─ Core 回報進入 ROUND_END → Round Result
  └─ Core 回報進入 ROUND_END（間諜沒被票出）→ Round Result
       └─ 房主按下一回合 → Core 回報進入 DEAL → Role & Prompt（成員 A）
```

### Spy Guess

- 間諜有**一次**機會猜答案；其他玩家只能等待。
- 猜對或猜錯由**房主（Core）判斷**，UI 不比對答案，也不在此畫面顯示對錯；結果在 Round Result 公布。
- 「自己是不是間諜」與「提示」沿用 `DEAL_INFO`（成員 A）收到的資料，UI 本地保留，不需要重新傳送。
- 其他玩家的畫面**不可出現提示或答案**。

### Round Result

本回合的結果依 [`docs/game-rules.md`](../../../docs/game-rules.md) 有三種，由 Core 判斷後告訴 UI，UI 只負責顯示：

| 情況 | 畫面顯示 |
| :--- | :--- |
| 間諜**沒有**獲得最高票 | 「間諜成功潛伏！」間諜得分 |
| 間諜被票出，且猜對答案 | 「間諜猜中答案！」間諜得分 |
| 間諜被票出，且猜錯答案 | 「間諜被抓到了！」間諜扣分 |

- 答案與間諜身分**到這個畫面才公開**（對應 `ROUND_RESULT`，房主廣播）。
- 「下一回合」按鈕只有房主可以按；其他玩家顯示「等待房主開始下一回合……」。

### UI → Core

| 事件 | 使用時機 | Payload |
| :--- | :--- | :--- |
| `SUBMIT_SPY_GUESS` | 間諜輸入答案並按下送出（對應封包 `SPY_GUESS` `0x08`，間諜 → 房主） | `{"guess": str}` |
| `NEXT_ROUND` | 房主在 Round Result 按下一回合 | `{}` |
| `LEAVE_ROOM` | 玩家在 Round Result 按離開房間 | `{}` |

- 輸入框為空時不能送出；送出後鎖定輸入框與按鈕，避免重複送出。

### Core → UI

| 事件 | 使用時機 | Payload |
| :--- | :--- | :--- |
| `SPY_GUESS_START` | Core 通知進入 `SPY_GUESS` | `{"accused_id": PlayerId, "accused_name": str}` |
| `ROUND_RESULT` | Core 通知進入 `ROUND_END`（對應封包 `ROUND_RESULT` `0x09`，房主 → 所有人） | 見下方 |

`ROUND_RESULT` 規劃格式：

```python
{
    "event": "ROUND_RESULT",
    "payload": {
        "round_number": 1,
        "spy_id": "p3",
        "spy_name": "Charlie",
        "answer": "西瓜",
        "hint": "兩個字的水果",
        "accused_id": "p3",        # 最高票的玩家；平票規則待定
        "spy_guess": "哈密瓜",      # 間諜沒被票出時為 None
        "guess_correct": False,    # 間諜沒被票出時為 None
        "outcome": "spy_caught",   # spy_escaped / spy_guessed_right / spy_caught
        "scores": [
            {"player_id": "p1", "name": "Alice", "delta": 0, "total": 2},
            {"player_id": "p3", "name": "Charlie", "delta": -1, "total": 0},
        ],
        "is_last_round": False,    # 回合數待定
    },
}
```

### Prototype（草圖）

Spy Guess — 間諜

    你被票出了！
    你的提示：兩個字的水果

    猜猜看答案是什麼？（只有一次機會）
    [____________]

    [送出答案]

    送出後狀態：已送出，等待結果……

Spy Guess — 其他玩家

    Charlie 被票出了！

    間諜正在猜答案……

Round Result

    第 1 回合結果

    間諜是：Charlie
    答案：西瓜　　提示：兩個字的水果
    間諜猜：哈密瓜（錯誤）

    間諜被抓到了！

    玩家       本回合    總分
    Alice       +0        2
    Bob         +0        1
    Charlie     -1        0
    Dave        +0        1

    房主看到：[下一回合]  [離開房間]
    其他玩家：等待房主開始下一回合……  [離開房間]

---

## 待確認事項

以下問題需要和 Core／Streaming 組確認，確認後更新本文件：

- [ ] **UI ↔ Core 事件格式要統一**：成員 A、B、D 以 queue 事件（如 `CREATE_ROOM`、`SUBMIT_DRAWING`）描述，成員 C 以網路封包（如 `VOTE`、`ROUND_STATE_SYNC`）描述；UI 不直接碰封包，建議統一改成 queue 事件，再註明對應的封包。
- [ ] **被票出的玩家是誰**：protocol 目前沒有封包會把投票結果告訴所有人（`ROUND_STATE_SYNC` 只帶 `state`，`VOTE` 只送給房主），Spy Guess 畫面需要這個資料。
- [ ] **平票處理、一般玩家計分方式、遊戲共幾回合**：`game-rules.md` 尚未決定，會影響 Round Result 與遊戲結束畫面。
- [ ] **間諜猜答案是否有時間限制**，時間到時如何處理。
- [ ] **提示重複傳送**：`DEAL_INFO`（成員 A）、`DRAWING_START` 與 `SPY_REFERENCE_*`（成員 B）都帶有 `hint`，是否統一由 `DEAL_INFO` 提供即可。
- [ ] **`CANVAS_SNAPSHOT` 格式**與 `DrawingPayload` 型別（protocol 待決 #2）。
- [ ] **UI 框架**（ADR 0006）：決定後補上各畫面的實際 API。
