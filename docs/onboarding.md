# Pretend2Paint 新手上路指南

> 第一次設定約 10 分鐘，**請在本週內完成**。
> Repo：https://github.com/NTUST-ICN-G7/Pretend2Paint

## 目錄

1. [基本資訊](#一基本資訊)
2. [第一次設定](#二第一次設定)
3. [用 Coding Agent 理解專案](#三用-coding-agent-理解專案)
4. [開發流程](#四開發流程)
5. [注意事項](#五注意事項)
6. [各組 11/22 前的重點](#六各組-1122-前的重點)

---

## 一、基本資訊

### 遊戲：P2P「誰是臥底」畫圖版

- 一般玩家拿到**答案**，間諜只拿到**提示**（例：答案「西瓜」→ 提示「兩個字的水果」）
- 一般玩家各自從白板開始畫，畫作先不公開
- 間諜從畫好的圖中**盲選一張**當參考，再自己畫
- 公開所有畫作，被間諜選中的那張會被標記（代表作者一定不是間諜）
- 投票找出間諜：間諜沒被票出就得分；被票出時可以猜一次答案，猜對得分、猜錯扣分

完整規則：[`docs/game-rules.md`](game-rules.md)

### 技術

- **Python 3.14**，用 **uv** 管理環境
- UI 框架：**tkinter**（Python 內建，見 [ADR 0006](decisions/0006-ui-framework.md)）

### 分工

| 模組 | 負責人 | 程式位置 |
| :--- | :--- | :--- |
| P2P Infra | 葉柏辰 | `src/pretend2paint/p2p/` |
| Streaming | 李昇原、黃佑竣 | `src/pretend2paint/streaming/` |
| Core | 張瀚元、鄒聿銘 | `src/pretend2paint/core/` |
| Canvas / UI | 錢呈恩、李愷哲、石凡可、簡國行 | `src/pretend2paint/ui/` |

測試放在 `tests/<模組>/`。

### 時程

| 期間 | 目標 |
| :--- | :--- |
| **11/15 ~ 11/22** | **各模組完成 API 文件**（`src/pretend2paint/<模組>/README.md`） |
| 11/22 ~ 12/06 | 寫程式 |
| 12/06 ~ 12/13 | 測試、修正 |
| 12/13 ~ 12/22 | 書面與口頭報告 |

### 重要文件

| 文件 | 內容 |
| :--- | :--- |
| [`README.md`](../README.md) | 專案總覽 |
| [`AGENTS.md`](../AGENTS.md) | 給 agent 的規則（人也值得讀一遍） |
| [`docs/architecture.md`](architecture.md) | 分層、資料流、執行緒模型 |
| [`docs/protocol.md`](protocol.md) | 封包格式與列表 |
| [`docs/decisions/`](decisions/) | 已定案的設計決策 |
| [`docs/agent-setup.md`](agent-setup.md) | 各 agent 工具的詳細說明 |

---

## 二、第一次設定

### 1. 安裝 uv

不需要自己裝 Python，uv 會自動下載 3.14。

macOS / Linux：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows（PowerShell）：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

裝完**重開終端機**，執行 `uv --version` 確認。

### 2. 取得專案

還沒 clone 過：

```bash
git clone git@github.com:NTUST-ICN-G7/Pretend2Paint.git
cd Pretend2Paint
```

已經 clone 過：

```bash
cd Pretend2Paint
git fetch origin
git switch main
git pull
```

### 3. 建立環境

```bash
uv sync                      # 建立環境、安裝套件
uv run pre-commit install    # 每次 commit 前自動檢查
uv run pytest                # 確認環境正常
```

看到 `6 passed` 就完成了 ✅

> `pre-commit` 會在 commit 前檢查格式與架構，有問題會擋下來，照提示修正即可。

---

## 三、用 Coding Agent 理解專案

專案已經寫好給 agent 的規則。**Codex、Claude Code、OpenCode、Pi、GitHub Copilot、Antigravity 都不需要另外設定**，打開就會照規範工作。

> ⚠️ **一定要從 repo 根目錄（`Pretend2Paint/`）啟動 agent**，從子資料夾開會讓部分工具漏讀規則。

### Step 1：讓 agent 帶你看懂專案

開一個新對話，貼上這段（把「XX 組」換成你的組別）：

```text
我是 XX 組的成員，第一次接觸這個專案。請讀 README.md、AGENTS.md、
docs/game-rules.md、docs/architecture.md、docs/protocol.md，
以及我負責模組的 AGENTS.md，然後用簡單的方式告訴我：
1. 這個遊戲怎麼玩、一回合有哪些階段
2. 整個程式分成哪幾層、資料怎麼流動
3. 我負責的模組要做什麼、不能做什麼
4. 我的模組要提供什麼給別組、需要別組提供什麼
5. 11/22 前我具體要完成什麼
```

### Step 2：寫 API 文件（11/22 前）

```text
我是 XX 組。請用 module-api-doc skill，根據 docs/ 與我們模組的 AGENTS.md，
幫我草擬 src/pretend2paint/<模組>/README.md 的 API 文件。
不確定的地方列出來問我，不要自己決定。
```

> 寫完**自己讀過一遍**，和組員確認後再發 PR。

### 常用說法

| 情境 | 對 agent 說 |
| :--- | :--- |
| 看不懂某條規則 | 「為什麼要這樣規定？請查 `docs/decisions/` 說明」 |
| 開始寫功能 | 「我要做 XXX，先告訴我你打算改哪些檔案，我確認後再開始」 |
| 發 PR | 「照 pr-workflow skill 幫我開分支、commit、發 PR」 |
| 新增封包 | 「用 add-packet-type skill 新增 XXX 封包」 |
| 問專案問題 | 「請根據這個專案的文件回答：……」 |

### 內建 Skills

| Skill | 用途 |
| :--- | :--- |
| `pr-workflow` | 開分支、commit、跑檢查、發 PR |
| `module-api-doc` | 照統一格式寫 API 文件 |
| `add-packet-type` | 新增或修改封包，會一起更新文件與測試 |
| `write-adr` | 記錄設計決策 |

### 確認 agent 有讀到規則

問它：「**列出你目前載入的規則檔與 skills**」，應該要看到 `AGENTS.md` 和上面 4 個 skill。
各工具的確認方式見 [`docs/agent-setup.md`](agent-setup.md)。

---

## 四、開發流程

### 1. 從最新的 main 開分支

```bash
git switch main
git pull
uv sync
git switch -c feature/<模組>-<描述>
```

- 新功能：`feature/core-voting`、`feature/ui-canvas`
- 修 bug：`fix/<模組>-<描述>`

### 2. Commit 訊息

格式：`<type>(<模組>): <描述>`（英文）

```text
feat(core): add voting phase
fix(streaming): handle oversized packet length
docs(p2p): add connection pool API
```

type：`feat` / `fix` / `docs` / `test` / `refactor` / `chore`

### 3. 發 PR 前在本機檢查

```bash
uv run ruff check . && uv run ruff format --check . && uv run lint-imports && uv run pytest
```

### 4. Push 並發 PR 到 main

```bash
git push -u origin HEAD
```

到 GitHub 發 PR，需要 **1 人 approve** 且 **CI 通過**才能合併。

### 5. 每次 pull 之後

```bash
uv sync
```

---

## 五、注意事項

### Git

- 🚫 **不能直接 push 到 main**（GitHub 會擋），所有改動都走 PR
- 🚫 不要 `git push --force`、不要刪別人的分支
- PR 盡量小、一次做一件事，比較好 review

### 程式

- **只改自己組的資料夾。** 需要改別組或 `common/`，先在群組找該組討論
- 🚫 **不要用 `pip install`。** 需要新套件先在群組提出，由 team leader 決定
- **分層規則**：`ui → core → streaming → p2p → common`，只能由左往右 import（CI 會自動檢查）；下層要通知上層用 callback
- `core` 只放純邏輯，不碰網路、不碰畫面
- **UI 組**：框架用 tkinter（Python 內建），不用也不要另外安裝 GUI 套件

### 遊戲安全（很重要）

- 🔒 **答案、提示、誰是間諜，只能單獨發給個別玩家，絕對不能廣播**，否則間諜看封包就知道答案
- 🔒 公開階段之前，畫作只能送給房主

### 使用 Agent

- **Agent 寫的東西你要看得懂、講得出來。** 報告和 review 都會問到，不能只說「AI 寫的」
- Agent 說「完成了」不代表真的完成，**一定要看到檢查指令全部通過**
- Agent 要改別組的檔案、新增套件、或修改 `AGENTS.md` / `.agents/` / `.claude/` 時，**先停下來問群組**
- 🚫 不要在專案內建立 `AGENTS.override.md` 或 `CLAUDE.local.md`，它們會蓋掉團隊規則（CI 會擋）。個人偏好請放在自己電腦的全域設定，位置見 [`docs/agent-setup.md`](agent-setup.md)
- 🚫 不要把 API key、密碼放進程式或 commit

### 規則有疑問

- 已定案的決策都在 [`docs/decisions/`](decisions/)（例如「房主負責出題計分」、「網路與 UI 分開執行緒」），請照著做
- 覺得規則不合理，**在群組提出**，不要自己改掉

---

## 六、各組 11/22 前的重點

### P2P（葉柏辰）

- 定出 connection pool 的 API
- 必須支援**只發給指定玩家**（單播）
- 收到資料時用 callback 通知上層
- 細節：[`src/pretend2paint/p2p/AGENTS.md`](../src/pretend2paint/p2p/AGENTS.md)

### Streaming（李昇原、黃佑竣）

- 程式已搬到 `src/pretend2paint/streaming/`，**邏輯沒動**，只改了 import 與 logging 寫法
- 之後請從 main 開新分支開發；舊的 `feature/streaming-prototype` 確認不需要後會刪除
- [`docs/protocol.md`](protocol.md) 整理了待補的封包和 3 個待決問題，請先看

### Core（張瀚元、鄒聿銘）

- 定出遊戲狀態機與房主邏輯的 API
- 規則沒寫清楚的地方（平票、一般玩家計分、房主斷線）請提案，不要自己發明

### UI（錢呈恩、李愷哲、石凡可、簡國行）

- ~~評估 tkinter / pygame-ce / PyQt6~~ → 已決定使用 tkinter（[`docs/decisions/0006-ui-framework.md`](decisions/0006-ui-framework.md)）
- 列出需要的畫面清單

---

有問題直接在群組問，或先問你的 agent：「請根據這個專案的文件回答：……」🙌
