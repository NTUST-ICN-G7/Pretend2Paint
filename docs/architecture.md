# 架構

## 目錄

```
src/pretend2paint/
├── __main__.py   # composition root：組裝各模組並啟動
├── common/       # 跨模組共用型別與事件（契約）
├── p2p/          # P2P Infra：discovery、connection pool
├── streaming/    # 通訊協定、framing、封包分發
├── core/         # 遊戲邏輯：狀態機、計分
└── ui/           # 介面與畫布
tests/<模組>/     # 對應各模組的測試
docs/             # 規則、架構、協定、決策紀錄
```

## 分層（[ADR 0002](decisions/0002-layered-architecture.md)）

```
ui ──► core ──► streaming ──► p2p
 │       │          │          │
 └───────┴──────────┴──────────┴──► common
```

- **上層可以 import 下層，下層不可 import 上層。** CI 用 `import-linter` 強制檢查（設定在 `pyproject.toml`）。
- 下層要把資料往上送，一律用 **callback / 事件**，由上層註冊。例如 p2p 收到資料後呼叫上層註冊的 `on_data(peer_id, raw_bytes)`，而不是 `import streaming`。
- `__main__.py` 是唯一可以同時 import 所有模組的地方，負責把它們接起來。
- 模組之間只透過 **`common/` 的型別** 和 **各模組在 `__init__.py` 公開的 API** 溝通，不要 import 別人模組的內部檔案。

## 各層職責

| 層 | 負責 | 不負責 |
| :--- | :--- | :--- |
| `p2p` | 找到節點、建立與維護 TCP 連線、送收 raw bytes、斷線通知 | 封包格式、遊戲規則 |
| `streaming` | 封包格式、framing、編解碼、依類型分發給上層 | 遊戲規則、決定要送給誰 |
| `core` | 遊戲狀態機、出題、指定間諜、投票、計分、決定每個訊息送給誰 | 網路細節、畫面 |
| `ui` | 畫面、畫布、使用者輸入 | 遊戲規則判斷 |
| `common` | 共用型別（`PlayerId`、`Phase`、`Role`…） | 任何邏輯 |

`core` 必須是**純邏輯**：不直接做網路或 UI 的 I/O，輸入是事件、輸出是「要送出的訊息」和「狀態變化」。這樣不開網路也能寫單元測試。

## 資料流

```
[收] 網路 ─► p2p ─(raw bytes)─► streaming ─(packet_type, payload)─► core ─(狀態變化)─► ui
[送] ui ─(使用者動作)─► core ─(訊息, 對象)─► streaming ─(bytes)─► p2p ─► 網路
```

## 權威節點（[ADR 0003](decisions/0003-host-authority.md)）

由**房主**統一出題、指定間諜、收集畫作與投票、計分，再把結果發給其他人。其他玩家只送出自己的動作。

## 執行緒模型（[ADR 0004](decisions/0004-threading-model.md)）

```
主執行緒：UI event loop ◄──── ui_queue ────┐
     │                                      │
     └──── net_queue ────► 背景執行緒：asyncio event loop（p2p + streaming + core）
```

- UI 框架的 event loop 佔用主執行緒。
- 網路（p2p）、封包處理（streaming）、遊戲邏輯（core）在**一條**背景執行緒的 asyncio loop 裡跑，core 不需要處理 lock。
- 兩邊只透過 thread-safe 的 `queue.Queue` 交換事件，**不要跨執行緒直接呼叫對方的方法或改對方的資料**。

## 機密資訊（[ADR 0005](decisions/0005-secret-information.md)）

答案、提示、間諜身分、未公開的畫作都屬於機密，只能**單播**給需要的人，詳見 [protocol.md](protocol.md)。
