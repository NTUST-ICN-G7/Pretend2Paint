## 這個 PR 做了什麼
<!-- 一兩句話說明 -->

## 模組
- [ ] p2p
- [ ] streaming
- [ ] core
- [ ] ui
- [ ] common / 跨模組（請 @ 受影響模組的負責人）
- [ ] 文件 / 設定

## 檢查
- [ ] 只改到自己負責的模組（若否，請說明原因）
- [ ] 沒有新增依賴（若有，已經 team leader 同意）
- [ ] 改到封包時，已同步更新 `docs/protocol.md` 與兩端測試
- [ ] 機密資訊（答案、提示、間諜身分）沒有被廣播
- [ ] 本機已通過：`uv run ruff check . && uv run ruff format --check . && uv run lint-imports && uv run pytest`

## 如何測試 / 截圖
<!-- 選填 -->
