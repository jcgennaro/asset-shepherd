# Asset Shepherd Project Status

**Last updated:** 2026-08-21
**Current commit:** ac10f6bb1ff12837bf45c0a5fcdd8ac99b9db5bf
**Current milestone:** M4
**Overall state:** IN_PROGRESS

## Milestones

| Milestone | State | Evidence | Commit | Notes |
|---|---|---|---|---|
| M0 Repository bootstrap | COMPLETE | pytest, Ruff, format, Pyright, lock check | 112b649d52009ffa544f7787fb4c0d59efc39272 | Baseline |
| M1 Project control docs | COMPLETE | Common quality gate passed; control files agree on direct-main workflow | e03b4b876a4f1a616da7e077d42620929816eee1 | Completed 2026-08-21 |
| M2 GLB capability spike | COMPLETE | Automated round trip preserves resources/counts and verifies transformed bounds independently | ac10f6bb1ff12837bf45c0a5fcdd8ac99b9db5bf | Completed 2026-08-21; D001 |
| M3 Schemas and fixtures | COMPLETE | Schemas validate; clean and broken robot artifacts regenerate byte-for-byte and independently reload | This commit | Completed 2026-08-21 |
| M4 Inspector | IN_PROGRESS |  |  |  |
| M5 Repair engine | NOT_STARTED |  |  |  |
| M6 Deterministic CLI MVP | NOT_STARTED |  |  | Mandatory checkpoint after completion |
| M7 Strands agent | NOT_STARTED |  |  | Mandatory checkpoint after completion |
| M8 Web product | NOT_STARTED |  |  |  |
| M9 AWS deployment | NOT_STARTED |  |  | Mandatory checkpoint after completion |
| M10 Evaluation | NOT_STARTED |  |  |  |
| M11 Docs and Builder posts | NOT_STARTED |  |  |  |
| M12 Release and submission | NOT_STARTED |  |  | Mandatory checkpoint before submission |

## Current gate

Implement the complete deterministic inspection contract and expose `inspection.json` through the CLI.

## Latest evidence

- Tests: `uv run pytest` — 7 passed, including schema and fixture acceptance.
- Lint: `uv run ruff check .` and `uv run ruff format --check .` — passed.
- Type checking: `uv run pyright` — 0 errors, 0 warnings, 0 informations.
- Demo command or URL: `uv run python -m asset_shepherd.fixtures` regenerates fixtures.
- Generated artifacts: 2 original GLBs, 2 expected-defect manifests, 1 profile, and 10 JSON schemas.

## Blockers

None.

## Next action

Complete the M4 inspector, findings, eligibility, deterministic report, and inspect CLI.
