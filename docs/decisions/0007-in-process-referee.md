# 0007. 裁判邏輯內嵌於開房者的遊戲程式

- 狀態：架構決議已核准（此文件隨 PR #5 提案，尚未合併至 main）
- 日期：2026-11-22
- 決策者：banahaker（team leader）
- 取代：[ADR 0003](0003-host-authority.md)
- 來源：<https://github.com/NTUST-ICN-G7/Pretend2Paint/pull/5#issuecomment-7080008547>、<https://github.com/NTUST-ICN-G7/Pretend2Paint/pull/5#issuecomment-7080128245>

## 背景

遊戲需要權威節點出題、指定間諜、收集畫作與投票、決定分數。原 ADR 0003 將房主作為權威節點，
但開房者也應參與遊戲。另開獨立裁判程序會增加非玩家節點的身分、啟動及管理成本；
若仍位於同一台電腦，亦不能防止該電腦的操作者檢查秘密狀態。

## 決定

1. **所有真人都參賽**，包含開房者。開房者額外具有大廳管理權限，不是旁觀裁判。
2. **裁判是開房者遊戲程式內的元件**：負責出題、指定間諜、收畫作與投票、計分及權威狀態。
   不另啟動獨立裁判程序，也不建立一個非玩家的 P2P 節點或玩家名額。
3. 依 [ADR 0004](0004-threading-model.md)，裁判邏輯與 p2p、streaming、core 於同一條背景
   asyncio event loop 執行；UI 仍在主執行緒，跨執行緒使用 thread-safe queue 傳送事件。
4. 遊戲狀態以房主程式中的裁判元件為準，其他玩家端提交自己的動作。
5. 接受**開房者能修改程式或查看本機機密資訊**的課堂專案風險；此架構不聲稱防止房主作弊。

## 影響及界線

- 原 [ADR 0003](0003-host-authority.md) 被本決策取代，歷史內容仍保留。
- [ADR 0005](0005-secret-information.md) 的秘密資料保護仍然有效：答案、提示、間諜身分等
  不可廣播；公開前的畫作也受到限制。房主自己是玩家，不代表應向其他客戶端洩漏秘密。
- `common.types.Phase`、`common.types.Role`、封包格式與跨模組公開 API 仍依既有正式契約；
  修改必須另循跨模組協調程序。
- 間諜參考圖自動選取、REVIEW、VOID、停權、加權選角、計分、平票、人數及回合數等候選玩法，
  **均非本 ADR 核准事項**，不得因已實作在候選 Part B 中便視為正式規則。
- 房主斷線／重新連線及逾時機制仍待 [Issue #8](https://github.com/NTUST-ICN-G7/Pretend2Paint/issues/8)
  與相關模組討論；大廳資訊及本機訊息仍待 [Issue #7](https://github.com/NTUST-ICN-G7/Pretend2Paint/issues/7)。
