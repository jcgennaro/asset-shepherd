# Asset Shepherd Project Status

**Last updated:** 2026-08-22
**Current commit:** M8 intent-first target agreement and product inflection review (this file is included)
**Current milestone:** RW2 Minimum Asset Flock / M9 AWS setup / M10 evaluation
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
| M8 Web product | COMPLETE | Intent-first target-story agreement; frozen intent and policy provenance; two-column app frame; large-type disclosure-first presentation; single-visible-step Rules/Upload and Inspect/Decide/Download; Strands interrupt/resume; dual GLB preview; verification/download | e6b9046c86b96dc43f3f4e255f00e759f2d3d22e | D006–D018; D018 supersedes the primary role-selector modality; latest intent flow is included in current commit |
| M9 AWS deployment | NOT_STARTED |  |  | Mandatory checkpoint after completion |
| M10 Evaluation | IN_PROGRESS | `docs/REAL_WORLD_VALIDATION_PLAN.md`; typed corpus and evidence harness | 085545efdda09aa3a77aa115ce521ab4dfecb3b0 | RW0–RW5 addendum controls real-world evaluation and demo-asset evidence |
| M11 Docs and Builder posts | NOT_STARTED |  |  |  |
| M12 Release and submission | NOT_STARTED |  |  | Mandatory checkpoint before submission |

## Real-world validation milestones

| Milestone | State | Evidence | Notes |
|---|---|---|---|
| RW0 Adopt and scaffold | COMPLETE | Canonical addendum; typed schemas; ignored corpus; generation card; registration, mutation, Blender, Unreal, and report tooling | 085545efdda09aa3a77aa115ce521ab4dfecb3b0; D003; no product behavior change |
| RW1 Patchling blind baseline | COMPLETE | Registered untouched raw hash; frozen inspect/plan/repair/verify/package; Blender raw/repaired evidence; turntable views; human rights and visual adjudication | D004 and D005; zero unsafe repairs or visual/resource regressions |
| RW2 Minimum Asset Flock | IN_PROGRESS | Patchling and Shader Lantern registered; Lantern approved deterministic/Blender/Unreal checkpoint complete | D009 and D011; two more untouched assets still required |
| RW3 Controlled realistic variants | SCAFFOLDED | Repeatable normalization, hierarchy, and material/texture mutation code; fixture dry runs | Real variants wait for registered corpus assets |
| RW4 Blender and Unreal acceptance | IN_PROGRESS | Blender 5.1.2 Lantern import/re-export; isolated Unreal 5.8 raw/repaired/control import and visual evidence | Lantern has no human-cleaned third arm, so the full three-way gate remains open |
| RW5 Evaluation report and demo | SCAFFOLDED | Typed adjudication and traceable case-study report renderer | Public claims remain prohibited until evidence exists |

## Current gate

Shader Lantern is the second registered real-world input and has completed its approved
inspect → plan → approve → repair → verify → package path plus Blender and isolated Unreal evidence.
Its exported geometry and PBR resources are preserved at the intended 1.2-meter height; the
triangle-budget warning remains explicit. RW2 still needs untouched Debug Beetle and Cloudforge
Workbench assets. M9 requires user-owned AWS profile, model access, region, and cost-control setup
before any paid invocation or resource creation.

## Latest evidence

- Tests: `uv run pytest` — 60 passed and the opt-in live-provider test skipped; intent-first web
  gate — 17 passed; intent canonicalization gate — 2 passed.
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
- Intent-first web acceptance: invalid descriptions, target uses, and heights fail before job
  creation; policy and upload remain unavailable until explicit agreement; non-static intent shows
  the rigging/skinning/animation boundary; former role routes redirect to the new entry point.
- Frozen intent evidence: each agreed story records an opaque ID, exact description and target,
  timestamp, schema version, and canonical SHA-256 in job `intent.json` and packaged provenance.
  Canonical reproduction passes and tampering fails closed. A changed intent creates a new job.
- Target-state derivation: the user supplies desired height, not a scale factor. A non-preset height
  creates a validated profile copy with only `expected_height_cm.target` overridden. Advanced
  policy copies remain schema-validated and changing any rule creates a separate inspection/job.
- Existing web safety acceptance remains: broken-fixture refresh/approve/resume/download; clean
  no-approval completion twice from independent app starts; invalid GLB rejection; unsupported
  inspection-only packaging; exact ZIP audit; source preservation; trusted preset baseline; 50 MB
  and GLB magic boundaries; finding-level rule provenance.
- Single-step evidence: the persistent left pane now orients **Describe → Agree → Inspect → Decide
  → Download**. Intake renders only Rules or Upload and every job response renders only its selected
  Inspect, Decide, or Download panel. Every server-rendered state retains one `data-focus-area`.
- Browser review at 1440 × 900 confirms that Describe, confirmation, and agreed intake use the full
  workspace without horizontal overflow. The full agreed story appears at confirmation and becomes
  a collapsed disclosure during intake so policy controls stay near the fold. At 390 × 844 the left
  workflow rail remains visible, content uses one column, horizontal overflow is absent, and browser
  diagnostics contain no warnings or errors.
- Versioned policy intake remains intact: both repository profiles are immutable presets with
  concise summaries and collapsed full-rule reviews. The agreed height overrides only their default
  target when necessary; `Customize a copy` still exposes only enforced target-state and report-only
  budget fields. Frozen/base IDs, explicit overrides, version, canonical hash, and finding rule
  citations remain preserved.
- Web design handoff: `docs/WEB_DESIGN_AND_FLOW.md` records the intent-first information
  architecture, target-story contract, policy derivation, single-step workflow, Bedrock boundary,
  evidence, and limitations. D018 supersedes the primary audience-selector modality while retaining
  the established layout, disclosure, authorization, and deterministic safety decisions.
- Product inflection review: `docs/INFLECTION_POINT.md` is the single current-versus-envisioned
  handoff. It preserves the existing form-led product as the executable baseline, defines the
  proposed persistent Bedrock/Strands asset conversation, fixes the authority boundary, surfaces ten
  pre-M9 decisions, and proposes a staged transition. Its envisioned model remains a review draft,
  not authorization for AWS work or additional repair domains.
- Distribution audit: `uv build --wheel` succeeded with the intent module, confirmation template,
  workflow rail, updated intake/job templates, CSS, JavaScript, favicon, and existing deterministic
  runtime assets included in the wheel. The checked-in public intent schema remains a repository
  contract artifact alongside the other exported schemas.
- Shader Lantern evidence: raw SHA-256
  `be2c9cab8d4e51f7a948c7c54db7a10c932f24faf69bc3166ff724ccc00c49b9`; 77,545 vertices;
  101,564 triangles; one material; three readable embedded 4096² base-color,
  roughness/metallic, and normal images; 99.908905 m represented height; grounded and Y-up; no rig,
  animation, morph target, negative scale, or non-uniform scale.
- The user approved Shader Lantern's selected Tripo design, intended 1.2-meter height, and exact
  reversible `normalize-root-v1` transform. The two safe display-name repairs and
  `0.0120109414×` uniform root scale executed; independent verification passed with a second empty
  plan and only `TRIANGLE_BUDGET_EXCEEDED` unresolved.
- Shader Lantern's repaired SHA-256 is
  `718722d6203dd0f0d62f86f42f0999e0d44c168f6f29767eee204d7d5631eebd`. Vertex, triangle,
  material, and texture counts remain 77,545, 101,564, 1, and 3. The result ZIP passed CRC and exact
  seven-artifact byte-for-byte audit.
- Blender 5.1.2 imports raw and repaired files with matching geometry/resources and no missing
  images, measures the repaired candidate at 1.2 meters, and re-exports it successfully. Four-view
  rendered MAE is 0.055–0.082/255; the re-export control differs from the delivered candidate by
  0.00028–0.00033/255 MAE.
- Unreal 5.8 imports raw, repaired, and Blender-control arms with one mesh, one material, and three
  textures each, zero errors, and the same non-fatal `FB_ngon_encoding` warning on raw/repaired.
  The visual pass preserves silhouette, material coverage, textures, colors, normals, opacity, and
  non-emissive behavior. The source GLB is opaque/non-emissive, so preview-only glass/glow cannot be
  claimed as exported content.
- Generated fixture evidence stays below ignored `build/validation/`; only reproducible scripts,
  schemas, templates, and typed records are committed.

## Blockers

RW2 requires untouched Debug Beetle and Cloudforge Workbench exports. M9 requires the user to
configure or confirm a dedicated `asset-shepherd` AWS profile, selected Bedrock region/model access,
and a budget alert before paid calls. Read-only preflight found that AWS CLI is not installed on this
workstation (`Get-Command aws` returned no command). A human-cleaned reference and manual-time
record remain required for the full RW4 comparison gate.

## Next action

Review `docs/INFLECTION_POINT.md` with ChatGPT Pro and record the resulting product direction before
beginning M9 implementation. The earliest corpus work remains RW2 registration of the untouched
Debug Beetle GLB when the user supplies it; do not begin Cloudforge until that batch is complete.
Before M9 paid-provider work, confirm the dedicated AWS profile, Bedrock model/region access, and
budget alert. No paid invocation or AWS resource creation is authorized yet.
