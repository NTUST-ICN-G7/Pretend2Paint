---
name: write-adr
description: 在 docs/decisions/ 新增一份 Pretend2Paint 架構決策紀錄（ADR）。在做出或記錄會影響多個模組的設計決定（協定、架構、工具、遊戲規則解釋）時使用。
---

# 撰寫 ADR

## 什麼時候需要
- 會影響兩個以上模組的決定
- 推翻或修改既有 ADR
- 工具鏈、依賴、程式風格的規範
- 遊戲規則中原本沒寫清楚、需要統一解釋的地方

單一模組內部的實作細節不需要 ADR。

## 步驟
1. 看 `docs/decisions/README.md` 的列表，取**最大編號 + 1**（四位數，例如 `0007`）。
2. 複製 `docs/decisions/0000-template.md` 為 `docs/decisions/NNNN-<英文短描述>.md`。
3. 填寫：
   - **狀態**：一律先寫「提案」。只有 team leader 能改成「通過」。
   - **日期**：今天。
   - **決策者**：留給使用者填，或填使用者告訴你的人。
   - **背景 / 決定 / 影響**：具體寫出各模組需要配合的事。
4. 在 `docs/decisions/README.md` 的表格新增一列。
5. 如果是推翻舊 ADR：**不要改舊 ADR 的內容**，只把舊的狀態改成「已被 NNNN 取代」。
6. 如果決定影響到 `AGENTS.md`、`docs/architecture.md`、`docs/protocol.md` 或 `docs/game-rules.md`，列出需要同步修改的地方告訴使用者（這些檔案由 team leader 維護）。

## 注意
ADR 是在記錄**已經討論過**的決定。不要自己替團隊做決定然後寫成 ADR；不確定時先問使用者。
