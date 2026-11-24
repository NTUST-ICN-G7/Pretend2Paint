# Part B Candidate Integration Contract v1.2.0 / B 模組候選整合契約 v1.2.0

**Audience:** A (Flow / Referee Engine), UI, Streaming/Socket. **Source:** teammate `README.pdf` draft plus user-confirmed revisions. **Scope:** implemented rules API only; no real Socket process is included.

**對象：** A（流程／自動裁判）、UI、Streaming／Socket。**依據：** 組員 README PDF 草案與使用者最新決議。**範圍：** 只有規則 API，沒有真正可連線的 Socket 裁判程序。

> **Status:** Candidate implementation reference, not the approved team integration contract. Only the in-process referee architecture below is approved by [ADR 0007](../../../../docs/decisions/0007-in-process-referee.md). Gameplay, phase order, visibility, voting, scoring and cross-module proposals below remain pending; follow the [team rules](../../../../docs/game-rules.md) and ADR 0005 until separately approved.
>
> **狀態：** 本文件為候選實作參考，不是團隊正式整合契約。僅下述內嵌式裁判架構經 [ADR 0007](../../../../docs/decisions/0007-in-process-referee.md) 核准。下列玩法、階段順序、可見性、投票、計分及跨模組提案仍待確認；另行核准前依[團隊規則](../../../../docs/game-rules.md)及 ADR 0005。

## A. Architecture / 架構

```text
Room creator's game process / 開房者的遊戲程式 (also a player)
  UI: main thread / 主執行緒
  Background asyncio thread / 背景執行緒 (ADR 0004)
    p2p + streaming + core
    core referee component: authoritative state / role secrets
    Part A event/timer engine (NOT SUPPLIED)
    Part B candidate rules package (SUPPLIED)
       | existing player network / 既有玩家網路
       +-- other human player processes / 其他真人玩家程式
All humans play; no separate referee process or player slot.
所有真人均參賽；不另設裁判程序或玩家名額。
```

Only the referee holds `SecretAnonymityMap`, answer, spy ID, drawing-to-author mapping, all vote identities, and moderation ledger. **Do not serialize the entire secret dataclass to a client.** A player's public number `P#` and a drawing's public number `D#` are independent per-attempt aliases and must not be inferred from one another.

只有裁判持有 `SecretAnonymityMap`、答案、間諜 ID、畫作作者映射、個別選票與審查帳本。**不得把整個私密 dataclass 序列化給玩家端。** 玩家公開 `P#` 與畫作 `D#` 是每次開局各自獨立的別名，不能建立編號相等的假設。

## B. Candidate phase flow (not approved for integration) / 候選階段流程（尚未核准整合）

| Phase | Part A responsibilities / A 的責任 | Part B functions / B 函式 |
|---|---|---|
| LOBBY | 4–7 humans, lobby creator also plays / 4–7 人全員可玩 | `GameConfig.validate()` |
| DEAL | Begin unique attempt; choose unused word; weighted spy; send **per-player private** deal / 新開局、選題、選角、私下發題 | `RoundProgress.begin_attempt()`, `WordBank.draw`, `choose_spy(players, rng, history)`, `deal_words` |
| DRAWING | Receive civilian stroke snapshots; server deadline; blank fallback / 保存一般玩家快照、超時補白紙 | `complete_drawings()` |
| SPY_ACTION | Auto choose ONE frozen civilian drawing, show only the image to spy; 30s spy drawing / 自動抽一張私下給間諜、30 秒作畫 | `shuffle_gallery`, `random_pick_index`, `resolve_blind_pick`, `complete_drawings()` |
| REVIEW | Freeze ALL drawings; shuffle public labels and review order; reveal one at a time to civilians for **5 seconds each**; NO is default; wait until all reviewed / 逐張 5 秒、隨機順序、預設不同意 | `build_anonymity_map`, `public_review_order`, `review_round`, `review_threshold`, `review_vote_quota` |
| REVIEW verdict | **If reference drawing is flagged**, settle immediately as VOID, preserve penalties, skip VOTING/GUESS, start replacement attempt after removal check / 參考圖違規立即作廢 | `settle_round(..., outcome=None)` |
| VOTING | Show anonymous full gallery to civilians; publicly mark selected reference drawing as safe; receive votes for D# only / 一般玩家看完整匿名圖廊並投票 | `public_gallery(marked_drawing)`, `decode_public_votes`, `validate_votes(...,spy=spy)`, `tally_votes`, `resolve_vote` |
| SPY_GUESS | Only if spy is uniquely caught, highest vote is tied, or nobody voted; show only NONFLAGGED drawings; server-checked timeout / 被抓、平票、無票才需猜；遮蔽違規圖 | `is_correct_guess(guess_or_None, card)` |
| REVEAL | Lock results, then show **all** final images incl. flagged to EVERYONE; may now publish authors / 結果鎖定才完整公開所有畫作 | Referee-private reveal policy |
| ROUND_END | Score normal only if not void; add review penalties; update completed-round history, scoreboard; remove users and stop if <4 / 正常分＋處罰、記完成回合、移出玩家 | `settle_round`, `apply_scores`, `ranking`, `rank_with_ties`, `winners`, `restrict_ledger` |

**Do not use the old `REVEAL` before `VOTING`.** In v1.2 the stage formerly called reveal has been split into `REVIEW` (civilians only), `VOTING` (civilians see full anonymous gallery) and later `REVEAL` (all including spy after locked decision). This is a candidate-only proposal, not an instruction to revise the approved engine.

**不要在投票前使用舊 `REVEAL` 公開全部畫作。** v1.2 將舊公開階段拆為 `REVIEW`（一般玩家）、`VOTING`（一般玩家看完整匿名畫廊）與最終 `REVEAL`（結果鎖定後所有人可看）。此為候選流程提案，不是修改正式 A 流程的指令。

## C. Data and function contract / 資料與函式契約

```python
from core import (
    GameConfig,
    ScoreRules,
    WordBank,
    RoundProgress,
    choose_spy,
    deal_words,
    complete_drawings,
    shuffle_gallery,
    random_pick_index,
    resolve_blind_pick,
    build_anonymity_map,
    decode_public_votes,
    ModerationLedger,
    review_vote_quota,
    review_threshold,
    review_round,
    validate_votes,
    tally_votes,
    resolve_vote,
    RoundOutcome,
    is_correct_guess,
    settle_round,
    RoundStatus,
    apply_scores,
    restrict_ledger,
)
```

Call order details: `RoundProgress.begin_attempt()` issues increasing `attempts_started`; use `current_attempt_id` as the numeric part of each server-internal attempt identifier, while the actual network protocol should also include its room/match identifier. Keep a distinct `completed_rounds` counter and stop at the target. After a VOID attempt, the count stays unchanged. Never reuse old sequence IDs; reject stale packets for a prior attempt.

呼叫順序：`RoundProgress.begin_attempt()` 產生遞增的 `attempts_started`；`current_attempt_id` 是本局內的開局編號，真實封包還需要房間／比賽識別。`completed_rounds` 與開局次數分開，達標才結束。作廢不增加完成回合，也不能重用先前的封包或事件編號；伺服器必須拒絕舊開局封包。

Choose spy with `choose_spy(players, rng, history)` where `history` counts only successful completed attempts; call `settle_round` to receive the correct next history. Use `random.SystemRandom()` for real gameplay; use `random.Random(seed)` ONLY for deterministic tests. Automatic reference selection uses `shuffle_gallery(civilians, rng)` then `random_pick_index(len(order),rng)` and `resolve_blind_pick(order,index)`; no client-side click or 10-second timer is required. The `spy_pick_seconds` config field is deprecated/retained for old payloads, with no runtime effect.

選間諜使用 `choose_spy(players, rng, history)`，`history` 只包含已完成回合的間諜次數；`settle_round` 會回傳下一版正確歷史。正式遊戲建議 `random.SystemRandom()`，固定 Seed 只用於測試。自動抽參考圖透過 `shuffle_gallery`、`random_pick_index`、`resolve_blind_pick`，不需要玩家點擊或另計 10 秒；`spy_pick_seconds` 僅為相容舊封包而保留，沒有實際作用。

The referee builds `SecretAnonymityMap` *after freezing the per-player drawing mapping* and must keep it private. For voting, accept a client's **public drawing label only**, resolve it via `decode_public_votes()`, and pass the authenticated connection's voter ID to `validate_votes(..., spy=spy)`. The client cannot supply/override its own internal player ID or alleged drawing author. Votes for self, marked civilian, unknown labels, or from the spy are invalid. First valid ballot per civilian per attempt only.

裁判在所有玩家作品定稿、內部畫作作者映射建立後，生成 `SecretAnonymityMap`，不得向客戶端公開。玩家投票只送**畫作公開編號**；裁判使用 `decode_public_votes()` 翻譯後，將已認證的連線身分交給 `validate_votes(..., spy=spy)`。客戶端不得任意指定自己的內部 ID 或畫作作者。投自己、已標記清白、未知編號及間諜的票都無效；每人每次開局只有第一張有效票。

Review uses `review_round(players=..., spy=..., drawing_authors=..., review_order=..., votes=..., ledger=..., rng=..., scores=..., threshold_ratio=..., removal_at=..., suspension_rounds=..., attempt_id=progress.current_attempt_id)`. Its `votes` are **internal drawing IDs**, after the referee translates public D# labels and authenticates civilian senders. The input represents the completed sequence of one positive violation button per 5-second picture; absent drawings imply NO. No review packets from the spy. Author voting on their own drawing is permitted. Review quotas are based on total players: 4/5 => 1 positive vote per civilian; 6/7 => 2. Fixed confirmation threshold is ceil(2/3 civilians), not reduced by reviewer suspensions.

`review_round` 使用參數 `players, spy, drawing_authors, review_order, votes, ledger, rng, scores, threshold_ratio, removal_at, suspension_rounds, attempt_id`。其中 `votes` 必須是裁判翻譯 D# 並驗證發送者後得到的**內部畫作 ID**，代表每張五秒審查時的唯一正面違規票；未投預設否。間諜不能審查，作者可以審查自己。四／五人每位一般玩家額度 1，六／七人額度 2。通過門檻固定為一般玩家的三分之二向上取整，不因審查權暫停而降低。

ReviewResult (`ReviewResolution`) is PRIVATE. `flagged_drawings` are withheld only from the spy **before guess**. The spy's selected reference should be checked immediately after moderation: if included in flagged set, call `settle_round(outcome=None)`, then skip voting/guess. `RoundSettlement.normal_delta` is all zero; add `total_delta` to scoreboard to apply moderation penalties. On normal attempts, construct a `RoundOutcome` and pass `outcome=...`; the settlement combines normal scores with discipline. It also increments completed rounds and spy history only when the attempt is scored.

`ReviewResolution` 屬裁判私有資料。`flagged_drawings` 只在間諜**猜詞前**暫時隱藏。審查完要立即檢查間諜抽到的參考圖；若被判違規，呼叫 `settle_round(outcome=None)`，跳過投票與猜詞。此時 `normal_delta` 全為零，但仍要把 `total_delta` 加入排行榜以保留違規處罰。正常回合則以 `RoundOutcome` 傳給 `settle_round`，它會加總正常分和處罰，只在完成回合時增加完成數與角色歷史。

The referee applies `settled.removed_players` **after** the attempt closes. Keep historical score logs if desired, but exclude removed players from the active roster and final competitive ranking. If players drop below four, end or return to lobby. Filter removed players out of private moderation state via `restrict_ledger(ledger, active_players)` and out of weighted spy history before the next attempt; if remaining players are still 4–7, rebuild new mappings for that roster.

裁判應在開局結算**後**才處理 `settled.removed_players`。可保留處罰紀錄供稽核，但被移出者不應繼續參與、也不列入最終競賽排名。剩不到四人則結束或返回大廳。若仍有 4–7 人，下一局前使用 `restrict_ledger` 清除不再參與者的私有審查狀態，間諜歷史也必須排除移出者並重新建立匿名對應。

## D. Security requirements / 安全要求

The `core` package is deliberately side-effect free but **does not authenticate packets**. A/Streaming must provide TLS/transport where appropriate, authenticated sender identity, `room_id`, `attempt_id`, `phase`, monotonic server deadlines, per-message unique IDs, size limits and a first-valid-write policy. Drop stale, late, replayed or cross-phase submissions. Referee receives raw drawings and stores safe snapshots. The UI cannot be trusted to hide data that the network has already delivered.

`core` 刻意保持無副作用，但**不會認證網路封包**。A/Streaming 須提供適當傳輸保護、已認證發送者、`room_id`、`attempt_id`、`phase`、以伺服器單調時間計算的截止期限、唯一事件 ID、封包大小上限及第一份有效提交規則。過期、重播或跨階段的訊息須拒絕。裁判保存畫作快照；UI 不能只靠畫面遮蔽已送到客戶端的機密資訊。

**Visibility:** Spy gets its hint and ONE civilian reference before its drawing. During review, only civilians get sequential drawings. During voting, civilians get the gallery plus a safe label; the spy does NOT get all images. If voting ends with spy caught/tie/no votes, give the spy only the approved NONFLAGGED images for guessing; after guess or skip, final reveal of ALL artwork is allowed. If the attempt is void, the referee may publicly announce the reason, but must avoid disclosing private role mapping before the finished match UI is ready.

**可見性：** 間諜作畫前只得提示與一張一般玩家參考圖。審查時只有一般玩家逐張取得畫作；投票時一般玩家看完整圖廊及清白標記，間諜**不會**收到完整畫廊。如果投票結束後間諜被抓／平票／無票，猜詞時只能取得非違規畫作；猜詞完成或免猜後，才可向所有人公開全部作品。作廢時可公告作廢原因，但不應不必要地提前洩漏秘密角色。

## E. Backward incompatible changes from 1.1.0 / 舊版介面差異

| Surface | v1.1 | v1.2 |
|---|---|---|
| `Phase` | `REVEAL` before voting | New `REVIEW`, `REVEAL` means final reveal / 審查階段新增、公開延後 |
| `choose_spy` | `choose_spy(players,rng)` | Optional `history` mapping enables weighted choice / 新增歷史參數 |
| reference selection | manual pick or timeout fallback | fully automatic via existing pure random functions / 改自動抽 |
| `ScoreRules` | `3,+2,-1,1,2` | `3,+1,-3,5,8` plus n-scaling, tie/discipline / 新分數、平票與處罰 |
| ballot | spy could vote | spy cannot cast an effective vote / 間諜沒有有效選票 |
| vote result | tie counted as escape | tie/no votes guess with 0 wrong / 平票／無票中性猜詞 |
| review | none | `review_round` with quotas, author penalties, reviewer suspensions / 新增審查 |
| void | none | `VOID_REFERENCE_VIOLATION`, no completed-round increment / 新增作廢 |
| `ranking()` | sort scores then IDs | same stable display; tied points share place / ID 排序僅供顯示 |

## F. Validation / 驗收

Run `python -m examples.rules_demo`, `python -m pytest -q`, and consult `QA_REPORT.md`. Integration over real Socket connections and reconnection are NOT TESTED by this deliverable.

執行示範與自動化測試，並參閱 `QA_REPORT.md`。本次交付不包含真實 Socket 連線及斷線重連的整合驗收。

The referee should pass `attempt_id=progress.current_attempt_id` into `review_round`; `settle_round` rejects reviews carrying an ID from a different attempt. The optional value `None` exists for legacy unit-test compatibility, not as a production recommendation.

裁判應在 `review_round` 傳入 `attempt_id=progress.current_attempt_id`；`settle_round` 會拒絕來自不同開局編號的審查結果。`None` 僅供舊單元測試相容，不建議正式程式省略。
