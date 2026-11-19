# 0001. 開發工具鏈：Python 3.14 + uv

- 狀態：通過
- 日期：2026-11-20
- 決策者：banahaker（team leader）

## 背景
組員本機的 Python 版本不一（有人是 3.10），各自用 pip 安裝會造成「我這邊可以跑」的問題。

## 決定
- Python **3.14**（`.python-version`、`requires-python = ">=3.14"`）。
- 環境與依賴一律用 **uv** 管理，`uv.lock` 進版控。不要用 `pip install`。
- Lint / format：**ruff**；測試：**pytest**；分層檢查：**import-linter**；commit 前檢查：**pre-commit**。
- 新增依賴必須先在群組討論，經 team leader 同意。

## 影響
- 本機不需要自己裝 Python 3.14，`uv sync` 會自動下載。
- 所有指令都透過 `uv run ...` 執行，確保大家用同一套版本。
