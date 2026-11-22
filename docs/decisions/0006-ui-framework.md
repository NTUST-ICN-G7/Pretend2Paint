# 0006. UI 框架

- 狀態：待定
- 日期：2026-11-20
- 決策者：banahaker（team leader）

## 背景
UI 組需要選一個 Python GUI 框架，必須支援畫布繪圖、在主執行緒跑 event loop，且有 Python 3.14 的安裝檔。

## 候選
| 框架 | 優點 | 缺點 |
| :--- | :--- | :--- |
| tkinter | 內建、不用額外安裝、有 Canvas | 外觀較陽春 |
| pygame-ce | 適合遊戲、繪圖彈性高 | 按鈕、輸入框等元件要自己做 |
| PyQt6 / PySide6 | 元件完整、外觀好 | 學習成本較高、套件較大 |

## 決定
待 UI 組評估後由 team leader 決定，決定後更新本文件與 `ui/AGENTS.md`。
