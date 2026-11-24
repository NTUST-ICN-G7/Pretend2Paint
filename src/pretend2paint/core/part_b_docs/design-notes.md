# Part B historical design notes / Part B 歷史設計說明

The following records describe earlier proposals. The original files remain available in Git history. The numbered copies were consolidated here because their identifiers overlapped with the team's decision index.

以下為先前候選提案的歷史摘要。原始內容保留於 Git 歷史；舊編號與小組決策索引重複，因此整併於本文件。

| Historical record / 歷史紀錄 | Topics / 主題 | Review outcome / 審查狀態 |
| --- | --- | --- |
| [Earlier rules contract](https://github.com/NTUST-ICN-G7/Pretend2Paint/blob/3aa84e2f4c678faa2786753654b1930f3708beea/src/pretend2paint/core/part_b_docs/adr/0006-game-rules-contract.md) | Rule functions, random assignment, voting and scoring | Earlier host-only design superseded; candidate rule details pending |
| [Earlier referee and timeouts](https://github.com/NTUST-ICN-G7/Pretend2Paint/blob/3aa84e2f4c678faa2786753654b1930f3708beea/src/pretend2paint/core/part_b_docs/adr/0007-headless-referee-and-timeouts.md) | All humans playing, referee process and deadlines | Separate-process proposal rejected; deadline details pending |
| [Review and void proposal](https://github.com/NTUST-ICN-G7/Pretend2Paint/blob/3aa84e2f4c678faa2786753654b1930f3708beea/src/pretend2paint/core/part_b_docs/adr/0008-void-reference-review-and-anonymity.md) | Automatic reference selection, anonymous voting, review, penalties and void attempts | Implemented in candidate; team approval pending |

## Architecture review result / 架構審查結果

The review dated 2026-11-22 accepted participation by every human and an automatic referee component inside the room creator's game process. It rejected a separate referee process or non-player node.

2026-11-22 審查接受所有真人共同參賽，裁判為開房者程式內的自動元件，不另外執行獨立程序或建立非玩家節點。

Sources: [PR #5 review](https://github.com/NTUST-ICN-G7/Pretend2Paint/pull/5#issuecomment-7080008547), [ADR clarification](https://github.com/NTUST-ICN-G7/Pretend2Paint/pull/5#issuecomment-7080128245), [ADR 0007](../../../../docs/decisions/0007-in-process-referee.md).

## Open questions / 尚待討論

The candidate's automatic reference selection, REVIEW, VOID, discipline, civilian-only voting, weighting, scoring, tie handling, player counts and round counts remain unresolved in the cited team review.

依上述審查，候選版自動選圖、審查、作廢、違規處置、僅一般玩家投票、加權、計分、平票、人數及回合數仍未定案。
