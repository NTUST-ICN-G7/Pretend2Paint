# 0002. 分層架構

- 狀態：通過
- 日期：2026-11-20
- 決策者：banahaker（team leader）

## 背景
四個小組平行開發，如果模組之間任意互相 import，很容易出現循環依賴，也很難各自測試。

## 決定
- 分層：`ui > core > streaming > p2p > common`。上層可以 import 下層，下層不可 import 上層。
- 下層往上送資料用 callback / 事件。
- `__main__.py` 是 composition root，負責組裝所有模組。
- 跨模組只使用 `common/` 的型別與各模組 `__init__.py` 公開的 API。
- CI 用 import-linter 強制檢查。

## 影響
- p2p 不能直接呼叫 `streaming`；要提供 callback 註冊介面。
- core 不做 I/O，可以完全用單元測試驗證。
