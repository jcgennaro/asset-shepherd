# Asset Shepherd Project Status

**Last updated:** 2026-08-21
**Current commit:** 112b649d52009ffa544f7787fb4c0d59efc39272
**Current milestone:** M2
**Overall state:** IN_PROGRESS

## Milestones

| Milestone | State | Evidence | Commit | Notes |
|---|---|---|---|---|
| M0 Repository bootstrap | COMPLETE | pytest, Ruff, format, Pyright, lock check | 112b649d52009ffa544f7787fb4c0d59efc39272 | Baseline |
| M1 Project control docs | COMPLETE | Common quality gate passed; control files agree on direct-main workflow | This commit | Completed 2026-08-21 |
| M2 GLB capability spike | IN_PROGRESS |  |  |  |
| M3 Schemas and fixtures | NOT_STARTED |  |  |  |
| M4 Inspector | NOT_STARTED |  |  |  |
| M5 Repair engine | NOT_STARTED |  |  |  |
| M6 Deterministic CLI MVP | NOT_STARTED |  |  | Mandatory checkpoint after completion |
| M7 Strands agent | NOT_STARTED |  |  | Mandatory checkpoint after completion |
| M8 Web product | NOT_STARTED |  |  |  |
| M9 AWS deployment | NOT_STARTED |  |  | Mandatory checkpoint after completion |
| M10 Evaluation | NOT_STARTED |  |  |  |
| M11 Docs and Builder posts | NOT_STARTED |  |  |  |
| M12 Release and submission | NOT_STARTED |  |  | Mandatory checkpoint before submission |

## Current gate

Prove the selected lightweight GLB stack can load, traverse, transform, rename, save, reload, and validate without Blender.

## Latest evidence

- Tests: `uv run pytest` — 1 passed.
- Lint: `uv run ruff check .` and `uv run ruff format --check .` — passed.
- Type checking: `uv run pyright` — 0 errors, 0 warnings, 0 informations.
- Demo command or URL: Not applicable for M1.
- Generated artifacts: Project control documents.

## Blockers

None.

## Next action

Complete the M2 GLB capability spike and record the architecture decision.
