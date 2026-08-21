# Asset Shepherd Project Status

**Last updated:** 2026-08-21
**Current commit:** e03b4b876a4f1a616da7e077d42620929816eee1
**Current milestone:** M3
**Overall state:** IN_PROGRESS

## Milestones

| Milestone | State | Evidence | Commit | Notes |
|---|---|---|---|---|
| M0 Repository bootstrap | COMPLETE | pytest, Ruff, format, Pyright, lock check | 112b649d52009ffa544f7787fb4c0d59efc39272 | Baseline |
| M1 Project control docs | COMPLETE | Common quality gate passed; control files agree on direct-main workflow | e03b4b876a4f1a616da7e077d42620929816eee1 | Completed 2026-08-21 |
| M2 GLB capability spike | COMPLETE | Automated round trip preserves resources/counts and verifies transformed bounds independently | This commit | Completed 2026-08-21; D001 |
| M3 Schemas and fixtures | IN_PROGRESS |  |  |  |
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

Implement versioned typed schemas and reproducible clean/broken robot fixtures with expected-defect manifests.

## Latest evidence

- Tests: `uv run pytest` — 2 passed, including the M2 GLB round-trip spike.
- Lint: `uv run ruff check .` and `uv run ruff format --check .` — passed.
- Type checking: `uv run pyright` — 0 errors, 0 warnings, 0 informations.
- Demo command or URL: M2 proof runs through `uv run pytest tests/spike/test_glb_capability.py`.
- Generated artifacts: Temporary GLBs created and independently reloaded by the spike test.

## Blockers

None.

## Next action

Complete M3 typed schemas, deterministic robot fixtures, manifests, and profile.
