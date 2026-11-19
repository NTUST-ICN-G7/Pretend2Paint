# Pretend2Paint

NTUST ICN 期末專案（G7）— **P2P 誰是臥底・畫圖版**

技術棧：Python 3（UI 框架待訂）

---

## 遊戲規則

1. **局外 Landing space**：玩家發現彼此、加入房間。
2. **每回合流程**
   1. **發題**：選詞或隨機生題。一般玩家拿到完整答案；間諜只拿到提示（例：答案「西瓜」→ 提示「兩個字的水果」）。
   2. **畫圖階段**：所有拿到正確答案的玩家各自從白板開始畫（不是接龍）。此階段畫作**不公開**。
   3. **間諜行動階段**：間諜從已完成的畫作中**盲選 1 張**作為參考，然後開始畫圖。
   4. **公開階段**：所有畫作公開；被間諜選中參考的畫作會被**標記**（代表該作者一定不是間諜）。
   5. **投票**：投出自己認為的間諜。
      - 間諜沒有得到最高票 → 間諜得分
      - 間諜被票出 → 間諜有一次機會猜答案：猜對得分、猜錯扣分
3. 回合結束

---

## 模組與分工

| 目錄 | 模組 | 負責人 | 內容 |
| :--- | :--- | :--- | :--- |
| `p2p/` | P2P Infra | 葉柏辰 | P2P 拓樸與 lifecycle 管理：UDP Broadcast（node discovery）、TCP full-mesh / connection pool |
| `streaming/` | Streaming | 李昇原、黃佑竣 | 通訊協定實作、Framing、封包管理 |
| `core/` | Core | 張瀚元、鄒聿銘 | 遊戲核心邏輯：業務邏輯（計分等）、狀態管理 |
| `ui/` | Canvas / UI | 錢呈恩、李愷哲、石凡可、簡國行 | 遊戲介面、畫布功能、UI 設計與開發 |

各模組的 API 說明請寫在該目錄的 `README.md`。

---

## 時程

| 期間 | 目標 |
| :--- | :--- |
| 11/15 ~ 11/22（1 週） | 完成 API（包含 Prototype、功能說明） |
| 11/22 ~ 12/06（2 週） | 寫程式 |
| 12/06 ~ 12/13（1 週） | 測試、修正 |
| 12/13 ~ 12/22 | 文字和口頭報告 |

---

## 開發規範

### 分支
- `main`：受保護分支，**不可直接 push**，只能透過 Pull Request 合併。
- 開發一律從最新的 `main` 開分支，命名：`feature/<模組>-<描述>`
  - 例：`feature/p2p-discovery`、`feature/core-scoring`、`feature/ui-canvas`
  - 修 bug：`fix/<模組>-<描述>`

```bash
git switch main
git pull
git switch -c feature/<模組>-<描述>
# ...開發、commit...
git push -u origin feature/<模組>-<描述>
# 到 GitHub 發 PR → main
```

### Pull Request
- 至少 **1 人 review** 通過才能合併。
- PR 盡量小、單一目的；標題寫清楚模組與內容。
- 合併前請先同步 `main`，確保測試通過。

### Commit 訊息
建議格式：`<type>(<模組>): <描述>`
- type：`feat` / `fix` / `docs` / `test` / `refactor` / `chore`
- 例：`feat(streaming): add vote packet type`

### 測試
```bash
cd streaming && python3 -m unittest -v
```

---

## 待辦 / 跨模組待討論

- [ ] **Streaming**：補齊封包類型 — 發題（答案/提示）、階段切換（畫圖 → 間諜行動 → 公開 → 投票）、投票、間諜猜答案、計分結果
- [ ] **Core + Streaming**：決定由誰出題。答案與提示必須**單播**給個別玩家，不可廣播，否則間諜可直接從封包看到答案
- [ ] **UI**：決定 UI 框架
- [ ] **全體**：模組之間改用 package import（目前 `streaming/` 內使用 `from protocol import ...`，只能在該目錄內執行）
