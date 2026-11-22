# p2p — P2P Infra

負責人：葉柏辰

> 先讀根目錄的 `AGENTS.md`。這份檔案只補充本模組的規則；兩者衝突時以根目錄為準，並告訴使用者。
> 對外 API 說明寫在同目錄的 `README.md`（使用 `module-api-doc` skill）。

## 職責
- UDP broadcast：區網內的 node discovery。
- TCP full-mesh：建立、維護、關閉與其他節點的連線（connection pool）。
- 節點加入 / 離開 / 斷線通知。
- **只處理 raw bytes**，不管封包格式與遊戲規則。

## 對上層的介面（streaming 需要）
- 送出（`ConnectionPool`，簽名需符合 streaming 的 `ConnectionPool` Protocol）：
  - `send(peer_id: PlayerId, data: bytes)`：單播給一個節點。
  - `send_many(peer_ids: Iterable[PlayerId], data: bytes)`：送給多個指定節點；**空清單丟 `ValueError`，不可當成「全部」**。
  - `broadcast(data: bytes)`：送給所有已連線節點，不可用於機密資訊。
  - **必須支援只發給指定節點**（單播），機密資訊靠它，見 `docs/decisions/0005-secret-information.md`。
- 接收：讓上層**註冊 callback**：`add_data_handler(handler(peer_id, raw_bytes))`、`add_peer_joined_handler(handler(peer_id))`、`add_peer_left_handler(handler(peer_id))`。
- 完整 API 以同目錄的 `README.md` 為準。
  - **不可 `import pretend2paint.streaming`** 或任何上層模組（分層規則）。

## 規則
- 用 asyncio 實作（`asyncio.start_server` / `open_connection` / `DatagramProtocol`），跑在背景執行緒的 event loop，見 `docs/decisions/0004-threading-model.md`。
- 不要阻塞 event loop（不要用 `time.sleep`、同步的 `socket.recv`）。
- port、broadcast 間隔等設定集中成常數，不要散落各處。
- 斷線、連線失敗要處理並通知上層，不要讓例外把 event loop 弄掛。
- 測試放 `tests/p2p/`；能用 localhost 測就用 localhost，不要依賴實體網路。

## 完成前
`uv run ruff check . && uv run ruff format --check . && uv run lint-imports && uv run pytest`
