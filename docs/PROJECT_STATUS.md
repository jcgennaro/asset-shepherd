# Asset Shepherd Project Status

**Last updated:** 2026-08-21
**Current commit:** M8 progressive-disclosure UX refinement (this file is included)
**Current milestone:** RW2 Minimum Asset Flock / M8 concept review / M9 AWS setup
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
| M8 Web product | COMPLETE | Role-first chooser; two-area intake; three-area decision/result states; shared real Strands interrupt/resume; dual GLB preview; verification/download | 4459b7b70ff46aa05f6b28e43c44e2300875c6ef | D006, D008, and D010; progressive-disclosure refinement included in current commit |
| M9 AWS deployment | NOT_STARTED |  |  | Mandatory checkpoint after completion |
| M10 Evaluation | IN_PROGRESS | `docs/REAL_WORLD_VALIDATION_PLAN.md`; typed corpus and evidence harness | 085545efdda09aa3a77aa115ce521ab4dfecb3b0 | RW0–RW5 addendum controls real-world evaluation and demo-asset evidence |
| M11 Docs and Builder posts | NOT_STARTED |  |  |  |
| M12 Release and submission | NOT_STARTED |  |  | Mandatory checkpoint before submission |

## Real-world validation milestones

| Milestone | State | Evidence | Notes |
|---|---|---|---|
| RW0 Adopt and scaffold | COMPLETE | Canonical addendum; typed schemas; ignored corpus; generation card; registration, mutation, Blender, Unreal, and report tooling | 085545efdda09aa3a77aa115ce521ab4dfecb3b0; D003; no product behavior change |
| RW1 Patchling blind baseline | COMPLETE | Registered untouched raw hash; frozen inspect/plan/repair/verify/package; Blender raw/repaired evidence; turntable views; human rights and visual adjudication | D004 and D005; zero unsafe repairs or visual/resource regressions |
| RW2 Minimum Asset Flock | IN_PROGRESS | Patchling and Shader Lantern registered; Lantern inspection/plan frozen at approval | D009; two more untouched assets still required; Lantern human size decision pending |
| RW3 Controlled realistic variants | SCAFFOLDED | Repeatable normalization, hierarchy, and material/texture mutation code; fixture dry runs | Real variants wait for registered corpus assets |
| RW4 Blender and Unreal acceptance | SCAFFOLDED | Blender 5.1.2 import/re-export evidence; Unreal 5.8 isolated map and three-arm fixture import | Real comparison and visual checkpoint wait for corpus/human reference |
| RW5 Evaluation report and demo | SCAFFOLDED | Typed adjudication and traceable case-study report renderer | Public claims remain prohibited until evidence exists |

## Current gate

M8 is complete and now begins with one role question, then progressively reveals upload, decision,
result, preview, and technical evidence. Each route completes the same real Strands loop and exact
result package, with an enforced maximum of three primary focus areas in every rendered state.
Shader Lantern is the second registered real-world input; its blind prediction remains frozen at the
physical-size approval before any visual diagnosis. RW2 still needs Debug Beetle and Cloudforge
Workbench. M9 requires user-owned AWS profile, model access, region, and cost-control setup before
any paid invocation or resource creation.

## Latest evidence

- Tests: `uv run pytest` — 48 passed and the opt-in live-provider test skipped; story web gate —
  7 passed.
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
- Patchling's rights-confirmed 4.86 MB raw GLB is the first tracked real-world demo input. D007 keeps
  generated results ignored and preserves the registered SHA-256 as the reproducibility anchor.
- The one-batch Shader Lantern card freezes the exact contracted prompt, 3-candidate request,
  untouched GLB/4K export settings, destination path, and transparency/emissive selection criteria.
- Web acceptance: broken-fixture refresh/approve/resume/download; clean no-approval completion twice
  from independent app starts; invalid upload rejection; unsupported inspection-only packaging;
  exact ZIP audit; source preservation; trusted profile selection; 50 MB and GLB magic boundaries.
- Chrome review: desktop and 390 × 844 responsive layouts passed; synthetic before/after difference
  is immediately visible; Patchling textured raw/repaired previews match; no console warnings or
  errors. The packaged wheel includes templates, CSS, JavaScript, and the local favicon.
- Progressive-disclosure web evidence: `/` starts with `Which best describes you?` and three concise
  role choices. Each intake has two primary focus areas; pending, blocked, and completed jobs have
  three. Tests enforce that budget while each role still runs the exact seven-file approval workflow.
  Desktop and 390 × 844 review passed with no horizontal overflow; the completed result keeps the
  download and before/after preview visible while technical evidence is collapsed. No application
  console errors or warnings were observed.
- Distribution audit: `uv build --wheel` succeeded and the wheel contains all three story templates,
  both shared partials, the job/chooser/base templates, CSS, JavaScript, and favicon.
- Shader Lantern evidence: raw SHA-256
  `be2c9cab8d4e51f7a948c7c54db7a10c932f24faf69bc3166ff724ccc00c49b9`; 77,545 vertices;
  101,564 triangles; one material; three readable embedded 4096² base-color,
  roughness/metallic, and normal images; 99.908905 m represented height; grounded and Y-up; no rig,
  animation, morph target, negative scale, or non-uniform scale.
- Shader Lantern's frozen plan has two safe display-name repairs, a report-only 1,564-triangle
  overage, and a pending reversible 0.0120109414× scale proposal to 1.2 m. No repair, verification,
  DCC import, or visual diagnosis has occurred before the user decision.
- Generated fixture evidence stays below ignored `build/validation/`; only reproducible scripts,
  schemas, templates, and typed records are committed.

## Blockers

Shader Lantern requires the user to approve or reject `normalize-root-v1`: its source represents a
99.908905 m height and the selected profile proposes 1.2 m, but intended prop size is not otherwise
known. RW2 also requires untouched Debug Beetle and Cloudforge Workbench exports. M9 requires the
user to configure or confirm a dedicated `asset-shepherd` AWS profile, selected Bedrock region/model
access, and a budget alert before paid calls. Read-only preflight found that AWS CLI is not installed
on this workstation (`Get-Command aws` returned no command). Unreal comparison and a human-cleaned
reference remain future RW4 work.

## Next action

The user reviews the simplified role-first M8 experience and approves or rejects Shader Lantern's
exact `normalize-root-v1` proposal. After that decision, freeze the complete Lantern package before
Blender/Unreal diagnosis and continue RW2 with one Debug Beetle generation card. Before M9 paid
provider work, confirm the dedicated AWS profile, Bedrock model/region access, and budget alert.
