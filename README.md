# Pretend2Paint

NTUST ICN 期末專案（G7）— **P2P 誰是臥底・畫圖版**

一般玩家拿到答案、間諜只拿到提示；大家各自畫圖，間諜盲選一張別人的畫作參考後再畫，最後投票找出間諜。
完整規則見 [docs/game-rules.md](docs/game-rules.md)。

## 快速開始

1. 安裝 [uv](https://docs.astral.sh/uv/getting-started/installation/)（不需要自己裝 Python，uv 會自動下載 3.14）
2. 設定環境：

```bash
git clone git@github.com:NTUST-ICN-G7/Pretend2Paint.git
cd Pretend2Paint
uv sync                       # 建立環境、安裝依賴
uv run pre-commit install     # commit 前自動檢查
uv run pytest                 # 確認一切正常
```

執行：`uv run python -m pretend2paint`

## 文件

| 文件 | 內容 |
| :--- | :--- |
| [docs/onboarding.md](docs/onboarding.md) | **新手上路：第一次設定、用 agent 理解專案、注意事項** |
| [docs/game-rules.md](docs/game-rules.md) | 遊戲規則與回合流程 |
| [docs/architecture.md](docs/architecture.md) | 目錄、分層、資料流、執行緒模型 |
| [docs/protocol.md](docs/protocol.md) | 通訊協定與封包列表 |
| [docs/decisions/](docs/decisions/) | 已定案的設計決策（ADR） |
| [docs/agent-setup.md](docs/agent-setup.md) | Coding agent（Codex / Claude Code / OpenCode / Pi / Copilot / Antigravity）說明 |
| [AGENTS.md](AGENTS.md) | 給 coding agent 的專案規範（人也值得讀一遍） |

## 模組與分工

| 目錄 | 模組 | 負責人 |
| :--- | :--- | :--- |
| [`src/pretend2paint/p2p/`](src/pretend2paint/p2p/) | P2P Infra：UDP discovery、TCP connection pool | 葉柏辰 |
| [`src/pretend2paint/streaming/`](src/pretend2paint/streaming/) | 通訊協定、Framing、封包管理 | 李昇原、黃佑竣 |
| [`src/pretend2paint/core/`](src/pretend2paint/core/) | 遊戲邏輯、狀態管理、計分 | 張瀚元、鄒聿銘 |
| [`src/pretend2paint/ui/`](src/pretend2paint/ui/) | 遊戲介面、畫布 | 錢呈恩、李愷哲、石凡可、簡國行 |
| [`src/pretend2paint/common/`](src/pretend2paint/common/) | 跨模組共用型別 | team leader |

各模組的 API 說明在該目錄的 `README.md`，模組規則在 `AGENTS.md`。測試放在 `tests/<模組>/`。

## 時程

| 期間 | 目標 |
| :--- | :--- |
| 11/15 ~ 11/22（1 週） | 完成 API（包含 Prototype、功能說明） |
| 11/22 ~ 12/06（2 週） | 寫程式 |
| 12/06 ~ 12/13（1 週） | 測試、修正 |
| 12/13 ~ 12/22 | 文字和口頭報告 |

## 開發規範

### 分支與 PR
- `main` 受保護：**不可直接 push**，只能透過 PR 合併，需要 **1 人 approve** 且 CI 通過。
- 從最新的 `main` 開分支：`feature/<模組>-<描述>`、`fix/<模組>-<描述>`

```bash
git switch main && git pull
git switch -c feature/core-voting
# ...開發、commit...
git push -u origin feature/core-voting
# 到 GitHub 發 PR → main
```

### Commit 訊息
`<type>(<模組>): <描述>`，type：`feat` / `fix` / `docs` / `test` / `refactor` / `chore`
例：`feat(streaming): add vote packet type`

### 檢查（CI 也會跑同樣的項目）

```bash
uv run ruff check --fix .     # lint
uv run ruff format .          # 格式化
uv run lint-imports           # 檢查模組依賴方向
uv run pytest                 # 測試
```

### 規則重點
- 只改自己負責的模組；需要改別人的模組或 `common/`，先找負責人。
- 不要用 `pip install`；新增依賴先在群組討論。
- 答案、提示、間諜身分**只能單播**，不能廣播。

## 待辦

- [ ] **全體**：11/22 前完成各模組 `README.md` 的 API 說明
- [ ] **Streaming**：補齊封包類型並處理 [protocol.md](docs/protocol.md) 的待決問題
- [ ] **Core**：提案一般玩家計分、平票、房主斷線處理
- [x] **UI**：評估 UI 框架 → 使用 tkinter（[ADR 0006](docs/decisions/0006-ui-framework.md)）
