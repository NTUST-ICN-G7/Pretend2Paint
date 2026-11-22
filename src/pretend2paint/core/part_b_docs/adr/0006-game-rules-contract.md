> **HISTORICAL / 歷史存檔:** This record reflects an older release. For the CURRENT v1.2 contract see `docs/adr/0008-void-reference-review-and-anonymity.md`, `docs/game-rules.md`, and `docs/INTEGRATION.md`.
> **歷史存檔：** 本文件是舊版決策，請以上述 v1.2 文件為準。

# ADR 0006 — Game Rules and Part B Integration Contract

**Status: Proposed / 尚待小組確認**

**Context (English)**

The drawing edition of Who Is Undercover needs independently testable rule functions so the networking and user-interface workstreams can integrate without circular dependencies. The authoritative team draft assigns role assignment, word deals, blind selections, voting, tie handling, guess matching, scoring, the question bank, and configuration to Part B. The updated gameplay sequence specifies private civilian drawings first, spy blind reference selection second, and gallery disclosure only after the spy's artwork is complete.

**背景（繁體中文）**

「誰是臥底畫圖版」需要可獨立驗證的規則函式，才能讓網路與使用者介面分工整合，避免循環依賴。組內 API 草稿指定 B 負責選間諜、發題、盲選、投票、平票、猜詞、計分、題庫與設定。更新後流程特別規定先由一般玩家私下畫圖，再讓間諜盲選參考，並在間諜完成畫作後才公開畫廊。

**Decision (English)**

- Part B is a Python standard-library package under `core/`, exporting its stable API from `core/__init__.py`.
- Part B defines `Phase`, `Role`, `PlayerId`, and `RuleError` centrally in `core/types.py`; Part A imports these shared contracts.
- The host chooses a new spy uniformly and independently every round. The host never participates as a player.
- Non-host active players number 4–7; the default game is five rounds.
- Voting excludes the voter and reference-marked civilian. The spy is caught only by a unique positive highest vote count; abstentions and tied top counts are escapes.
- Score defaults are +3/+2/−1 for the spy across the three result cases, plus +1 or +2 for civilians who voted for the spy.
- Random choices accept explicit `rng` arguments for deterministic tests. `WordBank.draw` changes only the caller-provided `used` set to track the no-repeat cycle.
- Part B never emits packets, logs secrets, starts timers, accesses UI, or imports Part A.

**決策（繁體中文）**

- B 採 Python 標準函式庫實作，對外介面集中於 `core/__init__.py`。
- B 在 `core/types.py` 統一宣告 `Phase`、`Role`、`PlayerId`、`RuleError`，由 A 直接匯入共用。
- 每回合獨立、均等隨機選出間諜，房主不參與遊戲。
- 非房主玩家為 4–7 人，預設五回合。
- 投票排除本人及被標記的一般玩家，只有間諜得到唯一最高且大於零的票數才被抓；棄權及最高票平票視為逃脫。
- 間諜在三種結果下預設為 +3/+2/−1 分，投中間諜的一般玩家依結果加 +1 或 +2 分。
- 所有亂數函式透過參數 `rng` 接收亂數來源，以支援固定 Seed 的測試；`WordBank.draw` 僅修改呼叫者提供的 `used` 集合以記錄不重複抽題週期。
- B 不送封包、不記錄機密、不開計時器、不操作 UI，也不匯入 A。

**Consequences (English)**

Part A is the sole authority for phase transitions, player authentication, disconnect handling, first-submission-wins behavior, packet routing, and gallery visibility. This decision does not claim that the complete network game is implemented. Items about zero eligible reference drawings and spy guess timeouts remain open for team confirmation.

**影響（繁體中文）**

A 是階段切換、玩家身分驗證、斷線處理、僅採用首次提交、封包路由與畫廊可見性控管的唯一權威。此決策不代表整個網路遊戲已實作完成。若沒有任何合格參考畫作，以及間諜猜詞逾時的處理方式，仍待組內確認。

**Supersedes:** None. Does not replace other members' ADR 0004 or ADR 0005.

**沒有取代其他成員**的 ADR 0004 或 ADR 0005。
