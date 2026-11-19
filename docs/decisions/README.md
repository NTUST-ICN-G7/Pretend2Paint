# 決策紀錄（ADR）

重要的架構或規範決定都記錄在這裡，避免同樣的事情反覆討論、或不同人做出互相矛盾的實作。

- 檔名：`NNNN-簡短英文描述.md`，編號遞增，不要重複使用。
- 格式：複製 [0000-template.md](0000-template.md)。agent 請使用 `write-adr` skill。
- 已經「通過」的決定不要直接改內容；要推翻就新增一份 ADR，並把舊的狀態改成「已被 NNNN 取代」。

| 編號 | 標題 | 狀態 |
| :--- | :--- | :--- |
| [0001](0001-toolchain.md) | 開發工具鏈：Python 3.14 + uv | 通過 |
| [0002](0002-layered-architecture.md) | 分層架構 | 通過 |
| [0003](0003-host-authority.md) | 由房主作為權威節點 | 通過 |
| [0004](0004-threading-model.md) | 執行緒模型 | 通過 |
| [0005](0005-secret-information.md) | 機密資訊只能單播 | 通過 |
| [0006](0006-ui-framework.md) | UI 框架 | 待定 |
