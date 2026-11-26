# p2p — 區網節點發現與 TCP full-mesh 連線池

負責人：葉柏辰

## 概觀

- **做什麼**：用 UDP broadcast 在區網找到其他節點，和每個節點維持一條 TCP 連線（full-mesh），
  送收 **raw bytes**，並通知上層節點加入 / 離開。
- **不做什麼**：不管封包格式（framing、JSON）、不管遊戲規則，也不決定「該送給誰」。
- **分層位置**：最底層（只依賴 `common`）。`streaming` 呼叫 p2p 送資料；p2p 收到資料時呼叫
  `streaming` 註冊的 callback（p2p **不會** import 任何上層模組）。
- **執行緒**：所有 API 都在背景 asyncio 執行緒呼叫（[ADR 0004](../../../docs/decisions/0004-threading-model.md)）。

> 目前狀態：**Prototype 已實作**（本 README 描述的 API 都可用，並有 `tests/p2p/` 測試）。

## 快速使用

```python
import asyncio

from pretend2paint.p2p import ConnectionPool


async def main() -> None:
    pool = ConnectionPool()  # peer_id 自動產生；預設開啟 UDP discovery

    pool.add_data_handler(lambda peer_id, data: print(peer_id, data))
    pool.add_peer_joined_handler(lambda peer_id: print("joined", peer_id))
    pool.add_peer_left_handler(lambda peer_id: print("left", peer_id))

    await pool.start()  # 開 TCP server + 開始廣播，之後同區網的節點會自動連上
    # await pool.connect("192.168.0.12", 50123)  # discovery 被擋時可手動連

    pool.send("some-peer-id", b"only for you")  # 單播
    pool.broadcast(b"hello everyone")  # 廣播（不可用於機密資訊）

    await asyncio.sleep(60)
    await pool.stop()


asyncio.run(main())
```

和 `streaming` 接起來（在 `__main__.py`）：

```python
pool = ConnectionPool()
manager = StreamManager(pool)  # streaming 透過 pool.send / pool.broadcast 送
pool.add_data_handler(manager.handle_incoming_data)  # 收到 bytes 交給 streaming
pool.add_peer_left_handler(manager.remove_peer)  # 斷線時清掉 streaming 的接收 buffer
await pool.start()
```

## API

### `ConnectionPool(peer_id=None, *, room="default", host="0.0.0.0", port=0, discovery=True, discovery_port=50505, discovery_targets=None, discovery_interval=1.0)`

一個 P2P 節點：UDP discovery + TCP 連線池。每個程式建立**一個**。

| 參數 | 型別 | 說明 |
| :--- | :--- | :--- |
| `peer_id` | `PlayerId \| None` | 自己的 id；省略時自動產生 uuid4 hex。**這個 id 就是全遊戲用的 `PlayerId`** |
| `room` | `str` | 網路分區名稱。只會和同 `room` 的節點互連（同一區網開多場遊戲時用） |
| `host` | `str` | TCP 監聽位址 |
| `port` | `int` | TCP 監聽 port；`0` = 由系統挑，實際 port 由 discovery 公告 |
| `discovery` | `bool` | 是否啟用 UDP broadcast discovery |
| `discovery_port` | `int` | UDP discovery port（所有節點要一樣） |
| `discovery_targets` | `Sequence[tuple[str, int]] \| None` | announcement 送往的位址；預設 `255.255.255.255:discovery_port`。主要給測試用 |
| `discovery_interval` | `float` | 廣播間隔（秒） |

#### 屬性

| 屬性 | 型別 | 說明 |
| :--- | :--- | :--- |
| `peer_id` | `PlayerId` | 自己的 id |
| `room` | `str` | 所在 room |
| `listen_port` | `int` | 實際監聽的 TCP port（`start()` 前為 0） |
| `peers` | `frozenset[PlayerId]` | 目前已連線（handshake 完成）的 peer，不含自己 |
| `is_running` | `bool` | 是否已 `start()` 且尚未 `stop()` |

#### `async start() -> None`
- 用途：開 TCP server，並開始 UDP discovery（廣播自己、收到別人的公告就自動連線）。
- 何時呼叫：註冊完 callback 之後、遊戲開始之前。
- 執行緒：asyncio 執行緒，`await`。
- 例外 / 錯誤：`RuntimeError`：重複 start；`OSError`：port 被占用等。

#### `async stop() -> None`
- 用途：關閉所有連線、server 與 discovery。
- 何時呼叫：程式結束時。可重複呼叫。
- 執行緒：asyncio 執行緒，`await`。
- 注意：自己 `stop()` **不會**觸發 `peer_left` callback。

#### `async connect(host: str, port: int) -> PlayerId`
- 用途：手動連到某個節點（例如學校 Wi-Fi 擋 UDP broadcast 時輸入對方 IP:port）。
- 回傳：對方的 `peer_id`；已連線過則回傳既有 id，不會產生第二條連線。
- 執行緒：asyncio 執行緒，`await`。
- 例外 / 錯誤：`RuntimeError`：尚未 `start()`；`OSError` / `TimeoutError`：連不上；
  `HandshakeError`：對方不是本程式、`room` 不同、或連到自己。

#### `send(peer_id: PlayerId, data: bytes) -> None`
- 用途：**單播**，只送給一個 peer。答案、提示、間諜身分、`REVEAL` 前的畫作都必須用這個
  （[ADR 0005](../../../docs/decisions/0005-secret-information.md)）。
- 執行緒：asyncio 執行緒，同步呼叫、不會阻塞（寫入 socket buffer 後立即返回）。
- 例外 / 錯誤：`TypeError`：`data` 不是 bytes-like；`PeerNotConnectedError`：該 peer 不在線。

#### `send_many(peer_ids: Iterable[PlayerId], data: bytes) -> None`
- 用途：送給多個指定 peer（重複的 id 只送一次）。
- 執行緒：同 `send`。
- 例外 / 錯誤：`ValueError`：`peer_ids` 為空（**空清單不等於全部**，避免機密誤廣播）；
  `TypeError`：`peer_ids` 是字串；`PeerNotConnectedError`：任一 peer 不在線，此時**整批都不送**。

#### `broadcast(data: bytes) -> None`
- 用途：送給所有已連線的 peer（不含自己）。**不可用於機密資訊。**
- 執行緒：同 `send`。
- 例外 / 錯誤：`TypeError`：`data` 不是 bytes-like。沒有任何 peer 時不做事。

### 例外

| 例外 | 說明 |
| :--- | :--- |
| `P2PError` | p2p 所有例外的基底類別 |
| `PeerNotConnectedError(P2PError, LookupError)` | 指定的 peer 沒有連線 |
| `HandshakeError(P2PError)` | 連線後 handshake 失敗 |

### Callback / 事件

用 `add_*_handler()` 註冊，可註冊多個，依註冊順序呼叫。全部在 asyncio 執行緒被呼叫，
**不可阻塞**；callback 丟出的例外會被記錄（`logging`）後忽略，不會讓連線或 event loop 掛掉。

| 註冊方法 | Callback 簽名 | 什麼時候被呼叫 |
| :--- | :--- | :--- |
| `add_data_handler(handler)` | `DataHandler = Callable[[PlayerId, bytes], None]` | 收到某個 peer 的資料。**bytes 是 TCP 串流的任意片段**，可能半包或黏包，由 streaming 負責 framing |
| `add_peer_joined_handler(handler)` | `PeerHandler = Callable[[PlayerId], None]` | 與某 peer 的 TCP 連線建立且 handshake 完成 |
| `add_peer_left_handler(handler)` | `PeerHandler = Callable[[PlayerId], None]` | 與某 peer 的連線斷開（對方關閉、網路中斷） |

保證：

- 同一個 peer 的 `data` 依送出順序抵達（TCP）。
- 同一個 peer 在 `joined` 之後才會有 `data`，`left` 之後不再有 `data`。
- 兩個節點之間只會有一條連線：雙方同時互連時，會保留由 `peer_id` 較小一方發起的那條，
  且不會重複觸發 `joined` / `left`。

## 運作方式（給好奇的人）

1. **Discovery**：每隔 `discovery_interval` 秒對 `255.255.255.255:discovery_port` 廣播
   `{"app", "v", "kind": "announce", "peer_id", "room", "port"}`（JSON）。收到同 `room` 的公告後，
   由 `peer_id` 較小的一方主動用 TCP 連線。
2. **Handshake**：TCP 連上後雙方互送 `b"P2PH" + 2-byte 長度 + JSON {"peer_id", "room", "port"}`，
   驗證通過才算 `joined`。
3. **之後**連線上只傳上層給的 raw bytes，p2p 不加任何 header。

以上格式只在 p2p 內部使用，與 [protocol.md](../../../docs/protocol.md) 的 streaming 封包無關。

## 與其他模組的約定

**提供給 `streaming`**：

- 符合 streaming 的 `ConnectionPool` Protocol：`send(peer_id, data)`、`broadcast(data)`；另外多提供
  `send_many(peer_ids, data)`。
- 收到資料呼叫 `handle_incoming_data(peer_id, raw_bytes)`、斷線呼叫 `remove_peer(peer_id)`
  ——由 `__main__.py` 用 `add_data_handler` / `add_peer_left_handler` 接上。

**提供給 `core` / `ui`**（透過 `__main__.py` 轉接、經 `queue.Queue` 給 UI）：

- `peer_id` 就是 `PlayerId`；`peers` 是目前在線名單。
- `peer_joined` / `peer_left` 可用於大廳名單與斷線處理。**房主斷線**時 p2p 只負責通知
  `peer_left(host_id)`，要換房主或結束遊戲由 core 決定。

**需要別人提供**：無。

## 尚未完成

- [ ] 寫入的背壓（backpressure）：目前 `send` 直接寫入 buffer，不等 `drain()`；畫作很大時可能需要
- [ ] 斷線自動重連（目前靠 discovery 再次公告後重新連上，會得到新的 `joined`）
- [ ] Discovery 是否要帶玩家暱稱，讓大廳在加入前就能顯示名字（待 core / ui 確認）
- [ ] 實機多台電腦的區網測試（學校 Wi-Fi 可能擋 UDP broadcast，必要時用 `connect()` 手動連）
