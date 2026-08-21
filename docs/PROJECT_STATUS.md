# Asset Shepherd Project Status

**Last updated:** 2026-08-21
**Current commit:** 27781e2d8afb185171a29982d3cad173e55fe90d
**Current milestone:** M6 mandatory checkpoint
**Overall state:** CHECKPOINT

## Milestones

| Milestone | State | Evidence | Commit | Notes |
|---|---|---|---|---|
| M0 Repository bootstrap | COMPLETE | pytest, Ruff, format, Pyright, lock check | 112b649d52009ffa544f7787fb4c0d59efc39272 | Baseline |
| M1 Project control docs | COMPLETE | Common quality gate passed; control files agree on direct-main workflow | e03b4b876a4f1a616da7e077d42620929816eee1 | Completed 2026-08-21 |
| M2 GLB capability spike | COMPLETE | Automated round trip preserves resources/counts and verifies transformed bounds independently | ac10f6bb1ff12837bf45c0a5fcdd8ac99b9db5bf | Completed 2026-08-21; D001 |
| M3 Schemas and fixtures | COMPLETE | Schemas validate; clean and broken robot artifacts regenerate byte-for-byte and independently reload | 444a99877a01694020209d22dab831660c84a47e | Completed 2026-08-21 |
| M4 Inspector | COMPLETE | Broken fixture yields all 10 expected defects; clean has no false severe/auto-safe findings; deterministic CLI artifacts | 4f7434b6ba58127d38e35f793db8ed27fddd3331 | Completed 2026-08-21 |
| M5 Repair engine | COMPLETE | Registered plan, strict authorization, approve/reject paths, stable counts/references, source preservation, idempotence | 27781e2d8afb185171a29982d3cad173e55fe90d | Completed 2026-08-21 |
| M6 Deterministic CLI MVP | COMPLETE | One command produces the exact seven-file ZIP; 16 verification checks pass; second plan empty | This commit | Completed 2026-08-21; mandatory checkpoint 1 |
| M7 Strands agent | NOT_STARTED |  |  | Mandatory checkpoint after completion |
| M8 Web product | NOT_STARTED |  |  |  |
| M9 AWS deployment | NOT_STARTED |  |  | Mandatory checkpoint after completion |
| M10 Evaluation | NOT_STARTED |  |  |  |
| M11 Docs and Builder posts | NOT_STARTED |  |  |  |
| M12 Release and submission | NOT_STARTED |  |  | Mandatory checkpoint before submission |

## Current gate

Mandatory checkpoint 1: review the completed deterministic CLI before any Strands agent code is added.

## Latest evidence

- Tests: `uv run pytest` — 23 passed, including approve, reject, blocked, tamper-failure, deterministic ZIP, and full CLI paths.
- Lint: `uv run ruff check .` and `uv run ruff format --check .` — passed.
- Type checking: `uv run pyright` — 0 errors, 0 warnings, 0 informations.
- Demo command or URL: `uv run asset-shepherd run fixtures/broken_robot.glb --profile profiles/unreal_indie_robot.json --approvals examples/approve_normalization.json --output demo-output`.
- Generated artifacts: `repaired.glb`, `inspection.json`, `repair_plan.json`, `decisions.json`, `verification.json`, `provenance.json`, `report.md`, and `result.zip`.

## Blockers

None.

## Next action

Stop at mandatory checkpoint 1. After review, begin M7 local Strands agent work.
