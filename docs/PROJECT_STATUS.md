# Asset Shepherd Project Status

**Last updated:** 2026-08-21
**Current commit:** b129fdce8548a8a0569af693305c83be39c1541f
**Current milestone:** M7 Strands agent
**Overall state:** IN_PROGRESS

## Milestones

| Milestone | State | Evidence | Commit | Notes |
|---|---|---|---|---|
| M0 Repository bootstrap | COMPLETE | pytest, Ruff, format, Pyright, lock check | 112b649d52009ffa544f7787fb4c0d59efc39272 | Baseline |
| M1 Project control docs | COMPLETE | Common quality gate passed; control files agree on direct-main workflow | e03b4b876a4f1a616da7e077d42620929816eee1 | Completed 2026-08-21 |
| M2 GLB capability spike | COMPLETE | Automated round trip preserves resources/counts and verifies transformed bounds independently | ac10f6bb1ff12837bf45c0a5fcdd8ac99b9db5bf | Completed 2026-08-21; D001 |
| M3 Schemas and fixtures | COMPLETE | Schemas validate; clean and broken robot artifacts regenerate byte-for-byte and independently reload | 444a99877a01694020209d22dab831660c84a47e | Completed 2026-08-21 |
| M4 Inspector | COMPLETE | Broken fixture yields all 10 expected defects; clean has no false severe/auto-safe findings; deterministic CLI artifacts | 4f7434b6ba58127d38e35f793db8ed27fddd3331 | Completed 2026-08-21 |
| M5 Repair engine | COMPLETE | Registered plan, strict authorization, approve/reject paths, stable counts/references, source preservation, idempotence | 27781e2d8afb185171a29982d3cad173e55fe90d | Completed 2026-08-21 |
| M6 Deterministic CLI MVP | COMPLETE | Happy, rejected, and clean-control runs; schema/ZIP audit; Blender 5.1.2 import; full gate | This commit | Completed and checkpoint-reviewed 2026-08-21 |
| M7 Strands agent | IN_PROGRESS |  |  | Mandatory checkpoint after completion |
| M8 Web product | NOT_STARTED |  |  |  |
| M9 AWS deployment | NOT_STARTED |  |  | Mandatory checkpoint after completion |
| M10 Evaluation | NOT_STARTED |  |  |  |
| M11 Docs and Builder posts | NOT_STARTED |  |  |  |
| M12 Release and submission | NOT_STARTED |  |  | Mandatory checkpoint before submission |

## Current gate

Complete the local Strands workflow with typed deterministic tools, structured plan selection, a
real approval interrupt/resume, approve and reject paths, bounded correction, metrics, an exact
deterministic package, offline unit tests, and an opt-in live integration test.

## Latest evidence

- Tests: `uv run pytest` — 24 passed, including explicit rejection, schema/ZIP audit, and
  byte-identical clean control.
- Lint: `uv run ruff check .` and `uv run ruff format --check .` — passed.
- Type checking: `uv run pyright` — 0 errors, 0 warnings, 0 informations.
- Demo command or URL: see `docs/checkpoints/deterministic-core.md` for exact approved, rejected,
  clean-control, package-audit, and Blender commands.
- Generated artifacts: `repaired.glb`, `inspection.json`, `repair_plan.json`, `decisions.json`, `verification.json`, `provenance.json`, `report.md`, and `result.zip`.

## Blockers

None.

## Next action

Commit the reviewed deterministic checkpoint, then implement M7 without beginning web or AWS work.
