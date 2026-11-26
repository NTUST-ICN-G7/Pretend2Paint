# Core 共用設計文件 v5.2（A＋B）

> v5.2 變更（回應 B 對 #14 的審查）：ADR 改為 0008 並依賴 0007；`WordBank.draw` 加 `last_answer`；開房者斷線顯示最後快照；`ReviewPlan` 驗證補強；機密規則分三類；提交的原子性與事件順序。

> v5.1 變更（回應 B 的第二輪確認）：規則加上核准狀態、不可變性要求、`PlayerView.vote_state`、`ReviewPlan` 保存 players / spy、題庫使用紀錄不隨作廢回滾。

> v5 變更（回應 B 的 9 點審查）：新增「提交點」資料生命週期（第 11 節）、`ReviewPlan`、`review_round` 收 `ScoreRules`、開房者操作也走封包、`TimerId` 加 token、`match_id`、`round_no` 固定、被移出者不列排名、題庫載入移到 runtime、棄票定義。

> 放在 `src/pretend2paint/core/DESIGN.md`，取代之前的版本。
> A（鄒聿銘）流程、B（張瀚元）規則**都以這份為準**；要改規則或 API，先改這份、兩人都同意後再改程式。
> 狀態：草稿，待 A、B 確認　｜　日期：2026-11-22

---

## 0. 一句話

**開房者的電腦同時跑「自動遊戲伺服器」和「他自己的玩家程式」**；伺服器每局自動抽 1 位間諜，其餘都是一般玩家；所有真人（4～10 人）都參加遊戲。

---

## 1. 規則（核准狀態見本節末）

| # | 項目 | 規則 |
| :--- | :--- | :--- |
| 1 | 伺服器 | 開房者的裝置執行**自動遊戲伺服器**（權威，保管所有秘密）。開房者本人**也是玩家** |
| 2 | 人數 | **4～10 人**，全部參加。N＝本局參與人數（含間諜） |
| 3 | 角色 | 每局自動抽 **1 位間諜**（加權隨機 1/(1+s)²，s＝已完成回合中當過間諜的次數），其餘為一般玩家 |
| 4 | 名字 | 每人自己設暱稱；大廳、結算、公開時顯示暱稱；審查和投票時只顯示畫作編號 D1、D2… |
| 5 | 出題 | 一般玩家拿到答案，間諜只拿到提示（都是**單播**） |
| 6 | 畫圖 | 一般玩家同時各畫 30 秒。可按鈕交、可重複交（以最後一次為準），時間到自動上傳；伺服器多等 2 秒寬限；沒交＝白紙 |
| 7 | 間諜行動 | 伺服器**自動**隨機抽 1 張一般玩家的畫，私下給間諜參考；間諜畫 30 秒 |
| 8 | 審查 | 所有畫作（含間諜的）以隨機順序**逐張**給**一般玩家**看，每張 5 秒；可以檢舉「畫裡有可辨認的文字」；預設不檢舉。**間諜看不到、不能審查** |
| 9 | 審查額度與門檻 | 每位一般玩家每局最多檢舉 `ceil((N−3)/2)` 張（4～5 人：1、6～7 人：2、8～9 人：3、10 人：4）；同一張圖 ≥ `ceil(2(N−1)/3)` 票檢舉＝違規 |
| 10 | 違規處罰 | 作者第 1 次違規 −15；第 2 次違規在該局結算後**踢出**。檢舉者連續 3 次檢舉失敗 −3，第 4 次再 −6 並暫停下一次審查權（照 B v1.2） |
| 11 | 參考圖違規 | 間諜拿到的那張參考圖被判違規 → **本局作廢**（VOID）：跳過投票與猜詞、正常分 0、處罰照算、不算完成回合 |
| 12 | 投票 | 只有一般玩家能投（匿名投畫作編號）；不能投自己、不能投清白畫（被參考的那張）；看不到即時票數；只認第一張有效票。**棄票**：按「棄票」鍵＝送出棄票並鎖定（之後不能再投）；時間到沒投＝棄票。兩者計票結果相同 |
| 13 | 投票結果 | 間諜唯一最高票 → **被抓，要猜**；一般玩家唯一最高票 → **間諜逃脫**；**全部一般玩家都棄票 → 間諜逃脫**；有人投但平票 → **間諜要猜** |
| 14 | 猜詞 | 正規化（NFKC、去空白、小寫）後等於答案或別名才算對；逾時＝猜錯；間諜猜詞時只看得到**沒被判違規**的畫 |
| 15 | 公開 | 結果鎖定後，所有畫作（含違規的）、作者、答案、間諜公開給所有人 |
| 16 | 回合 | 完成 **5** 回合結束（作廢局不算）；demo 可設 2。顯示的回合編號在每局開始時固定（＝已完成回合＋1），作廢補局沿用同一個編號 |
| 17 | 斷線 | 以**結算提交點**為界（第 11 節）：**提交前**任一玩家斷線 → 本局作廢（VOID_DISCONNECT）：公布本局資訊、完全不計分（含本局審查處罰）、不算完成回合；**提交後**（REVEAL、ROUND_END）斷線 → 本局結果照算，下一局開始前移除該玩家。人數 < 4 → 遊戲結束。開房者（伺服器）斷線 → 遊戲結束。不重連；遊戲中不能加入 |
| 18 | 最終排名 | 只列遊戲結束時仍在場的玩家；被踢出或中途離開的人顯示在「已離開」清單（保留歷史分數），不參與名次與冠軍 |

### 核准狀態

| 狀態 | 規則編號 |
| :--- | :--- |
| ✅ 已核准 | 1（ADR 0007，組長授權放在 PR #5）、5、14 的基本部分（間諜被抓要猜詞） |
| ⏳ A/B 暫定，待組長核准 | 2、3（加權）、4、6（重複交與寬限）、7（自動參考圖）、8～11（審查、處罰、參考圖作廢）、12～13（匿名投票、棄票、平票）、15～18 |

**實作規則：** 已核准的直接做；暫定的可以先寫程式，但**數值與行為相關的測試等核准後才合併**（B 已同意此順序）。核准後把整列改成 ✅。

### 1.1 計分（N＝本局人數，base＝5＋3·(N−4)）⏳

| 結果 | 間諜 | 投中間諜的一般玩家 | 其他一般玩家 |
| :--- | :---: | :---: | :---: |
| 一般玩家唯一最高票（逃脫） | +3 | base | 0 |
| 一般玩家全部棄票（逃脫） | +3 | — | 0 |
| 間諜唯一最高票、猜對 | +1 | base | 0 |
| 間諜唯一最高票、猜錯 / 逾時 | −3 | base＋3 | 0 |
| 平票、猜對 | +1 | base | 0 |
| 平票、猜錯 / 逾時 | 0 | base | 0 |
| VOID_REFERENCE（參考圖違規） | 0 | 0 | 0（處罰照算） |
| VOID_DISCONNECT（有人斷線） | 0 | 0 | 0（處罰也不算） |

審查處罰另外加在正常分之後。同分同名次。**係數是暫定值**，試玩後調整（見第 10 節）。

---

## 2. 全系統架構

```text
┌──────────────── 開房者的電腦 ─────────────────┐      ┌──────── 其他玩家的電腦 ────────┐
│ ui（主執行緒）                                 │      │ ui（主執行緒）                   │
│   ↕ queue                                     │      │   ↕ queue                       │
│ runtime（背景 asyncio）                        │      │ runtime（背景 asyncio）          │
│   ├─ GameServer   ← 權威、秘密、計時            │      │   └─ PlayerEngine               │
│   └─ PlayerEngine ← 開房者自己的玩家狀態         │      │                                 │
│ streaming / p2p                                │◄────►│ streaming / p2p                 │
└────────────────────────────────────────────────┘ TCP  └─────────────────────────────────┘
```

- 分層：`ui | runtime → core → streaming → p2p → common`；core 不做 I/O。
- **開房者的 UI 只能看 `PlayerView`**，不能看伺服器的秘密。
- **開房者沒有特權捷徑。** 開房者的所有操作（包括 `StartGame`、`UpdateConfig`、交畫、檢舉、投票、猜詞）都由他的 `PlayerEngine` 產生 `Unicast(to=伺服器)`，runtime 在本機轉成 `PacketReceived(sender=開房者)` 交給 `GameServer`，**和遠端玩家走同一套驗證**。反方向（伺服器 → 開房者）也一樣在本機轉交。
- 開房者電腦收到的網路封包依**方向**分派：「P → S」類型交給 `GameServer`，「S → P」類型交給 `PlayerEngine`（第 7 節表格有方向欄）。
- 每場遊戲開始時伺服器產生隨機 `match_id`，**所有遊戲中封包都帶 `match_id` 和 `attempt_id`**，不符就丟掉，避免舊場次、舊局的封包被接受。

### 2.1 一局的階段

```text
LOBBY ─開始(4～10人)─► DEAL ─► DRAWING ─► SPY_ACTION ─► REVIEW ─┬─ 參考圖違規 ─────────────────────────► REVEAL(VOID_REFERENCE)
                                                                  └─► VOTING ─┬─ 逃脫（含全棄票）────► REVEAL
                                                                              └─ 被抓 / 平票 ─► SPY_GUESS ─► REVEAL
REVEAL ─► ROUND_END ─┬─ 完成 5 回合 或 人數 < 4 ─► 遊戲結束
                     └─ 否則 ─► DEAL（新 attempt）
提交點之前（DEAL～SPY_GUESS）有人斷線 ─► REVEAL(VOID_DISCONNECT) ─► ROUND_END
提交點之後（REVEAL、ROUND_END）有人斷線 ─► 本局照常結束，下一局前移除該玩家（第 11 節）
```

`common/types.py` 的 `Phase` 需更新為：`LOBBY、DEAL、DRAWING、SPY_ACTION、REVIEW、VOTING、SPY_GUESS、REVEAL、ROUND_END`（小寫值，由 team leader 修改）。

### 2.2 預設秒數（`GameConfig.phase_seconds`，可改）

| DEAL | DRAWING | SPY_ACTION | REVIEW | VOTING | SPY_GUESS | REVEAL | ROUND_END |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 5 | 30 | 30 | **每張 5** | 30 | 30 | 10 | 10 |

DRAWING、SPY_ACTION 另加 `submit_grace_seconds = 2`。

**寬限的意思是「容許網路延遲」，不是「多給玩家 2 秒畫」：**
- 玩家端倒數到 0 → UI 鎖住畫布、自動送出最後一份 `SubmitDrawing`，之後不再送。
- 伺服器只設**一個**計時器：`秒數＋寬限`，到期時定稿；這段期間抵達的快照都接受（以最後抵達的為準）。
- 寬限結束後才到的快照一律丟掉。

### 2.3 誰在什麼時候看得到什麼（機密規則）

| 階段 | 一般玩家 | 間諜 | 走法 |
| :--- | :--- | :--- | :--- |
| DEAL | 答案 | 提示 | 單播 |
| DRAWING | 只有自己的畫 | 等待畫面 | — |
| SPY_ACTION | 等待畫面 | 1 張參考圖（不知道作者） | 單播給間諜 |
| REVIEW | 逐張看所有畫（D# 編號，無作者） | 等待畫面 | 逐一單播給一般玩家 |
| VOTING | 全部畫（D# 編號）＋清白標記；看不到票數 | 等待畫面 | 逐一單播給一般玩家 |
| SPY_GUESS | 等待畫面 | 沒被判違規的畫 | 單播給間諜 |
| REVEAL | 全部公開：作者、間諜、答案、違規、票數 | 同左 | 廣播 |

機密規則分三類（ADR 0008，部分取代 ADR 0005）：

1. **提交前，只能單播給本人**：答案、提示、角色。作者對應、別人的角色、選票、檢舉只存在伺服器。
2. **提交前的畫作例外（限定接收者、不含作者、不可廣播）**：`SPY_REFERENCE`→間諜；`REVIEW_ITEM`、`GALLERY`→逐一單播給一般玩家；`SPY_GALLERY`→間諜。
3. **提交後的公開例外**：結算提交完成後才可廣播 `REVEAL_ALL`（答案、提示、間諜、作者、違規、得票數）。

---

## 3. 檔案架構

```text
src/pretend2paint/
├── common/types.py           # leader：PlayerId、Phase、Role、Stroke、Drawing、BLANK_DRAWING
├── runtime/                  # A（需 leader 同意）：執行 Effect、計時、分派封包
└── core/
    ├── __init__.py           # 重新匯出 flow 和 rules 的公開 API
    ├── README.md             # module-api-doc 格式
    ├── DESIGN.md             # 本文件
    ├── flow/                 # ── A：流程 ──
    │   ├── events.py         # 輸入事件
    │   ├── effects.py        # 輸出動作
    │   ├── views.py          # PlayerView
    │   ├── timers.py         # TimerId
    │   ├── packets.py        # 封包方向、payload 組裝與解析
    │   ├── server.py         # GameServer（權威狀態機）
    │   ├── _server_state.py  # 伺服器私有資料
    │   └── player.py         # PlayerEngine
    └── rules/                # ── B：規則（全部純函式）──
        ├── errors.py         # RuleError
        ├── config.py         # GameConfig、ScoreRules、default_phase_seconds
        ├── progress.py       # RoundProgress
        ├── words.py          # WordCard、WordBank（只驗證與抽題，不讀檔）
        ├── words.json        # 題庫資料（59 題），由 runtime 讀取後交給 WordBank
        ├── roles.py          # choose_spy、deal_words、Deal
        ├── drawings.py       # complete_drawings、pick_reference
        ├── anonymity.py      # SecretAnonymityMap、build_anonymity_map
        ├── review.py         # ModerationLedger、ReviewPlan、plan_review、review_round、restrict_ledger
        ├── voting.py         # valid_vote_targets、validate_votes、tally_votes、resolve_vote、VoteOutcome、VoteStatus
        ├── guessing.py       # normalize_guess、is_correct_guess
        └── scoring.py        # RoundOutcome、RoundStatus、RoundSettlement、settle_round、settle_void_disconnect、apply_scores、ranking、rank_with_ties、winners

tests/core/
├── flow/   # A 的測試
├── rules/  # B 的測試（B 的 145 個測試搬過來）
└── test_full_game.py   # A＋B：假網路跑完整場（4、7、10 人）
```

**依賴規則：** `flow` 可以 import `rules`；`rules` 絕不 import `flow`。兩邊都只用 `common.types` 的 `PlayerId`、`Phase`、`Role`、`Drawing`。

---

## 4. B 的 API（rules）

以 B v1.2.0 的程式為基礎。標 **【改】** 的是 B 需要調整的地方，標 **【新】** 的是要新增的。

### 4.1 設定與進度

```python
class RuleError(ValueError): ...


@dataclass(frozen=True)
class ScoreRules:
    spy_escape: int = 3
    spy_caught_right: int = 1
    spy_caught_wrong: int = -3
    spy_tie_right: int = 1
    spy_tie_wrong: int = 0
    civilian_hit: int = 5  # base 的起始值
    civilian_hit_spy_lost_bonus: int = 3
    civilian_hit_per_extra_player: int = 3
    author_violation_penalty: int = -15
    reviewer_fail_penalty_3: int = -3
    reviewer_fail_penalty_4: int = -6


def default_phase_seconds() -> dict[Phase, float]: ...  # 【改】照第 2.2 節；REVIEW 是「每張」秒數


@dataclass(frozen=True)
class GameConfig:
    rounds: int = 5
    min_players: int = 4
    max_players: int = 10  # 【改】7 → 10
    phase_seconds: Mapping[Phase, float] = field(default_factory=default_phase_seconds)
    submit_grace_seconds: float = 2.0  # 【新】
    spy_weight_exponent: float = 2.0
    score: ScoreRules = ScoreRules()
    # 【改】刪除 spy_pick_seconds

    def validate(self) -> list[str]: ...
    def to_payload(self) -> dict[str, Any]: ...
    @classmethod
    def from_payload(cls, data: Mapping[str, Any]) -> "GameConfig": ...


@dataclass(frozen=True)
class RoundProgress:  # 不可變：每個操作回傳新物件
    target_rounds: int
    attempts_started: int = 0
    attempts_settled: int = 0
    completed_rounds: int = 0

    @property
    def current_attempt_id(self) -> int: ...
    @property
    def finished(self) -> bool: ...  # completed_rounds >= target_rounds
    def begin_attempt(self) -> "RoundProgress": ...  # 已完成目標再呼叫 → RuleError
```

### 4.2 題目與角色

```python
@dataclass(frozen=True)
class WordCard:
    answer: str
    hint: str
    aliases: tuple[str, ...] = ()


class WordBank:
    cards: tuple[WordCard, ...]

    def __init__(self, cards: Sequence[WordCard]) -> None: ...
    @classmethod
    def from_records(cls, records: Sequence[Mapping[str, Any]]) -> "WordBank":
        ...
        # 【改】取代 from_json / default：core 不讀檔，runtime 用 importlib.resources 讀 words.json 後傳進來

    def draw(
        self, rng: random.Random, used: set[str], *, last_answer: str | None = None
    ) -> WordCard:
        ...
        # B 已實作。題庫用完重置時排除 last_answer，避免跨週期連續重複（單題題庫無法避免）
        # A 保存上一次「已發出」的答案，下次抽題傳入；作廢局不回滾


def choose_spy(
    players: Sequence[PlayerId],
    rng: random.Random,
    history: Mapping[PlayerId, int],
    exponent: float = 2.0,
) -> PlayerId:
    ...
    # 【改】history 改為必填，只留加權這一種


@dataclass(frozen=True)
class Deal:
    role: Role
    text: str


def deal_words(
    players: Sequence[PlayerId], spy: PlayerId, card: WordCard
) -> dict[PlayerId, Deal]: ...
```

### 4.3 畫作與參考圖

```python
type DrawingId = str  # 伺服器內部編號，例："a3-p7"（attempt 3、玩家 p7）


def complete_drawings(
    authors: Sequence[PlayerId], submitted: Mapping[PlayerId, Drawing]
) -> dict[PlayerId, Drawing]:
    ...
    # 【改】沒交的補 common.types.BLANK_DRAWING，不再需要 blank_factory


def pick_reference(civilians: Sequence[PlayerId], rng: random.Random) -> PlayerId:
    ...
    # 【新】包住 shuffle_gallery + random_pick_index + resolve_blind_pick（這三個改為私有）
```

### 4.4 匿名

```python
@dataclass(frozen=True)
class PublicDrawing:
    label: str  # "D3"
    safe: bool  # 清白標記（被參考的那張）


@dataclass(frozen=True)
class SecretAnonymityMap:  # 只存在伺服器，不可序列化給玩家
    drawing_labels: Mapping[DrawingId, str]

    def label_of(self, drawing_id: DrawingId) -> str: ...
    def drawing_of(self, label: str) -> DrawingId: ...  # 【新】未知編號 → RuleError
    def public_gallery(
        self, safe_drawing: DrawingId | None = None
    ) -> tuple[PublicDrawing, ...]: ...
    def public_review_order(self, rng: random.Random) -> tuple[str, ...]: ...


def build_anonymity_map(
    drawing_authors: Mapping[DrawingId, PlayerId], rng: random.Random
) -> SecretAnonymityMap:
    ...
    # 【改】拿掉 P# 玩家編號（大家用暱稱，沒用到）
```

### 4.5 審查

```python
def review_vote_quota(n_players: int) -> int: ...  # 【改】ceil((N−3)/2)，支援到 10 人
def review_threshold(n_players: int) -> int: ...  # ceil(2(N−1)/3)


@dataclass(frozen=True)
class AuthorRecord:
    confirmed_violations: int = 0


@dataclass(frozen=True)
class ReviewerRecord:
    failure_streak: int = 0
    pending_suspensions: int = 0


@dataclass(frozen=True)
class ModerationLedger:
    authors: Mapping[PlayerId, AuthorRecord] = field(default_factory=dict)
    reviewers: Mapping[PlayerId, ReviewerRecord] = field(default_factory=dict)


@dataclass(frozen=True)
class ReviewPlan:  # 【新】REVIEW 開始時算一次，A 發畫面、B 驗證都用同一份；伺服器私有
    attempt_id: int
    players: tuple[PlayerId, ...]  # 本局全部參與者（含間諜）
    spy: PlayerId
    order: tuple[DrawingId, ...]  # 播放順序
    eligible: frozenset[PlayerId]  # 這局可以檢舉的一般玩家
    suspended: frozenset[PlayerId]  # 這局被暫停的一般玩家（看得到圖、不能檢舉）
    quota: int  # 每人可檢舉張數
    threshold: int  # 判定違規所需票數


def plan_review(
    *,
    players: Sequence[PlayerId],
    spy: PlayerId,
    drawing_authors: Mapping[DrawingId, PlayerId],
    amap: SecretAnonymityMap,
    ledger: ModerationLedger,
    rng: random.Random,
    attempt_id: int,
) -> ReviewPlan:
    ...
    # 【新】原本 review_round 內部「隨機決定執行哪些暫停」移到這裡，只做一次
    # 取代 v4 的 eligible_reviewers


@dataclass(frozen=True)
class ReviewResolution:  # 伺服器私有
    attempt_id: int
    flagged_drawings: frozenset[DrawingId]
    penalty_delta: Mapping[PlayerId, int]
    removed_players: frozenset[PlayerId]
    ledger: ModerationLedger  # 「待提交」的 ledger，結算提交後才生效（第 11 節）

    def may_show_to_spy_before_guess(self, drawing_id: DrawingId) -> bool: ...


def review_round(
    *,
    plan: ReviewPlan,
    drawing_authors: Mapping[DrawingId, PlayerId],
    votes: Mapping[PlayerId, Sequence[DrawingId]],
    ledger: ModerationLedger,
    scores: ScoreRules,
) -> ReviewResolution:
    ...
    # 【改】改收 plan 和 scores（扣分用 scores 裡的係數）；不再收 rng
    # votes：只能來自 plan.eligible，每人 ≤ plan.quota（A 收的時候先擋，B 再驗一次）
    # B 驗證一致性：eligible ∪ suspended ＝ players − {spy}、兩者不重疊；
    #               drawing_authors 的鍵 ＝ set(plan.order)、作者 ⊆ players；不符丟 RuleError
    #               plan.attempt_id 與目前這局一致；order 沒有重複；每位玩家恰好對應一張畫


def restrict_ledger(ledger: ModerationLedger, active: Collection[PlayerId]) -> ModerationLedger: ...
```

### 4.6 投票與猜詞

```python
def valid_vote_targets(
    players: Sequence[PlayerId], voter: PlayerId, safe_author: PlayerId
) -> frozenset[PlayerId]: ...


def validate_votes(
    votes: Mapping[PlayerId, PlayerId],
    players: Sequence[PlayerId],
    safe_author: PlayerId,
    *,
    spy: PlayerId,
) -> None:
    ...
    # 不合法丟 RuleError：投自己、投清白、未知玩家、間諜投票


def tally_votes(votes: Mapping[PlayerId, PlayerId]) -> Counter[PlayerId]: ...


class VoteStatus(StrEnum):
    SPY_ESCAPED = "spy_escaped"  # 一般玩家唯一最高，或【改】全部棄票
    SPY_CAUGHT = "spy_caught"  # 間諜唯一最高
    TIE = "tie"  # 有人投但最高票平手


@dataclass(frozen=True)
class VoteOutcome:
    top: tuple[PlayerId, ...]
    status: VoteStatus  # 【改】直接放結果，不用再呼叫 .status(spy)
    all_abstained: bool  # 【新】


def resolve_vote(tally: Counter[PlayerId], spy: PlayerId) -> VoteOutcome: ...
def guess_required(outcome: VoteOutcome) -> bool: ...  # 【新】SPY_CAUGHT 或 TIE


def normalize_guess(text: str) -> str: ...
def is_correct_guess(guess: str | None, card: WordCard) -> bool: ...  # None / 空白 → False
```

### 4.7 結算

```python
class RoundStatus(StrEnum):
    SCORED = "scored"
    VOID_REFERENCE = "void_reference"  # 【改】原 VOID_REFERENCE_VIOLATION
    VOID_DISCONNECT = "void_disconnect"  # 【新】


@dataclass(frozen=True)
class RoundOutcome:
    players: tuple[PlayerId, ...]
    spy: PlayerId
    votes: Mapping[PlayerId, PlayerId]  # 已驗證：投票人 → 被投的作者
    vote: VoteOutcome
    guess_correct: bool | None  # 不用猜時為 None
    safe_author: PlayerId


@dataclass(frozen=True)
class RoundSettlement:
    status: RoundStatus
    normal_delta: Mapping[PlayerId, int]
    disciplinary_delta: Mapping[PlayerId, int]
    total_delta: Mapping[PlayerId, int]  # 加到計分板的就是這個
    progress: RoundProgress
    spy_history: Mapping[PlayerId, int]
    ledger: ModerationLedger
    removed_players: frozenset[PlayerId]


def settle_round(
    *,
    progress: RoundProgress,
    review: ReviewResolution,
    reference_drawing: DrawingId,
    drawing_authors: Mapping[DrawingId, PlayerId],
    players: Sequence[PlayerId],
    spy: PlayerId,
    spy_history: Mapping[PlayerId, int],
    rules: ScoreRules,
    outcome: RoundOutcome | None = None,
) -> RoundSettlement:
    ...
    # outcome=None 只用在參考圖違規；其餘情況必須給 outcome


def settle_void_disconnect(
    *,
    progress: RoundProgress,
    players: Sequence[PlayerId],
    spy_history: Mapping[PlayerId, int],
    ledger: ModerationLedger,
) -> RoundSettlement:
    ...
    # 【新】全部 0 分、不算完成回合、不改間諜歷史
    # ledger 傳「上一次提交的」ledger（不是 review_round 剛算出來的），所以本局審查處罰自動作廢
    # 不需要知道誰斷線：移除玩家是 A 的事（A 收到 PeerLeft 就從名單拿掉）


def apply_scores(
    board: Mapping[PlayerId, int], delta: Mapping[PlayerId, int]
) -> dict[PlayerId, int]: ...
def rank_with_ties(
    board: Mapping[PlayerId, int],
) -> list[tuple[PlayerId, int, int]]: ...  # (玩家, 分數, 名次)
def winners(board: Mapping[PlayerId, int]) -> tuple[PlayerId, ...]: ...


# 【改】score_round 改為私有（_score_round），A 只呼叫 settle_round
```

### 4.8 不可變性（A、B 共同遵守）

- 所有回傳的 dataclass 都是 `frozen=True`；內部的 `Mapping` 用 `types.MappingProxyType` 包起來，或至少回傳**新的** dict，不可共用呼叫者傳進來的物件。
- B 的函式**絕不原地修改**傳入的 `board`、`ledger`、`history`、`progress`、`used` 以外的參數（`WordBank.draw` 的 `used` 是唯一例外，見第 11 節）。
- B 要有測試：呼叫 `review_round`、`settle_round`、`settle_void_disconnect` 前後，committed 的物件內容完全不變；作廢後不殘留處罰或歷史變更。

### 4.9 B 不提供的

計時、網路、驗證封包發送者、決定送給誰、畫面。這些都是 A（或 runtime / streaming）的事。

---

## 5. 標準呼叫順序（A 照這個寫，B 照這個測）

```python
rng = random.SystemRandom()  # 測試用 random.Random(seed)
bank = WordBank.from_records(records)  # records 由 runtime 讀 words.json 而來
config = GameConfig()
progress = RoundProgress(target_rounds=config.rounds)
history: dict[PlayerId, int] = {}
ledger = ModerationLedger()
board = {p: 0 for p in players}
used: set[str] = set()
last_answer: str | None = None

while not progress.finished and len(players) >= config.min_players:
    # DEAL
    progress = progress.begin_attempt()
    attempt = progress.current_attempt_id
    card = bank.draw(rng, used, last_answer=last_answer)
    last_answer = card.answer  # 發出即記錄，作廢不回滾
    spy = choose_spy(players, rng, history, config.spy_weight_exponent)
    deals = deal_words(players, spy, card)  # 逐一單播
    civilians = [p for p in players if p != spy]

    # DRAWING（收 CANVAS_SNAPSHOT，保留最新）→ 時間到＋寬限
    civ_drawings = complete_drawings(civilians, submitted_civilians)

    # SPY_ACTION
    safe_author = pick_reference(civilians, rng)  # 單播參考圖給間諜
    spy_drawing = complete_drawings([spy], submitted_spy)[spy]

    # REVIEW
    drawings = {**civ_drawings, spy: spy_drawing}
    drawing_authors = {f"a{attempt}-{p}": p for p in drawings}
    reference = f"a{attempt}-{safe_author}"
    amap = build_anonymity_map(drawing_authors, rng)
    plan = plan_review(
        players=players,
        spy=spy,
        drawing_authors=drawing_authors,
        amap=amap,
        ledger=ledger,
        rng=rng,
        attempt_id=attempt,
    )
    # 依 plan.order 每張 5 秒，單播給所有一般玩家；plan.suspended 的人檢舉鍵反灰
    review_votes = {...}  # 只收 plan.eligible；D# → amap.drawing_of(label)
    review = review_round(
        plan=plan,
        drawing_authors=drawing_authors,
        votes=review_votes,
        ledger=ledger,
        scores=config.score,
    )
    # review.ledger 是「待提交」，還沒取代 ledger

    if reference in review.flagged_drawings:  # 參考圖違規 → VOID
        settled = settle_round(
            progress=progress,
            review=review,
            reference_drawing=reference,
            drawing_authors=drawing_authors,
            players=players,
            spy=spy,
            spy_history=history,
            rules=config.score,
        )
    else:
        # VOTING：單播 amap.public_gallery(reference) 給一般玩家；收 D# 票
        votes = {}  # 每人第一張有效票
        #   target = drawing_authors[amap.drawing_of(label)]
        #   validate_votes({voter: target}, players, safe_author, spy=spy) 通過才收
        vote = resolve_vote(tally_votes(votes), spy)

        guess_correct = None
        if guess_required(vote):  # SPY_GUESS
            # 只給間諜 review.may_show_to_spy_before_guess(d) 為 True 的畫
            guess_correct = is_correct_guess(spy_guess_or_none, card)

        outcome = RoundOutcome(tuple(players), spy, votes, vote, guess_correct, safe_author)
        settled = settle_round(
            progress=progress,
            review=review,
            reference_drawing=reference,
            drawing_authors=drawing_authors,
            players=players,
            spy=spy,
            spy_history=history,
            rules=config.score,
            outcome=outcome,
        )

    # ── 提交點：settle_round 成功後才一次更新下面所有狀態（第 11 節）──
    # REVEAL → ROUND_END
    board = apply_scores(board, settled.total_delta)
    progress, history, ledger = settled.progress, dict(settled.spy_history), settled.ledger
    players = [p for p in players if p not in settled.removed_players]
    ledger = restrict_ledger(ledger, players)
    history = {p: n for p, n in history.items() if p in players}

# 提交點之前有人斷線：
#   settled = settle_void_disconnect(progress=progress, players=players,
#                                    spy_history=history, ledger=ledger)   # ledger＝上次提交的
#   公布本局資訊 → A 從名單移除該玩家 → 人數 < 4 就結束
# 提交點之後有人斷線：本局照常 REVEAL / ROUND_END，下一局 DEAL 前移除

active_board = {p: s for p, s in board.items() if p in players}
final = rank_with_ties(active_board)  # 已離開 / 被踢出的人另外列出，不排名
```

---

## 6. A 的 API（flow）

### 6.1 事件 `events.py`

```python
type Event = (
    PeerJoined
    | PeerLeft
    | PacketReceived
    | TimerFired
    | JoinRoom
    | UpdateConfig
    | StartGame
    | SubmitDrawing
    | FlagDrawing
    | CastVote
    | GuessWord
)


@dataclass(frozen=True)
class PeerJoined:
    player: PlayerId


@dataclass(frozen=True)
class PeerLeft:
    player: PlayerId


@dataclass(frozen=True)
class PacketReceived:
    sender: PlayerId
    packet_type: PacketType
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class TimerFired:
    timer: TimerId


# UI → PlayerEngine
@dataclass(frozen=True)
class JoinRoom:
    nickname: str


@dataclass(frozen=True)
class UpdateConfig:
    config: GameConfig  # 只有開房者


@dataclass(frozen=True)
class StartGame:
    pass  # 只有開房者


@dataclass(frozen=True)
class SubmitDrawing:
    drawing: Drawing  # 可重複；倒數到 0 由 UI 自動送


@dataclass(frozen=True)
class FlagDrawing:
    label: str  # 審查時檢舉目前這張


@dataclass(frozen=True)
class CastVote:
    label: str | None  # None＝主動棄票並鎖定；不送＝時間到算棄票


@dataclass(frozen=True)
class GuessWord:
    text: str
```

所有 UI 操作（含開房者的 `UpdateConfig`、`StartGame`）都由 `PlayerEngine` 轉成送往伺服器的封包；伺服器檢查 `sender == owner` 才接受開始與改設定。

### 6.2 動作 `effects.py`、計時 `timers.py`

```python
type Effect = Unicast | Broadcast | StartTimer | CancelTimer | ViewChanged | GameOver


@dataclass(frozen=True)
class Unicast:
    to: PlayerId
    packet_type: PacketType
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class Broadcast:
    packet_type: PacketType
    payload: Mapping[str, Any]  # 不可含機密


@dataclass(frozen=True)
class StartTimer:
    timer: TimerId
    seconds: float


@dataclass(frozen=True)
class CancelTimer:
    timer: TimerId


@dataclass(frozen=True)
class ViewChanged:
    view: PlayerView  # 只由 PlayerEngine 產生


@dataclass(frozen=True)
class GameOver:
    reason: GameOverReason  # FINISHED / HOST_LEFT / NOT_ENOUGH_PLAYERS


class TimerKind(StrEnum):
    PHASE_END = "phase_end"  # 一般階段結束（DEAL、VOTING、SPY_GUESS、REVEAL、ROUND_END）
    SUBMIT_CLOSE = "submit_close"  # DRAWING / SPY_ACTION：秒數＋寬限到期、定稿
    REVIEW_ITEM = "review_item"  # REVIEW：第 step 張播完


@dataclass(frozen=True)
class TimerId:
    token: int  # 伺服器每開一個計時器就 +1，全場唯一
    attempt_id: int
    phase: Phase
    kind: TimerKind
    step: int = 0  # REVIEW 第幾張；其他為 0
```

伺服器同一時間只有**一個**有效計時器（`active_timer`）。`TimerFired` 的 `timer != active_timer` 一律忽略；換階段時先 `CancelTimer` 舊的。

### 6.3 兩個引擎

```python
class GameServer:
    """自動遊戲伺服器。只在開房者那台建立，保存所有秘密。"""

    def __init__(
        self, owner_id: PlayerId, config: GameConfig, words: WordBank, rng: random.Random
    ) -> None: ...
    def handle(self, event: Event) -> list[Effect]: ...
    def debug_snapshot(self) -> dict[str, Any]: ...  # 只給測試 / log，不可送出


class PlayerEngine:
    """每位玩家（含開房者）的狀態，只知道自己該知道的。"""

    def __init__(
        self, my_id: PlayerId, server_id: PlayerId, nickname: str, is_owner: bool
    ) -> None: ...
    def handle(self, event: Event) -> list[Effect]: ...
    def view(self) -> PlayerView: ...
```

### 6.4 給 UI 的狀態 `views.py`

```python
@dataclass(frozen=True)
class PlayerView:
    phase: Phase
    attempt_id: int | None
    round_no: int  # 伺服器在 DEAL 時固定送來，最多 = total_rounds；作廢補局不變
    total_rounds: int
    seconds_left: float | None
    players: tuple[PlayerInfo, ...]  # id、暱稱、在線、分數
    is_owner: bool
    can_start: bool  # 開房者 + 人數 4～10
    config: GameConfig | None

    my_role: Role | None
    my_text: str | None  # 答案或提示
    waiting: bool  # 這階段我沒事做（顯示等待畫面）

    my_submitted: bool  # DRAWING / SPY_ACTION：已交過
    reference: Drawing | None  # 間諜：參考圖

    review_item: ReviewItem | None  # REVIEW：目前這張（label、drawing、第幾張、共幾張）
    flags_left: int  # REVIEW：剩幾次檢舉
    can_flag: bool  # REVIEW：被暫停時為 False（看得到圖、檢舉鍵反灰）
    my_flags: frozenset[str]

    gallery: tuple[GalleryItem, ...]  # VOTING（一般玩家）/ SPY_GUESS（間諜）
    safe_label: str | None
    vote_options: frozenset[str]
    vote_state: VoteState  # OPEN＝可投；VOTED＝已投（看 my_vote）；ABSTAINED＝主動棄票；
    # NOT_ELIGIBLE＝間諜或非投票階段。只有 OPEN 時投票鍵可按
    my_vote: str | None
    must_guess: bool

    reveal: RevealInfo | None  # REVEAL：每張畫的作者、間諜、答案、違規、票數
    last_round: RoundSummary | None  # ROUND_END：狀態、各人加減分、被踢出的人
    game_over: GameOverReason | None
    ranking: tuple[tuple[PlayerId, int, int], ...]  # 只含在場玩家
    snapshot_round: int | None  # 分數快照截至第幾回合；開房者斷線時顯示，None＝尚無分數
    departed: tuple[tuple[PlayerId, int, str], ...]  # 已離開 / 被踢出：(玩家, 分數, 原因)
```

```python
class VoteState(StrEnum):
    NOT_ELIGIBLE = "not_eligible"
    OPEN = "open"
    VOTED = "voted"
    ABSTAINED = "abstained"
```

`ReviewItem`、`GalleryItem`、`RevealInfo`、`RoundSummary`、`PlayerInfo` 都是 frozen dataclass，欄位見程式。

### 6.5 GameServer 必擋的封包（只記 log、丟掉）

- 送的人不在本局名單；遊戲中想加入。
- `attempt_id` 不是目前這局；階段不對；寬限後才到的畫。
- 身分不對：間諜在 DRAWING 交畫、一般玩家在 SPY_ACTION 交畫、間諜審查或投票、一般玩家猜詞、被暫停的人檢舉。
- 檢舉超過額度、同一張檢舉兩次、檢舉的不是目前這張。
- 第二張票（只認第一張有效票）。
- 未知的 D# 編號；payload 格式錯。

---

## 7. 封包清單（Streaming 照這份更新 protocol.md）

方向：**S**＝伺服器（開房者那台的 GameServer）、**P**＝玩家（PlayerEngine，含開房者自己）。
遊戲開始後的所有封包都帶 `match_id` 和 `attempt_id`（下表省略不寫）；不符一律丟掉。`role` 一律用 `common.types.Role` 的小寫值（`"civilian"`、`"spy"`）。

| 名稱 | 方向 | 傳送 | Payload |
| :--- | :--- | :--- | :--- |
| `JOIN_ROOM` | P → S | 單播 | `{nickname}` |
| `UPDATE_CONFIG` | P（開房者）→ S | 單播 | `{config}` |
| `START_GAME` | P（開房者）→ S | 單播 | `{}` |
| `ROOM_STATE` | S → P | 廣播 | `{owner, accepting, players:[{id, nickname}], config}` |
| `ROUND_STATE_SYNC` | S → P | 廣播 | `{match_id, attempt_id, phase, round_no, total_rounds, seconds_left}` |
| `DEAL_WORD` | S → P | **單播** | `{attempt_id, role, text}` |
| `CANVAS_SNAPSHOT` | P → S | 單播 | `{attempt_id, drawing}`（可重複） |
| `SPY_REFERENCE` | S → P（間諜） | **單播** | `{attempt_id, drawing}` |
| `REVIEW_ITEM` | S → P（審查者） | **單播** | `{attempt_id, label, drawing, index, total, flags_left}` |
| `REVIEW_FLAG` | P → S | 單播 | `{attempt_id, label}` |
| `GALLERY` | S → P（一般玩家） | **單播** | `{attempt_id, items:[{label, drawing}], safe_label, options}` |
| `VOTE` | P → S | 單播 | `{attempt_id, label}`（`label: null`＝主動棄票） |
| `VOTE_RESULT` | S → P | 廣播 | `{attempt_id, status}` |
| `SPY_GALLERY` | S → P（間諜） | **單播** | `{attempt_id, items:[{label, drawing}]}` |
| `SPY_GUESS` | P → S | 單播 | `{attempt_id, text}` |
| `REVEAL_ALL` | S → P | 廣播 | `{attempt_id, status, spy, answer, hint, items:[{label, author, drawing, flagged, is_reference}], votes:{label: n}}` |
| `ROUND_RESULT` | S → P | 廣播 | `{attempt_id, status, normal_delta, disciplinary_delta, total_delta, scores, removed, completed_rounds}` |
| `GAME_OVER` | S → P | 廣播 | `{reason, ranking}` |

不再需要：`SPY_SELECT_REF`、`DRAW_STROKE`。

---

## 8. 共用型別（team leader 改 `common/types.py`）

```python
class Phase(StrEnum):
    LOBBY = "lobby"
    DEAL = "deal"
    DRAWING = "drawing"
    SPY_ACTION = "spy_action"
    REVIEW = "review"
    VOTING = "voting"
    SPY_GUESS = "spy_guess"
    REVEAL = "reveal"
    ROUND_END = "round_end"


@dataclass(frozen=True)
class Stroke:
    color: str  # "#RRGGBB"
    width: float  # 畫布寬的比例
    points: tuple[tuple[float, float], ...]  # 0～1 比例座標


@dataclass(frozen=True)
class Drawing:
    strokes: tuple[Stroke, ...] = ()


BLANK_DRAWING = Drawing()
```

---

## 9. 計畫

### 9.1 分工

| 誰 | 負責 |
| :--- | :--- |
| A 鄒聿銘 | `core/flow/`、`runtime/`、`tests/core/flow/`、`test_full_game.py`；`common` 修改提案 |
| B 張瀚元 | `core/rules/`、`tests/core/rules/`；依第 4 節【改】【新】調整；`RULES_DESIGN.md`（差異表） |
| team leader | `common/types.py`、`pyproject.toml`（runtime 分層）、ADR 更新（0003 改為「開房者裝置跑自動伺服器、所有人都玩」） |
| Streaming | 第 7 節封包、`protocol.md` |
| UI | 照 `PlayerView` 做畫面；審查畫面（逐張 5 秒＋檢舉鍵）；各種等待畫面 |

### 9.2 時程

| 日期 | A | B |
| :--- | :--- | :--- |
| 11/23 | 本文件定稿；`common` 提案 PR | 本文件定稿；開始改 rules |
| 11/24 | flow 型別骨架 PR（events / effects / views / timers / packets） | rules PR ①：errors、config、words、progress（通過 uv / ruff） |
| 11/25～26 | GameServer：LOBBY～SPY_ACTION | rules PR ②：roles、drawings、anonymity、voting、guessing |
| 11/27～28 | GameServer：REVIEW～ROUND_END | rules PR ③：review、scoring（含 settle_void_disconnect） |
| 11/29 | PlayerEngine | 一起寫 `test_full_game.py` |
| 11/30～12/1 | 斷線、安全測試、runtime | 補測試、修 bug |
| **12/2** | **第一次整合：3 台以上電腦跑完一局** | 同左 |
| 12/2～12/6 | 修整合問題 | 修整合問題 |

### 9.3 合併規則

- 每個 PR：通過 `uv run ruff check . && uv run ruff format --check . && uv run lint-imports && uv run pytest`，並由另一人 review。
- 改到本文件第 1、4、6、7 節 → 另一人同意才能合併。
- rules 和 flow 的介面以第 5 節的呼叫順序為驗收標準：`test_full_game.py` 能跑完 4、7、10 人整場才算對上。

---

## 10. 待確認 / 風險

| # | 項目 | 目前做法 |
| :--- | :--- | :--- |
| R1 | 計分平衡：10 人時投中間諜的一般玩家拿 23 分，間諜最多 +3 | 試玩後調 `ScoreRules` |
| R2 | 10 人時審查時間：10 張 × 5 秒 = 50 秒 | 可接受；太長再改每張秒數 |
| R3 | 開房者的電腦保有秘密，理論上他能偷看 | 接受（期末專案），報告中說明 |
| R4 | 「可辨認文字」的定義（數字、符號、箭頭算不算） | 開會時定幾個例子，寫進 game-rules |
| R5 | 平票（有人投）時間諜要猜；全部棄票間諜直接逃脫 | A 提案，**待 team leader 核准** |
| R6 | 斷線作廢局連處罰也不算 | A 提案，**待 team leader 核准** |
| R7 | 4～10 人、審查額度公式 ceil((N−3)/2) | A 提案，**待 team leader 核准** |
| R8 | 新增 REVIEW 會讓一般玩家在 REVEAL 前看到畫作，和 ADR 0005「REVEAL 前畫作只給房主」衝突 | ADR 0008 部分取代 0005（PR #14），team leader 核准 |

**核准流程：** 第 1 節與 R5～R8 已寫成 ADR 0008（依賴 #5 的 ADR 0007，部分取代 0005），在 PR #14 等 team leader 核准。核准前，B 先做不受影響的修改（改用 common 型別、修 ruff、ReviewPlan、拆檔），規則數值相關的測試等核准後再改。

---

## 11. 資料生命週期與提交點

**原則：每一局的狀態先存在「待提交」區，結算成功的那一刻才一次寫進正式狀態。** 因為 B 的物件都是不可變的，「作廢」只要丟掉待提交區就好，不需要回滾。

| 資料 | 正式狀態（committed） | 本局待提交（pending） |
| :--- | :--- | :--- |
| 分數 | `board` | `settled.total_delta` |
| 回合進度 | `progress` | `settled.progress` |
| 間諜歷史 | `history` | `settled.spy_history` |
| 審查紀錄 | `ledger` | `review.ledger` → `settled.ledger` |
| 名單 | `players` | `settled.removed_players`、斷線者 |

```text
DEAL ─ DRAWING ─ SPY_ACTION ─ REVIEW ─ VOTING ─ SPY_GUESS ─┤提交點├─ REVEAL ─ ROUND_END
│◄──────────── 斷線 → VOID_DISCONNECT，丟掉 pending ────────────►│◄─ 斷線 → 結果照算 ─►│
```

- **提交點**＝`settle_round()` 成功回傳、伺服器把 pending 寫入 committed 的那一步。
  - 正常局：在 VOTING 或 SPY_GUESS 結束時。
  - 參考圖違規：在 REVIEW 結束時（VOID_REFERENCE 也是一次提交，處罰照算）。
- **提交前斷線**：呼叫 `settle_void_disconnect(ledger=committed ledger)`，再把結果寫入 committed（只會增加 `attempts_settled`）。本局審查處罰隨 pending 一起丟掉。
- **提交後斷線**：不改本局結果；斷線者在下一局 DEAL 前移除，`restrict_ledger` 與 history 同步清掉。
- 同一局只能提交一次；`RoundProgress` 會擋重複結算。
- **原子性與順序**：GameServer 在單一 asyncio 執行緒依事件抵達順序逐一處理（ADR 0004）。VOID_REFERENCE、VOID_DISCONNECT 與正常結算互相競爭時，**先被處理的事件完成提交**；之後同一局的事件一律忽略。
- **畫面順序**：內部提交在 REVEAL **之前**；玩家看到的畫面順序是 REVEAL → ROUND_END。

### 11.2 開房者斷線時玩家端的分數

- `PlayerEngine` 保存**最後一次收到的** `ROUND_RESULT`（含累計分數與 `completed_rounds`）作為快照。
- 收到 `PeerLeft(server)`（心跳逾時偵測，有數秒延遲）→ `GameOver(HOST_LEFT)`，`PlayerView` 顯示快照與「截至第 N 回合」。
- 若伺服器在提交後、廣播前當機，最新一局無法取得，以快照為準。
- 從未收到任何 `ROUND_RESULT` → 顯示「遊戲中斷，尚無分數」（`ranking` 為空、`snapshot_round` 為 None）。
- 作廢局（VOID_DISCONNECT、VOID_REFERENCE）會增加 `attempts_settled`、不增加 `completed_rounds`，所以下一局的 `attempt_id` 一定是新的，不會重複。

### 11.3 例外：題庫使用紀錄不回滾

- 題目在 DEAL 發出去的那一刻就加入 `used`，**作廢也不移除**（玩家已經看過題目，補局不能再出同一題）。
- 題庫全部用完時：清空 `used` 重新開始，但**排除剛剛出過的那一題**（`draw(..., last_answer=...)`），避免連續兩局同一題。A 保存 `last_answer`。
- 題庫至少要比「最多局數」多：`len(cards) > target_rounds + 預期作廢局`；B 的 `GameConfig.validate()` 可加警告（59 題 > 5 回合，目前足夠）。

