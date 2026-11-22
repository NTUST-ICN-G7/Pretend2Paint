> **HISTORICAL / 歷史存檔:** This record reflects an older release. For the CURRENT v1.2 contract see `docs/adr/0008-void-reference-review-and-anonymity.md`, `docs/game-rules.md`, and `docs/INTEGRATION.md`.
> **歷史存檔：** 本文件是舊版決策，請以上述 v1.2 文件為準。

# ADR 0007 — All Humans Play, Automatic Deadline Finalization / 自動裁判及截止定稿

**Decision / 決定： ACCEPTED BY USER (game behavior); PROPOSED BY ASSISTANT (server architecture).**
**遊戲規則已由使用者確認；伺服器架構為建議，待全組確認。**

## Context / 背景
The teammate's README draft allocated one human participant to the host-only referee role. The user clarified that every human should play, all outcomes are adjudicated automatically, deadline-finished blank canvases are valid drawings, and an unanswered spy guess is wrong.

組員的 README 草稿要求有一位真人只當房主裁判；使用者更正為所有真人都應能參與，規則由程式自動裁決，時間到即使未動筆也要有白紙畫作，間諜猜詞未答則算錯。

## Decision / 決策
Part B accepts `players` as **all participating humans**, not humans excluding a host. A separately running **RefereeEngine / ServerEngine** is proposed for Part A. The referee process does not get a player ID, voting rights, or points. The room creator may be a player with only lobby management privileges. Server-side deadlines finalize submitted snapshots and fill missing ones with blank canvases; spy guessing timeout resolves to `False` and then the normal loss scoring is applied.

B 的 `players` 代表**所有真正參與的玩家**，不再是「扣除房主的人」。建議 A 提供在獨立程序執行的 **RefereeEngine / ServerEngine**，不取得玩家 ID、選票或積分。開房者仍是玩家，只可能有大廳設定權限。由伺服器截止時間確定快照，缺少畫作時補白紙；間諜猜詞逾時判 `False` 並依猜錯結算。

## Compatibility / 相容性
Public v1.0.0 rule signatures remain compatible; `is_correct_guess(None, card)` now returns `False`, and two helpers are added: `complete_drawings(...)` and `validate_votes(...)`. `RoundOutcome` gains optional `marked` at the end, and scoring validates this mark when supplied. Part A's `HostEngine` structure and event dispatch **must be updated separately by its owner**; this package does not alter their files.

v1.0.0 原有公開函式維持相容；`is_correct_guess(None, card)` 現在回傳 `False`；新增 `complete_drawings(...)`、`validate_votes(...)`，並在 `RoundOutcome` 最後新增選填 `marked`，提供計分階段的標記驗證。A 的 `HostEngine` 及事件分派**必須由原負責組員另外更新**，此套件沒有直接修改他們的檔案。

## Consequences / 影響
A must not trust clients for timers or secret access. The automatic referee is a separate process, not necessarily a separate physical machine; if it shares a machine with one player, that machine operator may still inspect secret memory. Reconnect policy and fairness of the spy's drawing time remain open.

A 不應信任玩家端計時或秘密存取權限。自動裁判是獨立**程序**，不一定要獨立實體電腦；若與某位玩家共用機器，該操作人員仍可能檢查秘密記憶體。斷線重連政策與間諜畫圖時間的公平性尚待決議。
