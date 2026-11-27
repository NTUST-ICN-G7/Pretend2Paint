# 0006. UI 框架

- 狀態：通過
- 日期：2026-11-22
- 決策者：banahaker（team leader），依 UI 組評估

## 背景
UI 組需要選一個 Python GUI 框架，必須支援畫布繪圖、在主執行緒跑 event loop，且有 Python 3.14 的安裝檔。

## 候選
| 框架 | 優點 | 缺點 |
| :--- | :--- | :--- |
| tkinter | 內建、不用額外安裝、有 Canvas | 外觀較陽春 |
| pygame-ce | 適合遊戲、繪圖彈性高 | 按鈕、輸入框等元件要自己做 |
| PyQt6 / PySide6 | 元件完整、外觀好 | 學習成本較高、套件較大 |

## 決定
UI 使用 **tkinter**。

- Python 內建，不需要 `uv add` 任何 GUI 套件，所有組員環境一致。
- 有 `Canvas` 可以直接做畫布、筆畫與顯示畫作。
- 學習成本低，適合第一次做 GUI 的組員。

## 影響
- UI 在主執行緒跑 tkinter 的 `mainloop()`，用 `root.after()` 定時輪詢 `ui_queue` 取得 core 的事件（配合 [ADR 0004](0004-threading-model.md)），不可在 UI 執行緒做網路 I/O。
- 外觀較陽春，畫面以清楚、可用為主。
- 畫作需由 `Canvas` 匯出成 `CANVAS_SNAPSHOT` 使用的圖片格式（目前暫定 base64 PNG，見 [protocol.md](../protocol.md) 待決問題），轉換方式由 UI 組與 Streaming 組確認。
- 不新增依賴；若之後需要額外套件（例如圖片轉換），需先經 team leader 同意。
