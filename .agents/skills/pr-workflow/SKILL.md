---
name: pr-workflow
description: Pretend2Paint 的標準 Git 流程：從 main 開分支、照格式 commit、跑完整檢查、發 Pull Request。在開始新任務、要 commit、要 push 或要發 PR 時使用。
---

# PR 流程

## 1. 開分支（開始任務時）

```bash
git switch main
git pull
git switch -c <type>/<模組>-<描述>
uv sync
```

- `<type>`：`feature`（新功能）、`fix`（修 bug）、`docs`、`chore`
- `<模組>`：`p2p` / `streaming` / `core` / `ui` / `common`
- `<描述>`：英文小寫、用 `-` 連接，例如 `feature/core-voting`

如果目前已經在一個功能分支上，且任務與該分支相同，就不用開新分支。**絕對不要在 `main` 上 commit。**

## 2. 確認範圍

```bash
git status
git diff --stat main...HEAD
```

- 改到的檔案應該都在使用者負責的模組（以及 `tests/<模組>/`）內。
- 如果改到別的模組、`common/`、`pyproject.toml`、`uv.lock`、`docs/decisions/` 或 agent 設定檔：**停下來告訴使用者**，建議拆成另一個 PR。

## 3. 檢查（全部要通過）

```bash
uv run ruff check --fix .
uv run ruff format .
uv run lint-imports
uv run pytest
```

有失敗就修，修不好就如實告訴使用者，不要跳過。

## 4. Commit

格式：`<type>(<模組>): <描述>`（英文、祈使句、小寫開頭）

```bash
git add <具體檔案>          # 不要 git add -A，避免帶到無關檔案
git commit -m "feat(core): add voting phase"
```

type：`feat` / `fix` / `docs` / `test` / `refactor` / `chore`。一個 commit 做一件事。

## 5. Push 與發 PR

```bash
git fetch origin
git rebase origin/main        # 有衝突就停下來問使用者
uv run pytest                 # rebase 後再跑一次
git push -u origin HEAD
```

發 PR（有 `gh` 的話）：

```bash
gh pr create --base main --fill
```

然後依照 `.github/pull_request_template.md` 補完說明。沒有 `gh` 就把 GitHub 上建立 PR 的網址給使用者。

## 禁止
- `git push --force` / `-f`（rebase 後真的需要時，問使用者後用 `--force-with-lease`，且只能用在自己的功能分支）
- 直接 push 到 `main`
- 刪除遠端分支、改寫別人的 commit
