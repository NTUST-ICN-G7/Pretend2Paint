# Undercover Drawing Game / 誰是臥底畫圖版 — Part B Rules API v1.2.0

> Source basis / 規格基礎: Team's `README.pdf` (original API draft) + user-confirmed rule decisions through 2026-11-22. **Only Part B is implemented.**
>
> 來源：組員 `README.pdf` 原始 API 草案，以及截至 2026-11-22 確認的規則。**本套件只實作 Part B。**

## Scope / 範圍

This package is a network-independent Python 3.10+ game-rules library. It handles secret role assignment, weighted spy selection, automatic civilian-reference selection, anonymous player/drawing labels, sequential civilian-only review, repeated-violation consequences, civilian-only voting, tie-aware scoring, and *void* attempts with correct completed-round accounting. The UI, Socket protocol, reliable server-side timers, reconnection, and actual headless referee engine belong to other teammates.

本套件是 Python 3.10+、與網路獨立的遊戲規則函式庫。內容包含秘密分配角色、加權選間諜、自動選取一般玩家參考圖、獨立隨機玩家／畫作編號、依序審查、重複違規處置、只有一般玩家的有效投票、平票計分，以及作廢回合與有效回合數的正確區分。UI、Socket 通訊、伺服器倒數、重連及自動裁判流程引擎由其他組員負責。

## Source files / 檔案

```text
core/
  __init__.py     public imports / 對外匯入
  types.py        Phase, Role, RoundStatus, VoteStatus
  config.py       GameConfig, ScoreRules, phase seconds, JSON serialization
  words.py        WordCard, WordBank
  words.json      59 built-in questions / 59 題
  rules.py        spy selection, scoring, private deals, vote and guess checks
  anonymity.py    secret randomized player/drawing label mappings
  moderation.py   limited civilian review, penalties, reviewer suspensions
  rounds.py       attempt IDs, void decisions, completed-round accounting
docs/
  game-rules.md
  INTEGRATION.md
  OPEN_DECISIONS.md
  adr/0008-void-reference-review-and-anonymity.md
examples/
  rules_demo.py   full two-completed-round example with one void attempt
tests/
  test_*.py       automated regression + v1.2 acceptance tests
pyproject.toml
QA_REPORT.md
```

## Quick start / 快速開始

Run from the project directory; the demo has no network access and needs no extra packages. It performs three attempts: the first is void because the spy's reference drawing is confirmed in violation; the next two are successfully scored. Two completed rounds are counted, not three.

從專案根目錄執行；示範不使用網路、不需要第三方套件。它進行三次開局：第一次因間諜參考畫作違規而作廢，後兩次正常計分。最後只計入兩個有效回合，不是三個。

```bash
python -m examples.rules_demo
python -m pip install 'pytest>=7'
python -m pytest -q
```

Alternatively install the wheel locally with `python -m pip install undercover_drawing_game_rules-1.2.0-py3-none-any.whl`.

也可直接使用 `python -m pip install undercover_drawing_game_rules-1.2.0-py3-none-any.whl` 安裝 Wheel 套件。

## Confirmed rules in this release / 本版已實作的規則

| Area / 項目 | v1.2.0 behavior / 行為 |
|---|---|
| Referee / 裁判 | Separate automatic process, not a human player / 獨立程式、不佔真人名額 |
| Players / 人數 | 4–7 humans, all can play / 4–7 人全部參與 |
| Spy / 間諜 | Weighted random using completed role history only / 依已完成回合歷史加權隨機 |
| Word / 題目 | Civilians get answer, spy receives hint only / 一般玩家拿答案、間諜只拿提示 |
| Drawing / 畫圖 | 30s civilian drawings, then auto reference + 30s spy drawing / 30 秒一般玩家，接著自動選圖與 30 秒間諜作畫 |
| Timeout / 逾時 | Last accepted snapshots; missing drawing = blank; missing guess = wrong / 最後快照、缺畫＝白紙、缺猜詞＝猜錯 |
| Anonymity / 匿名 | Independent fresh P# and D# labels per attempt / 每次開局獨立重新洗牌 |
| Review / 審查 | 5s per randomly ordered drawing; civilians only, default no vote / 每張 5 秒、隨機順序、一般玩家、預設不同意 |
| Review button / 違規 | One button, 1 vote per civilian (4–5 players), 2 (6–7), never on spy / 單一違規鍵，按人數限額 |
| Review passed / 審查通過 | >= ceil(2/3 * civilian count); temporarily hidden from spy before guess / 達一般玩家三分之二門檻，猜詞前暫不公開給間諜 |
| Candidate / 投票資格 | **All drawings remain eligible** except the marked safe civilian / 違規作品也不失去候選資格；標記清白者除外 |
| Author / 作者 | First confirmed violation -15; second violation removed after settlement / 第一次 −15，第二次回合結算後移出 |
| Reviewer / 審查者 | 3 consecutive failed accusations -3; 4th -6 and next eligible review suspension / 連續失敗 3 次 −3；第 4 次再 −6，下一次審查暫停 |
| Reference violation / 參考圖違規 | **VOID** immediately after review; no normal scores, preserve penalties, retry without consuming a completed round / 回合作廢，保留違規處罰、補回有效回合 |
| Effective voters / 有效投票者 | Civilians only; vote for drawing labels, no self or marked author / 只有一般玩家有效投票，不投自己及標記清白者 |
| Voting result / 投票結果 | Unique spy top = caught; unique civilian top = escaped; tie/no votes = spy guessing / 間諜唯一最高票被抓；其他唯一最高票逃脫；平票或棄權猜詞 |
| Ranking / 排名 | Equal scores are equal rank; `ranking()` sorts IDs for stable display only / 同分並列，程式排序不作勝負判斷 |

## Provisional scoring table / 暫定計分表

These numbers are configurable, not empirically proven balanced. A correct civilian voter earns `5 + 3*(N-4)` points in a 4–7-player game; if the spy is uniquely caught and guesses wrong, add 3 more. Civilians who abstain or vote incorrectly earn zero. Spy cannot submit an effective vote.

本版分數可調整，尚未經實際玩家數據證明平衡。4–7 人遊戲，一般玩家投中間諜得 `5 + 3*(N-4)` 分；若間諜唯一最高票被抓且猜錯，再加 3 分。棄權或投錯不加分；間諜沒有有效投票權。

| Outcome / 結果 | Spy / 間諜 | Correct civilian / 投中間諜者 |
|---|---:|---:|
| Unique highest is a civilian / 唯一最高票為一般玩家 | +3 | base / 基礎分 |
| Spy uniquely caught, correct guess / 間諜被抓猜對 | +1 | base / 基礎分 |
| Spy uniquely caught, wrong or timeout / 間諜被抓猜錯或逾時 | -3 | base+3 / 基礎分再加三 |
| Tie / no votes, guess correct / 平票或全棄權，猜對 | +1 | base / 基礎分 |
| Tie / no votes, guess wrong or timeout / 平票或全棄權，猜錯 | 0 | base / 基礎分 |
| Spy reference confirmed violation / 間諜參考圖違規 | 0 normal points / 正常分為零 | 0 normal points / 正常分為零 |

## Primary public functions / 主要公開 API

```python
from core import (
    GameConfig,
    ScoreRules,
    WordBank,
    choose_spy,
    deal_words,
    complete_drawings,
    shuffle_gallery,
    random_pick_index,
    resolve_blind_pick,
    build_anonymity_map,
    decode_public_votes,
    ModerationLedger,
    review_threshold,
    review_vote_quota,
    review_round,
    restrict_ledger,
    valid_vote_targets,
    validate_votes,
    tally_votes,
    resolve_vote,
    is_correct_guess,
    RoundOutcome,
    score_round,
    RoundProgress,
    settle_round,
    RoundStatus,
    apply_scores,
    ranking,
    rank_with_ties,
    winners,
)
```

The complete, executable integration-style example is in `examples/rules_demo.py`; avoid copying only fragments of the demo into the flow engine. See `docs/INTEGRATION.md` for the contract and required server-side safeguards.

完整且可執行的整合風格範例請見 `examples/rules_demo.py`；流程組應參考 API 合約整合，而不是只複製局部程式。詳見 `docs/INTEGRATION.md`，其中包含伺服器端必要的安全驗證。

## Important limits / 重要限制

- **No Socket server, client, UI, network timer, retry transport or reconnection code is implemented by Part B.** / **Part B 不含 Socket 伺服器、客戶端、UI、真實計時器、傳輸重送或斷線重連程式。**
- Review reflects the players' voting consensus; it is **not** automated OCR, text classification or proof of intentional misconduct. / 審查反映玩家投票共識，**不是**自動 OCR、文字辨識或惡意意圖的證明。
- Automatic referee must not send `SecretAnonymityMap`, private roles, reference author, raw review votes, answer, or final rejected drawings to unauthorized clients. / 裁判不得提前傳送完整身分對應、秘密角色、參考作者、原始審查票、答案或尚不可公開的圖。
- Review suspension is deferred if enforcing it would make the fixed civilian review threshold unreachable. / 如果暫停審查權導致原本的門檻無法達成，則延期執行。
- Confirmed violations and reviewer failure penalties are preserved when a reference violation voids an attempt. / 參考圖違規導致回合作廢時，作者與審查者的處罰仍保留。
- The older v1.1 API contract changed in `Phase`, score defaults, spy ballot validation, tie semantics and review effects; Part A **must** adapt. / v1.1 的階段、分數預設、間諜投票、平票判定及審查流程已變動；A 模組**必須**同步更新。

## Documentation / 文件

Read `docs/game-rules.md`, `docs/INTEGRATION.md`, `docs/OPEN_DECISIONS.md`, `docs/adr/0008-void-reference-review-and-anonymity.md`, and `QA_REPORT.md` before connecting a network/UI layer.

在接入網路／UI 前，應閱讀上述規則、整合、待確認事項、決策紀錄與測試報告。
