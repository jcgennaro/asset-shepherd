# Asset Shepherd Project Status

**Last updated:** 2026-08-21
**Current commit:** M8 completion commit (this file is included)
**Current milestone:** RW2 Minimum Asset Flock / M9 AWS setup
**Overall state:** HUMAN_ACTION_REQUIRED

## Milestones

| Milestone | State | Evidence | Commit | Notes |
|---|---|---|---|---|
| M0 Repository bootstrap | COMPLETE | pytest, Ruff, format, Pyright, lock check | 112b649d52009ffa544f7787fb4c0d59efc39272 | Baseline |
| M1 Project control docs | COMPLETE | Common quality gate passed; control files agree on direct-main workflow | e03b4b876a4f1a616da7e077d42620929816eee1 | Completed 2026-08-21 |
| M2 GLB capability spike | COMPLETE | Automated round trip preserves resources/counts and verifies transformed bounds independently | ac10f6bb1ff12837bf45c0a5fcdd8ac99b9db5bf | Completed 2026-08-21; D001 |
| M3 Schemas and fixtures | COMPLETE | Schemas validate; clean and broken robot artifacts regenerate byte-for-byte and independently reload | 444a99877a01694020209d22dab831660c84a47e | Completed 2026-08-21 |
| M4 Inspector | COMPLETE | Broken fixture yields all 10 expected defects; clean has no false severe/auto-safe findings; deterministic CLI artifacts | 4f7434b6ba58127d38e35f793db8ed27fddd3331 | Completed 2026-08-21 |
| M5 Repair engine | COMPLETE | Registered plan, strict authorization, approve/reject paths, stable counts/references, source preservation, idempotence | 27781e2d8afb185171a29982d3cad173e55fe90d | Completed 2026-08-21 |
| M6 Deterministic CLI MVP | COMPLETE | Happy, rejected, and clean-control runs; schema/ZIP audit; Blender 5.1.2 import; full gate | a077077ca94c44b9693893672a7208d84d1f05b8 | Completed and checkpoint-reviewed 2026-08-21 |
| M7 Strands agent | COMPLETE | Real Strands loop; native interrupt/resume; approve/reject; bounded correction; metrics; offline and opt-in live tests | 02876da55e2dd0bee3dfbe80bd01cd50f87ba76d | Completed 2026-08-21; D002; mandatory checkpoint 2 reviewed by the addendum instruction |
| M8 Web product | COMPLETE | FastAPI/Jinja local product; real Strands interrupt/resume; dual GLB preview; verification/download; browser and automated acceptance | M8 completion commit (this file is included) | D006 |
| M9 AWS deployment | NOT_STARTED |  |  | Mandatory checkpoint after completion |
| M10 Evaluation | IN_PROGRESS | `docs/REAL_WORLD_VALIDATION_PLAN.md`; typed corpus and evidence harness | 085545efdda09aa3a77aa115ce521ab4dfecb3b0 | RW0–RW5 addendum controls real-world evaluation and demo-asset evidence |
| M11 Docs and Builder posts | NOT_STARTED |  |  |  |
| M12 Release and submission | NOT_STARTED |  |  | Mandatory checkpoint before submission |

## Real-world validation milestones

| Milestone | State | Evidence | Notes |
|---|---|---|---|
| RW0 Adopt and scaffold | COMPLETE | Canonical addendum; typed schemas; ignored corpus; generation card; registration, mutation, Blender, Unreal, and report tooling | 085545efdda09aa3a77aa115ce521ab4dfecb3b0; D003; no product behavior change |
| RW1 Patchling blind baseline | COMPLETE | Registered untouched raw hash; frozen inspect/plan/repair/verify/package; Blender raw/repaired evidence; turntable views; human rights and visual adjudication | D004 and D005; zero unsafe repairs or visual/resource regressions |
| RW2 Minimum Asset Flock | HUMAN_ACTION_REQUIRED | Shader Lantern generation card and typed drafts | Patchling remains the hero/preservation case; richer PBR coverage moves to the corpus |
| RW3 Controlled realistic variants | SCAFFOLDED | Repeatable normalization, hierarchy, and material/texture mutation code; fixture dry runs | Real variants wait for registered corpus assets |
| RW4 Blender and Unreal acceptance | SCAFFOLDED | Blender 5.1.2 import/re-export evidence; Unreal 5.8 isolated map and three-arm fixture import | Real comparison and visual checkpoint wait for corpus/human reference |
| RW5 Evaluation report and demo | SCAFFOLDED | Typed adjudication and traceable case-study report renderer | Public claims remain prohibited until evidence exists |

## Current gate

M8 is complete. One local command starts a coherent profile-select/upload/findings/approval/
repair/verify/preview/download product over the real Strands loop. Refresh preserves an in-process
pending interrupt, unsupported assets package safe diagnostics, and invalid uploads fail before a job
is retained. RW2 still needs an untouched Shader Lantern export. M9 requires user-owned AWS profile,
model access, region, and cost-control setup before any paid invocation or resource creation.

## Latest evidence

- Tests: `uv run pytest` — 45 passed and the opt-in live-provider test skipped.
- Lint: `uv run ruff check .` and `uv run ruff format --check .` — passed.
- Type checking: `uv run pyright` — 0 errors, 0 warnings, 0 informations.
- Local-consumer evidence: Blender 5.1.2 imported and re-exported the clean fixture with its source
  hash unchanged; Unreal 5.8 generated the isolated comparison map and imported three isolated arms
  with 15 static meshes and 4 materials each.
- Patchling evidence: raw SHA-256 `dc2f03ae8ed368f46c2a4ac9e2ebb71f23e980b0c9e6913c685d011e273f418d`;
  26,135 vertices; 18,727 triangles; one packed 4096² base-color image; 0.998 m height; no rig,
  animation, morph, negative scale, or grounding issue. Name-only repair verifies project-ready.
- Blender imports Patchling raw and repaired outputs with identical bounds, geometry, material, and
  packed-image counts and no missing image.
- Provenance registration passed with identical before/after raw hashes. The user confirmed paid
  Tripo commercial rights; Smart Mesh P1.0/Fast, 25k quad target, workspace item ID, and the GLB/4K
  export panel values are recorded.
- Patchling is accepted as the visual hero and preservation case. Its one-material limitation is
  disclosed and is not treated as an in-scope repair; D005 assigns richer PBR coverage to RW2.
- The one-batch Shader Lantern card freezes the exact contracted prompt, 3-candidate request,
  untouched GLB/4K export settings, destination path, and transparency/emissive selection criteria.
- Web acceptance: broken-fixture refresh/approve/resume/download; clean no-approval completion twice
  from independent app starts; invalid upload rejection; unsupported inspection-only packaging;
  exact ZIP audit; source preservation; trusted profile selection; 50 MB and GLB magic boundaries.
- Chrome review: desktop and 390 × 844 responsive layouts passed; synthetic before/after difference
  is immediately visible; Patchling textured raw/repaired previews match; no console warnings or
  errors. The packaged wheel includes templates, CSS, JavaScript, and the local favicon.
- Generated fixture evidence stays below ignored `build/validation/`; only reproducible scripts,
  schemas, templates, and typed records are committed.

## Blockers

RW2 requires the user to generate and hand off an untouched Shader Lantern GLB. M9 requires the user
to configure or confirm a dedicated `asset-shepherd` AWS profile, selected Bedrock region/model
access, and a budget alert before paid calls. Unreal comparison and a human-cleaned reference remain
future RW4 work.

## Next action

The user generates the Shader Lantern batch and places the selected untouched GLB at
`validation/corpus/shader_lantern_01/raw/asset.glb`. Before M9 paid-provider work, confirm the
dedicated AWS profile, Bedrock model/region access, and budget alert. Preserve Patchling as the
immutable registered baseline.
