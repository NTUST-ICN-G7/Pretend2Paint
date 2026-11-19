# P2P Infra

負責人：葉柏辰

維護 P2P 拓樸與 lifecycle 管理。

- UDP Broadcast（node discovery）
- TCP full-mesh / connection pool

## API

（待補：請列出對外提供的類別/函式、參數與用途）

> Streaming 目前需要 connection pool 提供 `broadcast(packet: bytes, targets: list | None)`，收到資料時呼叫 `stream_manager.handle_incoming_data(peer_id, raw_bytes)`。
