# Core B scope audit — R2 / foundation guard

Status: PROPOSED scope classification, not a new ADR or an approval.
Baseline: `eaac1d8a3a5a5aebc5f31b7adb5a0b066f981ac4` (PR #5); main `bdaea5bc5744133c480e100d0362320d628d61f6`.
Authority: [leader review](https://github.com/NTUST-ICN-G7/Pretend2Paint/pull/5#issuecomment-7080008547), [ADR 0007 authorization](https://github.com/NTUST-ICN-G7/Pretend2Paint/pull/5#issuecomment-7080128245), [game rules](../../../../docs/game-rules.md), [ADR 0007](../../../../docs/decisions/0007-in-process-referee.md). PR #14 / ADR 0008 is still a proposal.

## Scope classification

| API / file | Classification | Next action and owner |
| --- | --- | --- |
| rules.py: _players, Deal, deal_words, choose_spy without history | Foundation: roster validation, one spy, private per-player deal; no approved population range or role-weight policy | B: preserve existing imports and test independent player views; A: enforce sender/recipient routing |
| words.py: WordCard, WordBank.from_records/draw | Foundation infrastructure; exhaustion/last_answer API already agreed by A+B, single-card edge remains documented | B: retain behavior; legacy from_json/default are I/O adapters and should not be invoked by runtime Core |
| rules.py: shuffle_gallery, resolve_blind_pick | Foundation: original manual blind reference selection | B: preserve index mapping; A supplies only civilian drawings and sends reference privately |
| rules.py: complete_drawings | Reusable helper, but deadline/blank-submission policy needs A/B confirmation | Keep separate from timing/phase policy |
| rules.py: normalize_guess/is_correct_guess | Foundation exact-answer/guess functionality; normalization and aliases are implementation choices, not new game rules | Preserve existing API and distinguish match mechanics from policy |
| rules.py: choose_spy(history), random_pick_index | Candidate: weighted selection and automatic reference replace original manual choice | B: isolate before production adoption; retain tests and historical commit |
| rules.py: valid_vote_targets/validate_votes/resolve_vote/score_round | Mixed: tallying and ordinary vote processing are foundation, but self/marked exclusions, spy vote exclusion, ties/abstention and numeric scoring encode unapproved policy | B+A: separate pure count/validation primitives from policy; no silent changes to existing public calls |
| rules.py: apply_scores, ranking, rank_with_ties, winners | Generic score arithmetic and ordering; tie places, winners and excluded participants are candidate policy | B: preserve generic arithmetic, obtain policy agreement before formal ranking acceptance |
| types.py: Role, RuleError | Foundation: shared Role re-export already migrated | Keep identity and import compatibility |
| types.py: Phase, RoundStatus, VoteStatus | Mixed/candidate: independent uppercase Phase, REVIEW and altered REVEAL ordering; VOID and tie status semantics | B+A+leader: align with common Phase only after separating dependent candidate code; no changes to common in this unit |
| config.py: GameConfig, ScoreRules, default_phase_seconds | Candidate: 4–7, five rounds, timing, weights, moderation and scoring defaults | B: isolate without changing values or claiming approval |
| anonymity.py | Candidate anonymous voting/review; general secrecy is mandatory but anonymity policy is not approved | B: preserve private maps/tests; do not expose author data or broaden reveal exceptions |
| moderation.py | Candidate REVIEW, quota, penalties, suspension, removal | B: isolate; ReviewPlan API requires A+B and rule approval |
| rounds.py | Candidate settlement/VOID_REFERENCE_VIOLATION coupled to moderation; counter consistency is a general invariant | B: preserve tests; A owns commit point, stale-event rejection; VOID_DISCONNECT is not implemented here |
| part_b/__init__.py, core/README.md, part_b_docs, examples, tests/core/test_part_b_* | Public exports, documentation, demonstrations and tests mix scope | B: retain old candidate snapshot and tests; audit callers before moving symbols; update stale labels and documents with the split |

The label "Settled" in historical OPEN_DECISIONS.md is not leader approval. README and PR #5 body contain historical CI/ADR status. The current formal CI and ADR authorization supersede those historical claims. Core AGENTS.md still references superseded ADR 0003; notify leader, do not edit agent settings.

## Foundation acceptance guard

New test file `tests/core/test_part_b_foundation_invariants.py` checks finite roster permutations, role-specific noninterference under changes to answer/hint, exact existing Deal serialization shape, fresh output ownership, blind index resolution, and RNG preservation for invalid rosters. Four fixture participants do not establish an approved player-count policy. The Deal shape is a local Core B object contract, **not** an approved DEAL_WORD wire schema.

References: boardgame.io [player view filter](https://github.com/boardgameio/boardgame.io/blob/main/src/master/filter-player-view.ts); OpenSpiel [State interface](https://github.com/google-deepmind/open_spiel/blob/master/open_spiel/spiel.h); Hypothesis [stateful tests](https://hypothesis.readthedocs.io/en/latest/stateful.html). These are design references only; no imported code or dependencies.

Issue #11 [acceptance draft](https://github.com/NTUST-ICN-G7/Pretend2Paint/issues/11#issuecomment-7212596774): 02-01 local role assignment, 02-03/02-04 local per-recipient data only, 04-01 local manual blind selection only (not the candidate automatic-selection behavior). Sender/recipient enforcement, phase, real transport and UI remain NOT TESTED; no assertion of full story coverage. CI evidence must be attached to the exact new HEAD separately.

## Safe split gate

1. Retain the current candidate commit and all candidate tests, before any removal from PR #5.
2. Inventory public exports and A's callers against the approved rules; obtain agreement before changing public behavior or candidate package paths.
3. Separate foundation and candidate-only policies in small commits; preserve compatible foundation imports and candidate history/tests.
4. Do not touch common/protocol/CI/agent configuration or other owners' implementation. Validate on a draft branch targeting PR #5, then exact-head CI and guarded fast-forward only after scope review.
5. No production code or policy has been changed by this audit. This is not end-to-end readiness.
