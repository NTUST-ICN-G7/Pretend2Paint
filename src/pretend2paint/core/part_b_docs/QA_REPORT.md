# Part B v1.2.0 QA Report / v1.2.0 規則模組驗收報告

**Test date / 測試日期:** 2026-11-22 (Asia/Taipei). **Environment:** CPython 3.13.5, Python package source requires 3.10+. **Runtime dependencies:** Python standard library only. `pytest` is needed only to execute tests.

**測試日期：** 2026-11-22（台灣）。**實際環境：** CPython 3.13.5，原始碼標示支援 Python 3.10+。**執行時依賴：** 僅 Python 標準函式庫，執行測試才需要 `pytest`。

## Verification matrix / 驗收矩陣

| Check / 檢查 | Status / 結果 | Evidence / 證據 |
|---|---|---|
| Source generation / 程式生成 | PASS | `core/`, `examples/`, `tests/`, `docs/`, `pyproject.toml` exist / 檔案存在 |
| Syntax / 語法 | PASS | `python -m compileall` / 編譯可讀 |
| Unit & regression tests / 單元與回歸 | **PASS 145/145** | `python -m pytest -q` / 145 passed |
| Void-round demonstration / 作廢回合示範 | **PASS** | `python -m examples.rules_demo` / attempt #1 VOID, #2/#3 SCORED, completed=2/2 |
| Violation penalty on VOID / 作廢保留處罰 | PASS | Attempt #1: violating civilian -15, normal score 0 / 第一局作者 −15、正常分 0 |
| No consumed completed round / 不消耗回合 | PASS | 3 attempts -> 2 completed / 三次開局、兩次有效 |
| Role history on VOID / 作廢不增加間諜歷史 | PASS | `tests/test_v120.py` status and history assertions / 歷史斷言 |
| Review quotas / 審查額度 | PASS | 4/5=1, 6/7=2; duplicate/over-quota rejected / 超額拒絕 |
| Review penalties & suspension / 審查者處罰 | PASS | Failure streak 3/4, deferred suspension, remove-on-second-violation / 失敗連續紀錄、暫停與二次移出 |
| Confidential identity map / 私密身分映射 | PASS (pure API) | public labels detached from private ID map / 公開資料不含作者 ID |
| Tie, no vote, self-vote and spy ballots / 平票與違規選票 | PASS | Rejected invalid ballots; neutral tie guess / 無效票拒絕、平票中性 |
| Public ties in leaderboard / 並列排名 | PASS | `rank_with_ties`, `winners` / 可並列 |
| Built wheel / Wheel 建置 | PASS | `python -m pip wheel --no-deps --no-build-isolation . -w dist` |
| Isolated wheel installation / 隔離安裝 | PASS | local `pip --no-index --target work/final_install`; import public API; read 59-card bank |
| Actual Socket server / 真正 Socket 伺服器 | **NOT TESTED** | Belongs to Part A / Streaming / A 與串流組 |
| UI and image editing / UI 與畫布 | **NOT TESTED** | Not included / 未納入本版 |
| End-to-end reconnection / 斷線重連 | **NOT TESTED** | Only documented host policy / 僅文件說明 |
| 3.10/3.11 execution / Python 3.10/3.11 執行 | **NOT TESTED** | Executed in Python 3.13 / 僅 3.13 實測 |
| Automatic handwriting detection / 自動文字辨識 | **UNSUPPORTED** | Review is human votes / 由玩家審查 |
| Offline collusion prevention / 場外串通防治 | **UNSUPPORTED** | Out of software's scope / 無法完全避免 |
| Actual user download / 使用者端實際下載 | **NOT TESTED** | User must check / 需使用者確認 |

## Actual demo output / 實際示範摘要

```text
Attempt=1, status=VOID_REFERENCE_VIOLATION, completed=0/2,
  reference=eric, delta={'alice': 0, 'bob': 0, 'cathy': 0, 'david': 0, 'eric': -15}
Attempt=2, status=SCORED, completed=1/2,
  reference=david, delta={'alice': 8, 'bob': 8, 'cathy': 8, 'david': 8, 'eric': 1}
Attempt=3, status=SCORED, completed=2/2,
  reference=bob, delta={'alice': -3, 'bob': 11, 'cathy': 11, 'david': 11, 'eric': 11}
Final board: {'alice': 5, 'bob': 19, 'cathy': 19, 'david': 19, 'eric': -3}
PASS: exactly two scored rounds despite three attempts
```

## Important boundaries / 重要限制

The supplied teammate `README.pdf` was a draft and its old flow assumptions (human host, manual spy pick, spy vote, early reveal, old scoring) were superseded by user decisions. Part B therefore includes intentionally breaking semantic changes from v1.1. Part A must align its Phase/Event/Effect/Packet integration with the documented new contract; the tests cannot establish real multi-machine network behavior.

組員的 `README.pdf` 是草稿，其中真人房主、間諜手動盲選、間諜投票、投票前公開以及舊分數等假設已由使用者新決定取代。因此 B 對 v1.1 有刻意不相容的語意調整；A 模組的 Phase／Event／Effect／Packet 必須依新整合文件修改。這些測試不能證明真實跨電腦網路通訊已通過。

The source archive and wheel checksums are reported separately in `WhoIsUndercoverDrawing_PartB_v1.2.0_SHA256SUMS.txt`. A dedicated ChatGPT Library save, if performed, is verified separately from the Python tests and must not be inferred from this report.

原始碼 ZIP 與 Wheel 的雜湊列在獨立的 SHA-256 檔案；ChatGPT Library 保存若執行，需另外查驗，不可僅從本報告推論成功。

No previous version's source or Library files were overwritten or deleted. / 未覆寫或刪除先前版本的原始碼或 Library 檔案。
