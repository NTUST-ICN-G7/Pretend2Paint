# AGENTS.md — Pretend2Paint

給所有 coding agent（Codex、Claude Code、OpenCode、Pi、GitHub Copilot、Antigravity）的專案規範。
**這份檔案與各模組的 `AGENTS.md` 是唯一的規則來源；`CLAUDE.md` 只是匯入它。**

## 專案

NTUST ICN 期末專案：P2P「誰是臥底」畫圖版。Python 3.14，用 uv 管理環境。
- 遊戲規則：`docs/game-rules.md`
- 架構與分層：`docs/architecture.md`
- 通訊協定（封包唯一來源）：`docs/protocol.md`
- 已定案的決策：`docs/decisions/`（不要違反；有疑慮就停下來問使用者）

## 目錄與負責人

| 路徑 | 模組 | 負責人 | 改之前先讀 |
| :--- | :--- | :--- | :--- |
| `src/pretend2paint/common/` | 共用型別（契約） | team leader | `src/pretend2paint/common/AGENTS.md` |
| `src/pretend2paint/p2p/` | P2P Infra | 葉柏辰 | `src/pretend2paint/p2p/AGENTS.md` |
| `src/pretend2paint/streaming/` | Streaming | 李昇原、黃佑竣 | `src/pretend2paint/streaming/AGENTS.md` |
| `src/pretend2paint/core/` | Core | 張瀚元、鄒聿銘 | `src/pretend2paint/core/AGENTS.md` |
| `src/pretend2paint/ui/` | Canvas / UI | 錢呈恩、李愷哲、石凡可、簡國行 | `src/pretend2paint/ui/AGENTS.md` |
| `src/pretend2paint/__main__.py` | 組裝與啟動 | team leader | `docs/architecture.md` |
| `tests/<模組>/` | 各模組測試 | 同模組 | — |

**重要：** 在修改上表任何目錄的檔案之前，**先讀該目錄的 `AGENTS.md`**。部分工具不會自動載入子目錄的規則檔，所以請主動讀。

## 指令

```bash
uv sync                          # 安裝 / 更新環境（第一次與 pull 之後）
uv run pytest                    # 測試
uv run ruff check --fix .        # lint
uv run ruff format .             # format
uv run lint-imports              # 檢查分層依賴
uv run python scripts/agent_workspace.py check   # 檢查 agent 設定檔
uv run python -m pretend2paint   # 執行
```

一律用 `uv run` / `uv add`，**不要用 `pip install`**，不要自己建 venv。

## 必須遵守

### 範圍
1. **只改使用者負責的模組。** 如果任務需要改到別的模組、`common/`、`pyproject.toml`、`docs/decisions/`、或任何 agent 設定檔，**先停下來告訴使用者**，說明要改什麼、為什麼，由使用者決定是否另開 PR 找負責人。
2. **不要新增依賴**（`uv add`）。需要新套件時先告訴使用者，由 team leader 決定。
3. 不要為了讓測試通過而刪除或弱化別人的測試。

### 架構（`docs/architecture.md`）
4. 分層：`ui > core > streaming > p2p > common`。**下層不可 import 上層**；往上送資料用 callback / 事件。
5. 跨模組只用 `common/` 的型別和對方 `__init__.py` 公開的 API，不要 import 對方的內部檔案。
6. `core` 是純邏輯，不做網路或 UI 的 I/O。
7. UI 在主執行緒；p2p / streaming / core 在同一條背景 asyncio 執行緒；兩邊只用 `queue.Queue` 溝通。

### 協定與安全
8. **答案、提示、間諜身分只能單播，絕對不能廣播。** `Phase.REVEAL` 前的畫作只能送給房主。
9. 新增或修改封包：同一個 PR 內更新 `docs/protocol.md`、`streaming/protocol.py`、兩端的測試。使用 `add-packet-type` skill。

### 程式風格
10. 識別字、commit 訊息用英文；註解、docstring、文件可以用繁體中文。
11. 公開的函式 / 類別要有 type hints 和 docstring。
12. 用 `logging.getLogger(__name__)`，不要在模組裡呼叫 `logging.basicConfig()`；不要用 `print` 除錯後留在程式裡。
13. 新功能要附測試，放在 `tests/<模組>/test_*.py`。

### Git
14. **不可 commit 或 push 到 `main`。** 從最新的 `main` 開分支：`feature/<模組>-<描述>` 或 `fix/<模組>-<描述>`。
15. Commit 格式：`<type>(<模組>): <描述>`，type 為 `feat` / `fix` / `docs` / `test` / `refactor` / `chore`。
16. 不要 `git push --force`、不要改寫已 push 的歷史、不要刪除遠端分支。
17. 發 PR 前使用 `pr-workflow` skill。

## 完成的定義

宣稱任務完成之前，必須全部通過並**在回覆中附上結果**：

```bash
uv run ruff check . && uv run ruff format --check . && uv run lint-imports && uv run pytest
```

沒跑、或有失敗，就明確說「未通過」以及原因，不要說「應該可以」。

## Skills

位於 `.agents/skills/`（Claude Code 用同步產生的 `.claude/skills/`，不要手改）：

| Skill | 什麼時候用 |
| :--- | :--- |
| `pr-workflow` | 開分支、commit、跑檢查、發 PR |
| `add-packet-type` | 新增或修改通訊封包 |
| `module-api-doc` | 撰寫或更新模組的 API 文件（`README.md`） |
| `write-adr` | 記錄架構或規範決策 |

## 修改 agent 設定

`AGENTS.md`、`CLAUDE.md`、`.agents/`、`.claude/` 由 team leader 維護。改完 `.agents/skills/` 後執行
`uv run python scripts/agent_workspace.py sync`。
