# Part B v1.2.0 proposed integration — review notes

> **Draft for team review; not yet game-ready or merged.**

## Source

The v1.2.0 source is copied from the previously built and tested Part B ZIP, with its imports remapped to `pretend2paint.core.part_b`. No changes to the behavior of the Part B rule functions are intended.

## Decisions requiring team approval before merge

1. `docs/decisions/0003-host-authority.md` specifies a **human host** who holds all secrets. This Part B design assumes **all humans participate** and an automatic referee handles secrets. These must be reconciled by the team.
2. `docs/decisions/0005-secret-information.md` forbids showing images to civilians before `Phase.REVEAL`; Part B adds a **civilian review phase** with sequential access. Revise approved game/privacy rules before connecting this code.
3. `common.types.Phase` has lowercase wire values and no `REVIEW`. Part B's private `types.Phase` currently has uppercase values and therefore **must not be used as a substitute** for the shared contract.
4. The team docs specify manual blind picking and everyone voting; this proposal specifies automatic reference and civilian-only voting.
5. The team repository requires Python >=3.14 and uv; original Part B was independently tested as Python >=3.10 package and is not yet validated under project CI.

## Scope of this PR

Only `src/pretend2paint/core/` and `tests/core/` are changed. No `common/`, protocol, project configuration, or approved ADR is modified. No direct `main` commit.

## Validation

The standalone source was previously reported as passing 145 tests. Current branch-run evidence, if available, must be reviewed separately before approval. Real networking, UI, and referee integration is not part of this PR.

## Tests run in the proposed namespace

- Local Python: **3.13.5**.
- `PYTHONPATH=src python -m pytest --import-mode=importlib tests/core`: **145 passed**.
- `PYTHONPATH=src python -m pretend2paint.core.part_b.examples.rules_demo`: **PASS** (1 void, 2 completed).
- `python -m compileall -q`: **PASS**.
- Full team checks (`uv run ruff check`, `uv run ruff format --check`, `uv run lint-imports`, `uv run pytest` under Python 3.14): **NOT TESTED** in this environment, must be verified by CI.
- The archived QA report (`QA_REPORT.md`) covers the **standalone** package and does not certify this integration.
