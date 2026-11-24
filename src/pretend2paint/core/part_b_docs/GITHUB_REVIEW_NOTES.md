# Part B v1.2.0 — review status (2026-11-24)

This record describes the candidate library and observed review and CI status. It does not establish new game rules.

## Observed architecture decision

The team review on PR #5 records that all humans participate, including the room creator, and that the referee runs inside the room creator's game process on the background asyncio thread. The separate-process design was rejected. ADR 0007 records this decision in PR #5, which remains open.

Sources:
- [Architecture review](https://github.com/NTUST-ICN-G7/Pretend2Paint/pull/5#issuecomment-7080008547)
- [ADR scope clarification](https://github.com/NTUST-ICN-G7/Pretend2Paint/pull/5#issuecomment-7080128245)
- [ADR 0007](../../../../docs/decisions/0007-in-process-referee.md)

## Outstanding differences

| Topic | Existing team design | Candidate implementation |
| --- | --- | --- |
| Phase | Shared lowercase values; REVEAL precedes VOTING | Private uppercase values; REVIEW and later REVEAL |
| Role | Shared lowercase values | Private uppercase values |
| Reference | Manual blind pick | Automatic selection in candidate flow |
| Voting | All players vote | Civilian-only voting |
| Scoring | Spy score direction specified; civilian scores and ties pending | Configurable numeric scores and tie behavior |
| Round handling | Existing phase sequence | VOID, review penalties and suspension |
| Player and round counts | Further discussion | Four to seven players; five completed rounds by default |

The review also identifies duplicate numbered design documents under `part_b_docs/adr/`. Their consolidation and the reduction of the candidate code to agreed rules remain open. No gameplay proposal is resolved by this status record.

## Validation evidence

- Historical standalone source: Python 3.13.5; 145 tests passed; standalone demonstration and compilation passed. The original standalone QA report remains a historical record.
- Integrated repair baseline: `26dde8980182f849a36fec4c4228f7a70e81d875`.
- [PR #12 validation CI](https://github.com/NTUST-ICN-G7/Pretend2Paint/actions/runs/45324864364): success.
- [PR #5 CI after fast-forward integration](https://github.com/NTUST-ICN-G7/Pretend2Paint/actions/runs/45336991528): Ruff lint, Ruff format (85 files), layered imports, pytest (211 passed), and agent workspace checks succeeded.
- Real multiplayer integration: not tested by the recorded CI evidence.

The repair baseline includes the approved authority-model documents and CI fixes. No shared types, packet formats, or workflow settings were changed by the CI repair. PR #5 has not been merged into main.
