# Coding Agent 設定指南

本專案支援 Codex、Claude Code、OpenCode、Pi、GitHub Copilot、Antigravity。
**不需要另外設定**，clone 下來就會讀到團隊規則。這份文件說明各工具讀哪些檔案，以及怎麼確認有讀到。

## 檔案結構

| 檔案 | 用途 | 誰讀 |
| :--- | :--- | :--- |
| `AGENTS.md` | 全專案規則（唯一來源） | 全部 |
| `CLAUDE.md` | 只有一行 `@AGENTS.md` | Claude Code（Copilot 也會讀到，無影響） |
| `src/pretend2paint/<模組>/AGENTS.md` | 模組規則 | Claude Code、OpenCode、Copilot CLI 會在讀到該目錄檔案時自動載入；其他工具靠根目錄 `AGENTS.md` 指示主動讀取 |
| `.agents/skills/` | Skills（唯一來源） | Codex、OpenCode、Pi、Copilot、Antigravity |
| `.claude/skills/` | Skills 副本（由腳本產生） | Claude Code（OpenCode、Copilot 也會讀，同名 skill 可能列兩次，無影響） |
| `.claude/settings.json` | Claude Code 權限：禁止 push main / force push / pip install | Claude Code |

## 確認規則有載入

開一個新 session，問 agent：**「列出你目前載入的規則檔與 skills」**，應該要看到根目錄的 `AGENTS.md` 和 4 個 skills（`pr-workflow`、`add-packet-type`、`module-api-doc`、`write-adr`）。

各工具也有內建方式：

| 工具 | 確認方式 |
| :--- | :--- |
| Codex | 問「List the instruction sources you loaded」；`/skills` 看 skills |
| Claude Code | `/context` 或 `/memory`；`/skills` |
| OpenCode | 問 agent；skills 會出現在可用工具中 |
| Pi | 問 agent；`/skill:<名稱>` 手動載入 skill |
| Copilot CLI | `/instructions`；`/skills` |
| Copilot（VS Code） | Chat 回覆下方的 References 會列出 `AGENTS.md` |
| Antigravity | 問 agent；提到 skill 名稱可以強制使用 |

## 建議用法

- **從 repo 根目錄啟動 agent。** 從子目錄啟動時，部分工具會漏掉上層規則以外的設定。
- 開始任務時直接說明你負責的模組，例如：「我是 core 組，要實作投票階段」。
- 要發 PR 時說「照 pr-workflow 發 PR」。

## 不要做的事

- **不要在 repo 內建立 `AGENTS.override.md`。** Codex / Pi 會用它取代同目錄的 `AGENTS.md`，等於關掉團隊規則（CI 會擋）。
- 不要在 repo 內放 `CLAUDE.local.md`：Claude Code 看到它就可能不讀 `AGENTS.md`。
- 不要修改 `.claude/skills/`，它會被同步腳本覆蓋。
- 個人偏好（回覆語言、口吻等）請放在自己的全域設定：
  - Codex：`~/.codex/AGENTS.md`
  - Claude Code：`~/.claude/CLAUDE.md`
  - OpenCode：`~/.config/opencode/AGENTS.md`
  - Pi：`~/.pi/agent/AGENTS.md`
  - Copilot CLI：`~/.copilot/copilot-instructions.md`
  - Antigravity：`~/.gemini/AGENTS.md`

## 已知限制

- Codex、Pi、Antigravity **不會自動載入子目錄的 `AGENTS.md`**。根目錄 `AGENTS.md` 已要求 agent 修改模組前主動閱讀；若發現 agent 沒照模組規則做，請提醒它「先讀 `src/pretend2paint/<模組>/AGENTS.md`」。
- GitHub 網頁版的 Copilot Chat 不讀 `AGENTS.md`。
- 規則檔只是給 agent 的指示，不保證遵守。真正的把關是 CI、分支保護與 code review。
