# Game Rules v1.2.0 / 遊戲規則 v1.2.0

## 1. Players and authoritative referee / 玩家與自動裁判

Four to seven human players participate. A separate automatic referee process holds private game state, regardless of who opened the lobby. The referee is not a spectator and never occupies a player slot. A player has an internal stable ID, a separately randomized public player label, and a separately randomized public drawing label each attempt.

四到七名真人全部參與遊戲。獨立自動裁判程序保存隱藏資訊，不因誰建立大廳而改變。裁判不佔玩家名額。每名玩家的內部 ID 固定，但公開玩家編號與畫作編號每次開局都獨立隨機產生。

## 2. Word selection and weighted spy / 出題及加權選角

The referee selects a question from the question bank, distributes the full answer privately to each civilian, and distributes only the hint to the spy. Spy selection uses weight `1/(1+s)^2`, where `s` counts **completed** rounds in which that player was spy. Repeated spy selection remains possible. A void attempt does not increase anyone's role history.

裁判從題庫抽題，私下將完整答案傳給一般玩家，將提示傳給間諜。選間諜採 `1/(1+s)^2` 加權，其中 `s` 僅計入已完成且曾擔任間諜的回合；仍可能連續當間諜。作廢回合不增加角色歷史。

## 3. Drawing / 作畫

Civilians receive 30 seconds to draw independently on separate canvases. At the server-side deadline, the latest accepted version of each civilian's drawing is finalized; a missing drawing is replaced with a blank canvas. The referee automatically selects one civilian drawing uniformly at random, privately shows it to the spy, and allows the spy 30 seconds to draw. The spy's missing drawing is likewise a valid blank.

一般玩家同時進行獨立白板作畫 30 秒。伺服器截止時間到時採用最後接收的有效快照，沒有資料則補上合法白紙。裁判從一般玩家畫作中等機率自動抽一張，私下給間諜參考，讓間諜畫 30 秒；間諜逾時未畫也自動交白紙。

## 4. Sequential civilian review / 一般玩家逐張審查

All final drawings are presented **one at a time**, in a randomized order, to civilians only. Each drawing is displayed for five seconds. The default is NO violation; each civilian may positively flag only a limited number per attempt: one for a four- or five-player game, two for six or seven. A flag is counted only once per reviewer per drawing. The author can vote on their own picture. The spy has no effective review vote.

所有最終畫作以隨機順序**逐張**給一般玩家審查，每張五秒。預設不同意違規。四、五人遊戲每名一般玩家最多按一次；六、七人最多按兩次。同一玩家同一張圖不能重複按，作者也可以審查自己作品；間諜不具有有效審查權。

A picture is confirmed in violation if at least `ceil(2*(N-1)/3)` civilian review votes support the violation, where `N` is the number of active players. This rule is about **recognizable writing**, not about whether the written word equals the answer. Reviews are human votes, not OCR. A confirmed drawing is withheld from the spy during any later guess phase, but it **remains eligible for civilian voting**. The spy's selected reference may already have been seen; such a case triggers the void rule below.

當至少 `ceil(2*(N-1)/3)` 位一般玩家同意違規，即判定畫作違規，`N` 為當回合人數。規範針對**可辨認的文字**，不管文字是否為正確答案；判定是玩家投票共識，不是 OCR。違規畫作在間諜後續猜詞前暫不公開，**但依然保有被投票資格**。如果違規的是間諜先前看到的參考圖，則適用後述回合作廢規則。

## 5. Penalties / 處罰

The first accepted violation by an author deducts 15 points. The second accepted violation by that author removes the player **after** the attempt is settled. Removal is game-level, not a global account ban. A reviewer's unsuccessful positive votes accumulate as a consecutive streak: three successive failures trigger -3; a fourth failure triggers a further -6 and one future eligible civilian-review suspension; the streak resets. A successful positive vote resets the failure streak. No review action does not count as failure. Suspensions that would make the fixed approval threshold unattainable are deferred.

同一作者第一次經通過的違規審查扣 15 分；第二次在該次開局結算**後**移出本場遊戲，不是封鎖帳號。審查者連續按下違規但未通過的次數累加：連續第三次扣 3 分；第四次再扣 6 分並在下一個符合資格的審查回合暫停權限，接著連續失敗次數歸零。一次成功審查會重設失敗連續次數；沒按按鈕不算失敗。若執行暫停會導致固定審查門檻無法達成，則延後暫停。

## 6. VOID reference / 參考圖違規作廢

If and only if the exact civilian drawing selected as the spy's reference is confirmed in violation, the attempt becomes `VOID_REFERENCE_VIOLATION` immediately after review. Skip civilian voting and spy guessing; award **zero normal outcome points** to everyone, but retain all confirmed author penalties and reviewer consequences. Do not increment completed rounds or completed spy-role history. Increment the unique attempt ID, choose a new word, role, anonymization and reference on the replacement attempt. If player removal leaves fewer than four active players, the referee must terminate or return to lobby instead of repeating forever.

**只有**間諜實際抽到的那張一般玩家參考圖被確認違規時，才在審查結束後將本次開局判為 `VOID_REFERENCE_VIOLATION`。直接跳過一般玩家投票和間諜猜詞，所有人的正常勝負分數為零，但保留作者及審查者處罰。不增加有效回合數，也不增加完成回合的間諜歷史；補局必須使用新開局識別碼、重新抽題、選角、匿名洗牌與抽參考圖。若移出玩家後不足四人，裁判應終止或返回大廳，不可無限重試。

A violation of the spy's own drawing, or of another civilian drawing that was NOT selected as the reference, **does not void** the attempt. The spy's drawing remains a valid voting candidate despite review violations. The old rule that review exclusion automatically gives spy escape points is superseded.

間諜自己的圖違規、或其他**未被抽為參考圖**的一般玩家作品違規，**都不會作廢**。間諜的畫作即使被判違規，仍可被投票。舊版「違規畫作排除候選、間諜因此自動逃脫」已被新決定取代。

## 7. Anonymous civilian voting / 匿名一般玩家投票

After review, every civilian simultaneously sees the same anonymous gallery, with the selected reference author marked as a confirmed innocent. Each civilian may cast one vote for a drawing other than their own or the marked innocent drawing; missing votes are abstentions. The spy has no effective vote. The client submits only the public drawing label, which the referee privately maps to the stable player ID before validating and counting. No author mapping or raw individual votes are disclosed before the result is locked.

審查後，一般玩家同時看到全部匿名畫作；被間諜抽中參考圖的作者標記為清白。一般玩家各有一票，不可投自己或已標記的清白作品；未投視為棄權。間諜沒有有效選票。客戶端只送出公開畫作編號，由裁判私下換成穩定的玩家 ID 後驗證與計票。結果鎖定前不得公開作者對應或個別選票。

## 8. Result and guess / 投票結果與猜詞

If the spy alone has the highest **positive** vote count, the spy is caught and must guess. If a civilian alone has the highest vote count, the spy escapes without guessing. If the top is tied, or nobody votes, the spy does not receive escape points but may guess. A missing or timed-out guess is incorrect. All drawings, including ones withheld by the review, are finally revealed to **everyone** only after the outcome can no longer be altered.

間諜若獲得**唯一最高且大於零**的票數，即被抓並須猜詞。如果其他一般玩家唯一最高票，間諜成功逃脫，不必猜詞。最高票平票或無有效票時，間諜沒有逃脫分，但可以猜詞；逾時未猜視為猜錯。所有會影響結果的操作已無法變更後，才將包括先前暫時隱藏者在內的全部畫作公開給**所有玩家**。

## 9. Provisional score balance / 暫定分數

| Outcome / 結果 | Spy | Correctly voting civilian (N players) |
|---|---:|---:|
| Spy escapes / 間諜逃脫 | +3 | `5+3*(N-4)` |
| Spy caught, guess right / 被抓猜對 | +1 | `5+3*(N-4)` |
| Spy caught, guess wrong/timeout / 被抓猜錯或逾時 | -3 | `8+3*(N-4)` |
| Top tied/no votes, guess right / 平票或無票猜對 | +1 | `5+3*(N-4)` |
| Top tied/no votes, guess wrong/timeout / 平票或無票猜錯 | 0 | `5+3*(N-4)` |
| Void reference / 參考圖違規作廢 | 0 normal | 0 normal |

Penalty deltas are added after normal scoring. Final-score ties share rank. These coefficients are playtesting defaults, not proven balanced.

違規處罰另外加總到正常勝負分數。同分並列。以上係數是實測前的暫定值，不代表已經證明平衡。

## 10. Timing, disconnection and trust / 計時、斷線及信任

Part A must enforce deadlines based on the authoritative server, snapshot blank canvases if no packet arrives, tolerate reconnection where possible, and stop the match if fewer than four active players remain. Authenticate senders, reject late and duplicate packets, and never leak the hidden author map, answer or unapproved drawings in client payloads. Part B supplies validations and outcomes but has no actual network I/O or timers.

A 模組必須以權威伺服器時間判斷期限，沒有收到畫作時補白紙，可行時提供重連寬限，並在不足四人時停止比賽。封包需認證傳送者，拒絕遲到與重複事件，不得在客戶端封包夾帶作者映射、答案或未核准的畫作。B 僅提供規則驗證與判定，不具備網路 I/O 或真正計時器。
