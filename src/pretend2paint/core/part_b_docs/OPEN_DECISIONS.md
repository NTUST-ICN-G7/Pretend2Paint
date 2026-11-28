# Open Design / Integration Questions v1.2.0 / 尚待討論事項

This document explicitly separates committed user rules from implementation limitations and proposed policies. It is **not** evidence that Part A or the network integration already works.

本文件區分已確認的使用者規則、實作限制與後續建議，**不代表** A 或網路整合已實際完成。

## Settled / 已定案

- All humans participate; an automatic referee makes decisions. / 所有真人都能玩，程式自動裁判。
- Each attempt independently randomizes public player and drawing labels. / 每次開局獨立隨機玩家與畫作編號。
- Automatic reference drawing selection; keep the risk that the spy may see a violating reference. / 系統自動選參考圖，接受可能抽到違規圖的風險。
- Sequential random-order review, five seconds per picture, one limited violation button; default NO. / 每張五秒、隨機順序、單一有限額度違規鍵、預設否。
- Approved violation does **not** change voting eligibility. / 違規畫作仍可被投票。
- If the spy's actual reference is flagged, the attempt is void, without consuming one of the target completed rounds. All discipline remains. / 間諜抽中的圖違規則作廢、不消耗預定有效回合，處罰照計。
- Spy does not cast an effective ballot; civilians vote for anonymous drawings. / 間諜不投有效票，一般玩家投匿名畫作。
- Tie or no vote is neutral, with a spy guess; wrong or timeout receives zero spy normal points. / 平票或無票可猜，猜錯／逾時正常分零。
- Initial score table and weighted spy are PROVISIONAL adjustable values. / 計分和角色加權初值可調整、尚待實測。

## Pending policy or integration / 仍需實測或其他組員完成

1. **Reconnection deadline / 重連期限**. Part B does not provide real-time event-loop or socket reconnection logic. Decide whether a player who disconnects during a fixed phase can resume and which drawing snapshot wins. Recommended: the authoritative latest accepted snapshot; a missing snapshot is blank.
   B 不實作真實事件迴圈或 Socket 重連，需確認斷線後何時可恢復，以及畫作定稿準則。建議採最後已接收的合法快照，無資料則白紙。
2. **Server outage / 裁判程序失效**. How to handle a crash and restore state: terminate/return to lobby for first version; durable recovery is optional.
   伺服器本身當機的恢復策略：第一版建議直接終止或返回大廳，持久化復原可留待後續。
3. **Visual content / 文字認定**. Review votes are not optical character recognition (OCR). Agree whether numbers, isolated letters, punctuation, arrows, logos, and symbolic shapes count as forbidden text; establish illustrative examples to reduce ambiguity.
   違規判定不是 OCR；須明定數字、單獨字母、標點、箭頭、標誌和符號是否視為文字，建議建立範例。
4. **History and roles / 加權公平性**. Weighted random can still produce repeated spies. Its exact exponent of 2 and scoring are unverified balance parameters. / 加權隨機仍可能連續當間諜，平方權重及分數尚未經實際玩家平衡驗證。
5. **Dynamic thresholds / 動態門檻**. User discussed lowering thresholds for repeat violators, but the most recent design recommendation kept thresholds fixed because quotas plus penalties already restrict misuse. The current implementation keeps fixed configurable ratios; no automatic historic threshold change is enabled.
   曾討論依歷史降低審查門檻，但近期建議先固定比例，因為有限額度與處罰已能限制濫用。本版門檻比例可設定，未自動依歷史變更。
6. **Reviewer suspension privacy / 暫停權限保密**. Part B defers suspensions rather than lower the fixed population threshold; Part A must implement a UI that does not leak hidden roles or map identities. / B 會在必要時延後暫停而非降低門檻；A/UI 需避免洩漏角色或作者對應。
7. **Minimum players / 最少人數**. Removal after settling may leave fewer than four players, in which case A stops the match. The exact UI final-screen wording is a team decision. / 回合後移除導致少於四人時由 A 結束；UI 提示文案由組員決定。
8. **Anti-collusion / 防串通**. Game logic cannot prevent offline collusion or visually identifying personal drawing styles; the system should not leak the author mapping through serialization. / 規則無法消除場外串通或畫風辨識，但系統必須保護作者映射。
9. **Legacy API compatibility / 舊 API 相容**. Score semantics, phases and effective voters are intentionally changed from v1.1.0. Part A must update its calls and tests. / 分數、階段與有效投票者相較 v1.1.0 刻意改變，A 必須同步更新。
