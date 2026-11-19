# 0004. 執行緒模型

- 狀態：通過
- 日期：2026-11-20
- 決策者：banahaker（team leader）

## 背景
UI 框架的 event loop 會佔用主執行緒，網路 I/O 不能阻塞 UI；多執行緒同時改遊戲狀態容易出現 race condition。

## 決定
- **主執行緒**：UI event loop。
- **一條背景執行緒**：asyncio event loop，跑 p2p、streaming、core。
- 兩者之間只透過 `queue.Queue` 交換事件（UI → 網路、網路 → UI）。
- 禁止跨執行緒直接呼叫對方的方法或修改對方的資料。

## 影響
- p2p 使用 asyncio 實作（`asyncio.start_server`、`open_connection`、`DatagramProtocol`）。
- core 只在 asyncio 執行緒內被呼叫，不需要 lock。
- UI 每個 frame / 定時器從 queue 取事件來更新畫面。
