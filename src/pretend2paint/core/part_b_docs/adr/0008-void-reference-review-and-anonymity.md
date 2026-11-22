# ADR 0008: Void Reference Violations and Anonymous Civilians-only Voting

**Status:** Accepted for Part B API implementation, 2026-11-22. **Supersedes:** conflicting sections of teammate `README.pdf` draft, v1.0/v1.1 Part B integration documents.

**狀態：** 2026-11-22 已納入 B 規則 API。**取代：** 組員 README 草稿、v1.0/v1.1 整合文件中與新規則衝突的部分。

## Context / 背景

Human-only hosts exclude a player from participating. A spy's physical mouse activity can reveal their real-world identity; however, if ballots target anonymous drawings, the identity alone does not determine which image to vote for. The team therefore favors independent shuffled public player and drawing labels instead of mandatory gesture minigames.

真人裁判會排除一名參與者。間諜獨立操作可能透露現實身分；但若投的是匿名畫作，只知道真人身分不會直接知道該選哪張。故採用獨立打亂玩家與畫作公開編號，不強制加入手勢小遊戲。

## Decision / 決策

The referee automatically and privately selects one civilian reference. Civilians review all frozen images sequentially, using a per-player quota and a fixed two-thirds-of-civilians threshold. Violations affect temporary spy visibility and participant discipline but never drawing vote eligibility. A flagged actual reference voids the attempt, retaining penalties while preserving the number of required completed rounds and the completed-spy history. Spy ballots are disallowed; ties trigger guess without negative normal spy score on failure. Reviewer abuse is discouraged by failure streak penalties and deferred suspensions.

裁判自動私下選一張一般玩家參考圖。一般玩家按順序逐張審查，受每人額度及固定三分之二門檻限制。違規只影響間諜在猜詞前觀看及玩家處罰，不影響畫作被投資格。間諜實際抽到的參考圖被判違規則作廢，保留處罰，但不消耗有效回合、也不計完成間諜次數。間諜不能投有效票；平票時可猜，猜錯不扣正常分。審查濫用透過失敗連續紀錄及延後執行的暫停審查權處理。

## Tradeoffs and excluded work / 取捨與未實作

The rule does not prevent a spy from initially seeing written information, but a void result prevents that unfair advantage from changing normal scoring if the review confirms the drawing. Human-vote review can be mistaken, and actual network authenticity/deadlines belong to Part A/Streaming. We do not claim automated text recognition, perfect fairness, complete anti-collusion, or a working hostless socket runtime.

規則無法在事前阻止間諜看到參考圖中的文字，但若審查確認，作廢回合可讓這項資訊優勢不改變正常計分。玩家投票可能誤判，封包認證與期限由 A/Streaming 實作。本案不宣稱能自動辨識文字、完全公平、完全防串通，或已具備可執行的無真人房主 Socket 系統。
