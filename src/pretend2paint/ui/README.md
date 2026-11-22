# ui — Canvas / UI

負責人：錢呈恩、李愷哲、石凡可、簡國行

> 本文件為 UI 組的**畫面規劃與 API 草稿（規劃中）**，尚未有對應程式碼。
> 封包名稱、Type、方向、傳送方式一律以 [`docs/protocol.md`](../../../docs/protocol.md) 為準；
> 下文的 UI ↔ Core 事件是 `queue.Queue` 內的**規劃格式**，不是網路封包，名稱與欄位仍需和 Core 組確認。

## 概觀

UI 模組負責在主執行緒顯示遊戲畫面、呈現 Core 提供的狀態，並將玩家操作轉成事件。UI 與 Core 透過 thread-safe 的 `queue.Queue` 傳遞事件；UI 不直接操作網路，也不判斷遊戲規則。

UI 框架使用 **tkinter**（Python 內建，不需額外安裝，有 `Canvas` 可畫圖）。目前尚未有程式碼，先規劃畫面流程與資料。

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

## 遊戲規則（UI 組版本）

> 與 [`docs/game-rules.md`](../../../docs/game-rules.md) 有差異的地方以 **粗體** 標示，待 team leader／Core 組確認後同步更新該文件。

1. **發題**：一般玩家拿到答案（例：「西瓜」），間諜只拿到提示（例：「兩個字的水果」）。
2. **畫圖**：一般玩家先各自畫圖，畫作不公開。
3. **間諜行動**：一般玩家畫完後，間諜從一般玩家的畫作中盲選 1 張作為參考，再畫自己的圖。
4. **公開**：所有畫作（包含間諜的）**以隨機順序、匿名方式**同時顯示在所有人的螢幕上；被間諜選為參考的那張畫作會加上標記，證明**這張圖一定是一般玩家畫的**。
5. **投票**：所有人**投票選出自己認為是間諜畫的那張畫作**（投畫作編號，不是投玩家名字）。
6. **間諜猜答案**：間諜的畫作若獲得**最高票，或與其他畫作平票**，間諜有一次機會猜一般玩家的答案（例如猜「西瓜」）；猜中的話，間諜方**扣的分數比較少**。
7. **結算**：間諜的畫作沒有拿到最高票（其他畫作唯一最高票）時，間諜成功潛伏，不用猜答案。實際分數依 Core 組規則（見下方成員 D 的「計分」）。

## 整體切換流程

畫面切換由 Core 提供的狀態或操作結果觸發，UI 不自行判斷遊戲規則：

```text
Landing
  └─ 建立／加入房間成功 → Waiting / Lobby
       └─ DEAL → Role & Prompt
            └─ DRAWING → Drawing（一般玩家畫圖；間諜等待）
                 └─ SPY_ACTION → Spy Reference（間諜盲選）→ Spy Drawing（間諜畫圖）
                      └─ REVEAL → Reveal（隨機、匿名公開畫廊）
                           └─ VOTING → Voting（同一畫面，啟用投票）
                                ├─ SPY_GUESS（間諜最高票或平票）→ Spy Guess → ROUND_END
                                └─ ROUND_END（其他畫作唯一最高票）→ Round Result
                                     └─ 下一回合 → Role & Prompt／遊戲結束（待定）
```

## 共通規則

### 執行緒（[ADR 0004](../../../docs/decisions/0004-threading-model.md)）

- Core → UI 的事件走 `ui_queue`；UI → Core 的動作走 `net_queue`。
- UI 在主執行緒跑 tkinter 的 `mainloop()`，用 `root.after()` 定時輪詢 `ui_queue`；**不做網路 I/O、不做任何阻塞操作**。

### 保密規則（[ADR 0005](../../../docs/decisions/0005-secret-information.md)）

- 答案、提示、間諜身分只能由 Core 提供給**當事人**；UI 不可顯示玩家不該知道的資訊。
- 間諜的畫面在任何階段都**不可出現答案**。
- 進入 `REVEAL` 之前，畫作只送給房主，不可讓其他玩家（包含間諜）看到。
- `REVEAL`／`VOTING` 階段畫作**匿名、隨機排序**，畫面上不可出現作者名稱。
- 答案、間諜身分、每張畫作的作者只在 `ROUND_RESULT`（畫面 10）才公開；`SPY_GUESS` 階段也**不可**向其他玩家透露哪張畫是間諜的。

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
- 不判斷遊戲規則（哪張畫作最高票、要不要進入猜答案、誰獲勝），只依 core 送來的階段狀態顯示。
- 不顯示答案、不顯示間諜身分、**不顯示畫作作者**。

| 狀態 | 遊戲階段 | 顯示內容 |
| :--- | :--- | :--- |
| 狀態 1（公開） | `REVEAL` | 所有玩家（含間諜）的畫作畫廊，**以隨機順序、匿名編號（#1、#2…）顯示，不顯示作者**；被間諜選為參考的畫作加上標記（代表這張圖一定是一般玩家畫的）；不顯示答案，也不顯示間諜身分。 |
| 狀態 2（投票） | `VOTING` | 保留同一份畫廊，加上**畫作編號的投票選項**（被標記的畫作不能投）、送出投票按鈕；送出後顯示等待狀態。 |

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
| `VOTE` | `0x07` | 玩家 → 房主 | → 房主（單播） | `{"drawing_index": int}`（投畫作編號，由房主對應到作者；欄位未定） |

送出時機：狀態 2 中玩家選好畫作並按下送出。送出後鎖定，避免重複投票。

Core → UI

| 封包 | Type | 方向 | 傳送方式 | Payload | 用途 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ROUND_STATE_SYNC` | `0x03` | 房主 → 所有人 | 廣播 | `{"state": "reveal"}` | 進入公開狀態 |
| `CANVAS_SNAPSHOT` | `0x04` | 房主 → 所有人 | 廣播 | **尚未定義（protocol 待決 #2）**；需為隨機排序後的匿名畫作，**不可帶作者** | 公開所有畫作與被標記的參考畫 |
| `ROUND_STATE_SYNC` | `0x03` | 房主 → 所有人 | 廣播 | `{"state": "voting"}` | 進入投票狀態 |
| `ROUND_STATE_SYNC` | `0x03` | 房主 → 所有人 | 廣播 | `{"state": "spy_guess"}` | 間諜最高票或平票，進入猜答案（本畫面結束） |
| `ROUND_STATE_SYNC` | `0x03` | 房主 → 所有人 | 廣播 | `{"state": "round_end"}` | 間諜沒拿到最高票，直接結算（本畫面結束） |
| `ROUND_RESULT` | `0x09` | 房主 → 所有人 | 廣播 | 見成員 D | 回合結果，交給結算畫面 |

### 保密規則

- `REVEAL` 與 `VOTING` 都**不可顯示答案**；答案依 protocol 只在 `ROUND_RESULT` 公開。
- **不可顯示間諜身分與畫作作者**。`ROUND_STATE_SYNC` 只帶 `state`；`CANVAS_SNAPSHOT` 不帶作者，畫作順序由房主隨機打亂。
- 被標記的畫作只代表「**這張圖一定是一般玩家畫的**」，不代表其他畫作是間諜畫的。
- 畫作在 `REVEAL` 之前只能送給房主（ADR 0005）；本畫面收到的 `CANVAS_SNAPSHOT` 是房主在 `REVEAL` 之後才廣播的。

### 共用顯示元件（不綁定 GUI 框架）

- **畫作卡片**：顯示 `drawing` 與匿名編號（#1、#2…）；唯讀，不可編輯，不顯示作者。
- **標記徽章**：被間諜選為參考的畫作附加「一定是一般玩家畫的」說明（欄位依 `CANVAS_SNAPSHOT` 的定義）。
- **投票清單**：列出畫作編號，一次只能選一張；被標記的畫作不能選；收到 `{"state": "voting"}` 之前保持停用，收到後才啟用；按下送出後鎖定，避免重複投票，並透過 `VOTE` 送進 `net_queue`。
- **等待區**：送出投票後顯示「已投票，等待其他玩家……」；不自行假設投票成功。
- **切換狀態時保留畫廊與捲動位置**，不重建整個畫面。

### Prototype（草圖）

Reveal & Voting — 狀態 1：公開（唯讀，`REVEAL`）

    公開畫作（隨機順序、匿名）            回合：1

    [ 畫作 #1 ]    [ 畫作 #2（一定是一般玩家畫的） ]

    [ 畫作 #3 ]    [ 畫作 #4 ]

    標記說明：被間諜選為參考的畫作，一定是一般玩家畫的
    等待 core 通知進入投票階段……

Reveal & Voting — 狀態 2：投票（`VOTING`，同一畫面）

    （上方畫作畫廊保留不變，以下為新增的投票區）

    投票：你認為哪一張是間諜畫的？

      ( ) 畫作 #1
      ( ) 畫作 #2（已標記，不能投）
      ( ) 畫作 #3
      ( ) 畫作 #4

    [送出投票]

    送出後狀態：已投票，等待其他玩家……

---

## 畫面 9～10：Spy Guess、Round Result（成員 D）

| 畫面 | 遊戲階段 | 顯示內容 |
| :--- | :--- | :--- |
| Spy Guess | `SPY_GUESS` | 只在間諜的畫作**最高票或平票**時出現。間諜：投票結果提示、自己的提示、答案輸入框、送出按鈕；其他玩家：「間諜正在猜答案……」等待狀態（**不透露哪張畫是間諜的**） |
| Round Result | `ROUND_END` | 本回合結果、間諜是誰、正確答案與間諜的提示、間諜猜的答案與對錯（若有猜）、每張畫作的作者與得票數、每位玩家本回合得分與總分；下一回合／離開按鈕 |

```text
Voting（成員 C）
  ├─ Core 回報進入 SPY_GUESS（間諜最高票或平票）→ Spy Guess
  │    └─ Core 回報進入 ROUND_END → Round Result
  └─ Core 回報進入 ROUND_END（其他畫作唯一最高票，間諜成功潛伏）→ Round Result
       └─ 房主按下一回合 → Core 回報進入 DEAL → Role & Prompt（成員 A）
```

### Spy Guess

- 間諜有**一次**機會猜一般玩家的答案（例如猜「西瓜」）；其他玩家只能等待。
- 要不要進入這個畫面、猜對還是猜錯，都由 **Core 判斷**；UI 不計票、不比對答案，也不在此畫面顯示對錯，結果在 Round Result 公布。
- 「自己是不是間諜」與「提示」沿用 `DEAL_INFO`（成員 A）收到的資料，UI 本地保留，不需要重新傳送。
- 其他玩家的畫面**不可出現提示、答案，也不可透露哪張畫是間諜的**（作者對應在 `ROUND_RESULT` 才公開）。
- 逾時未送出視為猜錯（依 Core 組提案；時間長度由 Core 設定）。

### Round Result

本回合的結果有以下幾種，由 Core 判斷後告訴 UI，UI 只負責顯示：

| 情況 | 畫面顯示 |
| :--- | :--- |
| 其他畫作**唯一最高票**（間諜不用猜） | 「間諜成功潛伏！」 |
| 間諜**唯一最高票**，且猜對答案 | 「間諜被抓到了，但猜中答案！」 |
| 間諜**唯一最高票**，且猜錯答案（或逾時） | 「間諜被抓到了！」 |
| 間諜與其他畫作**平票**（或沒人投票），且猜對答案 | 「平票！間諜猜中答案」 |
| 間諜與其他畫作**平票**（或沒人投票），且猜錯答案（或逾時） | 「平票！間諜沒猜中」 |

- 答案、間諜身分、**每張畫作的作者**都是**到這個畫面才公開**（對應 `ROUND_RESULT`，房主廣播）。
- 公開時沿用 Reveal 畫面的畫作編號，讓玩家對得起來「#3 原來是 Charlie 畫的」。
- 「下一回合」按鈕只有房主可以按；其他玩家顯示「等待房主開始下一回合……」。

### 計分

**具體分數以 Core 組規則為準**，UI 只顯示 Core 算好的 `delta`（本回合得分）與 `total`（總分），不自己計算。

目前 Core 組的提案（分支 `feature/core-part-b-v120-proposal-20261122` 的 `game-rules.md` v1.2.0，**尚未合併、分數為暫定值**）：

| 結果 | 間諜 | 投中間諜的一般玩家（N 人局） |
| :--- | ---: | ---: |
| 間諜成功潛伏 | +3 | `5+3*(N-4)` |
| 間諜被抓、猜對 | +1 | `5+3*(N-4)` |
| 間諜被抓、猜錯或逾時 | -3 | `8+3*(N-4)` |
| 平票或無票、猜對 | +1 | `5+3*(N-4)` |
| 平票或無票、猜錯或逾時 | 0 | `5+3*(N-4)` |

也就是說，間諜被抓時「猜對」比「猜錯」少損失 4 分，符合「猜中的話間諜方扣的分數比較少」。

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
| `SPY_GUESS_START` | Core 通知進入 `SPY_GUESS` | `{"reason": "caught" \| "tie", "time_limit": int}`（`reason` 只送給間諜；其他玩家只收到 `{}`） |
| `ROUND_RESULT` | Core 通知進入 `ROUND_END`（對應封包 `ROUND_RESULT` `0x09`，房主 → 所有人） | 見下方 |

`ROUND_RESULT` 規劃格式：

```python
{
    "event": "ROUND_RESULT",
    "payload": {
        "round_number": 1,
        # spy_escaped / caught_right / caught_wrong / tie_right / tie_wrong
        "outcome": "caught_wrong",
        "spy_id": "p3",
        "spy_name": "Charlie",
        "answer": "西瓜",
        "hint": "兩個字的水果",
        "spy_guess": "哈密瓜",  # 間諜不用猜時為 None
        "guess_correct": False,  # 間諜不用猜時為 None
        "drawings": [  # 沿用 Reveal 的畫作編號，公開作者與得票數
            {"drawing_index": 1, "author_name": "Alice", "votes": 0},
            {"drawing_index": 2, "author_name": "Bob", "votes": 0, "marked": True},
            {"drawing_index": 3, "author_name": "Charlie", "votes": 2},
            {"drawing_index": 4, "author_name": "Dave", "votes": 1},
        ],
        "scores": [  # 分數由 Core 計算
            {"player_id": "p1", "name": "Alice", "delta": 8, "total": 8},
            {"player_id": "p3", "name": "Charlie", "delta": -3, "total": -3},
        ],
        "is_last_round": False,  # 回合數待定
    },
}
```

### Prototype（草圖）

Spy Guess — 間諜

    你的畫作拿到最高票！（平票時顯示：你的畫作跟其他畫作平票！）
    你的提示：兩個字的水果

    猜猜看一般玩家的答案是什麼？（只有一次機會）
    [____________]　　剩餘時間：15s

    [送出答案]

    送出後狀態：已送出，等待結果……

Spy Guess — 其他玩家

    投票結束！

    間諜正在猜答案……

Round Result

    第 1 回合結果

    間諜被抓到了！

    間諜是：Charlie
    答案：西瓜　　間諜拿到的提示：兩個字的水果
    間諜猜：哈密瓜（錯誤）

    畫作    作者       得票
    #1      Alice       0
    #2      Bob         0   （被間諜選為參考）
    #3      Charlie     2   ← 間諜
    #4      Dave        1

    玩家       本回合    總分
    Alice       +8        8
    Bob         +0        0
    Charlie     -3       -3
    Dave        +0        0

    房主看到：[下一回合]  [離開房間]
    其他玩家：等待房主開始下一回合……  [離開房間]

---

## 待確認事項

以下問題需要和 team leader／Core／Streaming 組確認，確認後更新本文件：

- [ ] **遊戲規則同步**：本文件的「遊戲規則（UI 組版本）」與 `docs/game-rules.md` 不同（畫作匿名、投畫作而非投玩家、平票也能猜答案）。Core 組提案 v1.2.0 與此大致一致，合併後需更新 `docs/game-rules.md`。
- [ ] **Core 提案的「逐張審查」階段**：Core v1.2.0 在投票前多了一般玩家逐張審查畫作（`Phase.REVIEW`）與違規處罰，目前 UI 沒有對應畫面，需決定由誰負責。
- [ ] **投票資格**：Core v1.2.0 規定只有一般玩家能投、不能投自己或被標記的畫作、間諜沒有有效票；UI 的 Voting 畫面需依此停用對應選項。
- [ ] **UI ↔ Core 事件格式要統一**：成員 A、B、D 以 queue 事件（如 `CREATE_ROOM`、`SUBMIT_DRAWING`）描述，成員 C 以網路封包（如 `VOTE`、`ROUND_STATE_SYNC`）描述；UI 不直接碰封包，建議統一改成 queue 事件，再註明對應的封包。
- [ ] **分數與回合數**：分數目前是 Core 的暫定值；遊戲共幾回合、最後如何決定總冠軍。
- [ ] **提示重複傳送**：`DEAL_INFO`（成員 A）、`DRAWING_START` 與 `SPY_REFERENCE_*`（成員 B）都帶有 `hint`，是否統一由 `DEAL_INFO` 提供即可。
- [ ] **`CANVAS_SNAPSHOT` 格式**與 `DrawingPayload` 型別（protocol 待決 #2），需支援匿名編號與參考標記。
- [ ] **UI 框架定案為 tkinter**：[ADR 0006](../../../docs/decisions/0006-ui-framework.md) 與 `ui/AGENTS.md` 仍寫「待定」，需由 team leader 更新；更新後再補上各畫面的實際 API。
