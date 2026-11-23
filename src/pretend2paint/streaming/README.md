# streaming — 通訊協定、framing、封包分發

負責人：李昇原、黃佑竣

## 概觀

streaming 負責封包格式（7-byte header + JSON）、處理 TCP 黏包／半包、把收到的封包依類型分發給上層註冊的 handler，並提供各封包的送出方法。
它**不**做遊戲規則判斷（誰該收這個封包由 core 決定），也不管連線怎麼建立。

在分層中的位置：`core` 呼叫 streaming（送、註冊 handler）；streaming 呼叫 `p2p`（送 bytes）；`p2p` 收到 bytes 後呼叫 streaming。
封包格式的唯一來源是 [`docs/protocol.md`](../../../docs/protocol.md)。

## 快速使用

```python
from pretend2paint.common.types import Phase
from pretend2paint.streaming import PacketType, StreamManager

manager = StreamManager(pool)  # pool 由 p2p 提供（ConnectionPool）

# 接線（由 __main__.py 負責）：
pool.add_data_handler(manager.handle_incoming_data)
pool.add_peer_left_handler(manager.remove_peer)


# core：註冊收到封包時的處理（在 StreamManager 建好之後、開始收資料之前）
def on_vote(peer_id: str, payload: dict) -> None:
    print(peer_id, "投給", payload["target"])


manager.register_handler(PacketType.VOTE, on_vote)

# p2p：收到某個 peer 的 bytes 時
manager.handle_incoming_data("peer_001", raw_bytes)

# p2p：peer 斷線時
manager.remove_peer("peer_001")

# core（房主）：發題、廣播階段
manager.send_deal_word(["peer_002"], "西瓜")
manager.broadcast_round_state(Phase.DRAWING)

# core（玩家）：投票給 peer_003
manager.send_vote([host_id], "peer_003")
```

## API

### `StreamManager(pool: ConnectionPool)`

| 參數 | 型別 | 說明 |
| :--- | :--- | :--- |
| `pool` | `ConnectionPool` | p2p 提供的連線池，見下方「與其他模組的約定」 |

**執行緒**：所有方法都不是 async，也不會阻塞；只能在 asyncio 背景執行緒呼叫（[ADR 0004](../../../docs/decisions/0004-threading-model.md)）。handler 也在這條執行緒被呼叫，**不可在 handler 裡做耗時或阻塞的事**。

#### 接收

##### `handle_incoming_data(peer_id: PlayerId, raw_data: bytes) -> None`
- 用途：p2p 收到某個 peer 的 bytes 時呼叫的**唯一入口**。內部會處理黏包、半包，再分發給 handler。
- 何時呼叫：每次 TCP 讀到資料（不需要自己切封包）。
- 例外 / 錯誤：不會丟例外。壞資料會被記錄並丟棄，之後的好封包照常處理。

##### `register_handler(packet_type: int, handler: Handler) -> None`
- 用途：註冊某類封包的 handler，`Handler = Callable[[PlayerId, dict], None]`，呼叫方式 `handler(peer_id, payload)`。同一類型可註冊多個，依註冊順序呼叫。
- 何時呼叫：啟動時。沒有 handler 的封包會被忽略。
- 例外 / 錯誤：`ValueError`：未知的封包類型。handler 本身丟出的例外會被記錄，不會影響其他 handler。
- 保證：交給 handler 的 `payload` 一定是 dict，且包含該封包的必備欄位（見 `docs/protocol.md`）。

##### `remove_peer(peer_id: PlayerId) -> None`
- 用途：清掉該 peer 的接收 buffer。peer 斷線時呼叫，避免重連後殘留半個封包。
- 例外 / 錯誤：peer 不存在時不做事。

#### 送出：單播

所有單播方法的 `target_peers` 都必須是**明確、非空**的 peer id 清單，不存在「空清單 = 全部」。

- 例外 / 錯誤：`ValueError`：`target_peers` 為空，或 `payload` 過大；`TypeError`：`target_peers` 是字串（避免把 `"host"` 當成 4 個 peer），或 payload 無法轉成 JSON。

| 方法 | 方向 | 說明 |
| :--- | :--- | :--- |
| `send_draw_stroke(target_peers, stroke_data: dict)` | 畫圖者 → 指定對象 | 畫筆資料；畫圖階段不公開，所以不能廣播 |
| `send_spy_selection(target_peers, index: int)` | 間諜 → 房主 | 盲選第 `index` 張參考圖（不帶作者） |
| `send_canvas_snapshot(target_peers, image: str, author=None, index=None, marked=None)` | 畫圖者 → 房主；房主 → 玩家 | `image` 為 base64 PNG（暫定）；後三個欄位只在公開階段由房主填 |
| `send_deal_word(target_peers, text: str)` | 房主 → 單一玩家 | 一般玩家的 `text` 是答案，間諜是提示。**只能一個對象**，否則 `ValueError` |
| `send_spy_reference(target_peers, image: str)` | 房主 → 間諜 | 參考圖，不含作者。**只能一個對象**，否則 `ValueError` |
| `send_vote(target_peers, target: PlayerId)` | 玩家 → 房主 | 投票 |
| `send_spy_guess(target_peers, guess: str)` | 間諜 → 房主 | 猜答案 |

#### 送出：廣播

只有這兩種封包允許廣播；其餘封包（包含答案、提示、畫作）在程式裡就無法廣播（[ADR 0005](../../../docs/decisions/0005-secret-information.md)）。

| 方法 | 說明 |
| :--- | :--- |
| `broadcast_round_state(state: Phase \| str)` | 房主 → 所有人：同步回合階段。`state` 不是合法的 `Phase` 時丟 `ValueError` |
| `broadcast_round_result(spy: PlayerId, answer: str, scores: dict[PlayerId, int])` | 房主 → 所有人：公布間諜、答案、得分 |

### `PacketType`
封包類型（`IntEnum`，log 與除錯時看得到名稱）（`DRAW_STROKE`、`SPY_SELECT_REF`、`ROUND_STATE_SYNC`、`CANVAS_SNAPSHOT`、`DEAL_WORD`、`SPY_REFERENCE`、`VOTE`、`SPY_GUESS`、`ROUND_RESULT`），給 `register_handler` 使用。數值與 payload 欄位見 `docs/protocol.md`。

### `StreamPacket` / `StreamPacketDecoder`
底層編解碼，一般情況下**不需要直接使用**，用 `StreamManager` 即可。

- `StreamPacket.encode(packet_type: int, payload_dict: dict) -> bytes`
- `StreamPacketDecoder.feed_data(data: bytes)`、`.parse_packets() -> list[tuple[int, dict]]`

## 與其他模組的約定

**需要 p2p 提供**（p2p 連線池的介面見 [`p2p/README.md`](../p2p/README.md)，streaming 只用到其中兩個）：

```python
class ConnectionPool(Protocol):
    def send_many(
        self, peer_ids: Iterable[PlayerId], data: bytes
    ) -> None: ...  # 空清單丟 ValueError
    def broadcast(self, data: bytes) -> None: ...  # 送給房間所有 peer
```

- 單播方法內部使用 `send_many`；廣播使用 `broadcast`。
- 接線由 `__main__.py` 負責：`pool.add_data_handler(manager.handle_incoming_data)`、`pool.add_peer_left_handler(manager.remove_peer)`。

**提供給 core / canvas：**
- core 註冊 handler 接收封包，用送出方法發封包，並負責決定「誰可以收」。
- 封包大小上限為 4 MiB；圖片請先壓縮再送。

## 尚未完成
- [ ] `DRAW_STROKE` 在畫圖階段要不要使用（Canvas / Core 決定）。
- [ ] `CANVAS_SNAPSHOT` 的圖片格式與大小待 Canvas 確認（目前暫定 base64 PNG）。
- [ ] 房主自己也是玩家：`send_*` 不能送給自己，`broadcast_*` 也不會送給自己（p2p 連線清單不含自己），需要本機直送機制，在 issue #7 討論。
- [ ] `DEAL_WORD` 沒有帶角色欄位，UI 如何得知自己是間諜待 Core 決定。
