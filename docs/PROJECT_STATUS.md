# Asset Shepherd Project Status

**Last updated:** 2026-08-23
**Current commit:** D036 agent-orchestrated architecture correction (this file is included)
**Current milestone:** M9 agent-led sensing and disposition / RW2 Minimum Asset Flock / M10 evaluation
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
| M6 Deterministic CLI MVP | COMPLETE | Happy, rejected, and clean-control runs; schema/ZIP audit; Blender 5.1.2 import; full gate | a077077ca94c44b9693893672a7208d84d1f05b8 | Completed and checkpoint-reviewed 2026-08-21 |
| M7 Strands orchestration harness | COMPLETE | Real Strands loop; native interrupt/resume; approve/reject; bounded correction; metrics; offline and opt-in live tests | 02876da55e2dd0bee3dfbe80bd01cd50f87ba76d | Historical tool/interrupt gate; D036 live agent judgment and action choice remain open in M9 |
| M8 Web product | COMPLETE | Intent-first target-story agreement; D021 single-family policy resolution; D022 ask-only-what-is-missing intake; frozen intent and policy provenance; single-visible-step Rules/Upload and Inspect/Decide/Download; Strands interrupt/resume; dual GLB preview; verification/download | e6b9046c86b96dc43f3f4e255f00e759f2d3d22e | D006–D018 establish the flow; D021/D022 remove implementation choices and repeated target fields without changing acceptance behavior |
| M9 Hosted Bedrock conversation and deployment | IN_PROGRESS | D019 durable workspace foundation; D036 agent-orchestrated correction and acceptance gate |  | Current implementation still delegates semantic findings and repair construction to deterministic code; correct locally before Bedrock/deployment |
| M10 Evaluation | IN_PROGRESS | `docs/REAL_WORLD_VALIDATION_PLAN.md`; typed corpus/evidence harness; D026 authority classes, deeper diagnostics/preservation, official Khronos adapter, render comparison | 085545efdda09aa3a77aa115ce521ab4dfecb3b0 | RW0–RW5 addendum controls real-world evaluation; untouched RW2 assets and full human-reference arm remain open |
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

M9 is paused at the D036 architecture correction. The current hosted workflow is durable and its
deterministic repair mechanics are useful, but it does not yet satisfy the product thesis: the
inspector creates target-dependent findings, the planner manufactures a grouped transform, the
scripted provider follows a predetermined sequence, and verification repeats planner heuristics.

The next gate is the ten-part acceptance contract in `docs/AGENT_ORCHESTRATED_WORKFLOW.md`. A real
workflow model must choose sensing, assessment, disposition, and supported action parameters; every
mutation must originate in an agent call; standardized renders must be model-accessible evidence;
and the grounded long-bodied quadruped regression must not be rotated. Deterministic code remains the
measurement, enforcement, exact-mutation, invariant-verification, and packaging layer.

## Latest evidence

- Architecture diagnosis: the grasshopper-sized quadruped source measured
  `0.471 × 0.463 × 0.998 m` and was already grounded with minimum Y exactly `0`. The inspector
  nevertheless emitted `ORIENTATION_NOT_Y_UP` solely because Z was the longest extent, the planner
  rotated Z to Y, and verification passed by checking that same longest extent was now Y. Luna had
  inferred only `RIG_READY_CHARACTER` and a 5 cm proposal; `agent_result.json` identifies the repair
  runtime as `asset-shepherd-scripted-v1`. No workflow model viewed the source or comparison renders.
- D036 corrects the authority model. `docs/AGENT_ORCHESTRATED_WORKFLOW.md` now documents the complete
  understand → sense → assess → choose disposition → preview action → approve → execute → re-observe
  → verify → package loop. The agent chooses sensors and repairs; deterministic tools return facts,
  calculate exact consequences, enforce constraints, mutate only on an agent call, and prove
  invariants. `docs/AGENT_OPERATING_CONTRACT.md` now defines the corresponding model behavior and
  live acceptance cases.
- Contract version 1.5 explicitly deprecates dominant-extent semantic inference, removes
  deterministic variable planning from the target architecture, makes standardized renders eligible
  sensing evidence, and adds the D036 gate to M9. No product-code compliance is claimed yet.
- Comparison-viewer recovery: the pinned `model-viewer` extension requires plain numeric
  `extra-model` offsets and enters a bad camera state when given the former unbounded
  `min-camera-orbit`/`max-camera-orbit` values. Both attributes are removed, initial and dynamic
  offsets are unitless, and the one shared WebGL scene now visibly renders source, repaired, and
  optional banana GLBs. Browser acceptance exercised Both/Before/After fits, metric axes, banana,
  desktop, and 390 × 844 layouts with no warning or error.
- Approval presentation now asks one compact question containing the exact before/target dimensions,
  keeps component evidence behind one `Details` disclosure, and offers only Reject/Approve. The
  redundant source-file reassurance and duplicate metric tiles are removed. Rendered browser
  acceptance confirms the old sentence is absent and the compact state has one disclosure.
- Agent operating contract: prompt version 2 now defines the user's goal, evidence and authorization
  boundaries, concise technical-art voice, structured-control versus free-text explanation split,
  bounded tool workflow, stop conditions, prompt-injection handling, on-topic behavior, and private
  content limits. The confirmed target and complete frozen policy are appended as delimited JSON job
  data. Tool descriptions now state prerequisites, important returns, and failure behavior. The
  interim Luna intake shares the same private topic/content boundary. New `agent_result.json` records
  use prompt version 2 while version-1 records remain valid. D034 and focused zero-network tests cover
  the contract; representative live-model conversational evaluation remains open.
- Derived normalization postconditions: grounding is now calculated from the bounds produced by
  the proposed scale-and-orientation matrix. A grounded Z-up regression proves the grouped plan
  includes scale, orientation, and newly required grounding; the repaired asset is Y-up, 3.5 m
  tall, grounded at Y=0, and produces an empty second plan.
- Exact failure reproduction: the persisted elephant-scale quadruped originally passed 30
  preservation/readiness checks but failed `SECOND_PLAN_EMPTY` because its rotated candidate
  extended to -1.75 m on Y. Re-running that exact source and frozen profile with the corrected
  planner completes `PASSED_PROJECT_READY`, passes grounding within tolerance, and leaves no
  second-plan candidate.
- Failed-result presentation: verification failure no longer masquerades as inspection-only or a
  successful package. The workspace shows what passed, the exact post-repair finding and failed
  assertion, and the fresh-approval boundary. The ZIP is labeled diagnostics. The rejected GLB is
  view-only and explicitly marked **candidate not ready** in the shared before/candidate viewer;
  fit modes, HUD targets, metric axes, and banana remain available for diagnosis.
- Bounded agent correction: Strands still orchestrates the typed deterministic tools, while Python
  owns measurement, planning, mutation, verification, and packaging. The former same-matrix retry
  is replaced by one fresh deterministic reinspection and plan derivation. It does not mutate the
  candidate or reuse prior approval; a newly proposed physical correction requires a new approval
  turn and versioned provenance before execution.
- Provider-neutral conversation state: Luna currently uses the Responses API for one
  non-persistent structured intake call only; it is not the full workflow conversation. Durable
  coherence lives in the Job Contract, artifacts, minimized events, exact approval state, and
  Strands snapshots. Both scripted and Bedrock agent factories now accept the same required
  session ID plus isolated storage contract, so a provider swap can retain state across turns and
  restarts.
- Spatial repair comparison: completed jobs with executed repairs now load source and candidate in
  one locally served 3D scene at their real relative scales. One camera supplies orbit, pan, zoom,
  and Both/Before/After fit modes. Projected AABB corners drive minimal HUD target boxes, labels,
  and leader lines on every camera change; a model below 18% of its counterpart's longest dimension
  receives an explicit **model here** callout. Optional metric axes use five 1/2/5-spaced meter
  ticks for the selected fit bounds. A toggleable generated banana measures approximately 20 cm
  along its curve. The unchanged Apache-licensed `<model-viewer>` 4.3.1 distribution is now local,
  eliminating the runtime CDN dependency. D031 route and browser evidence covers the 182-meter
  source versus 1.8-meter result, focused fit, meter-axis retargeting, and banana overlay.
- User-oriented help: **How it works** now contains three actions only—describe and upload,
  review what was found, and download the result—followed by one start action. Public release
  numbers, implementation scope inventory, internal tool/provenance terms, and generic caveats are
  removed. Active-rule and finding copy also describe the user-visible fact rather than the
  prototype version; durable versioned policy and artifact metadata are unchanged. D030 route and
  browser evidence covers the exact three-step budget, desktop/mobile layout, and removed terms.
- Simplified inspection review: the former three-column evidence dashboard is replaced by one
  progressive six-check log, one structured summary with at most three attention groups, and one
  **Do these issues look fixable?** acknowledgement before Decide. Complete measurements,
  expectations, findings, rule provenance, plan candidates, stages, preview, and frozen policy are
  retained in a closed 48-row **More details** table. The Inspect view no longer repeats the target
  story, a second workflow rail, or public implementation-boundary copy. Direct Decide navigation
  and submission remain gated until acknowledgement.
- Upload and intake boundary: both upload surfaces share **Choose or drop your GLB** behavior.
  Click-to-choose remains functional; Explorer drop accepts exactly one `.glb`, updates the visible
  filename, and reports invalid drops in place. A structured intake decline stores no description or
  GLB and renders only a concise response without policy commentary.
- D029 browser evidence: the broken fixture replay visibly transitions from **Checking …** rows to
  pass/attention markers. At 1366 × 900 the summary and fixability question share the working view;
  at 390 × 844 the three areas remain ordered with no page overflow, and opened tabular detail
  scrolls inside its own container. Browser console warnings and errors are empty.
- Tests: `uv run pytest` — 108 passed and the opt-in live-provider test skipped. D019–D033 acceptance
  covers objective preflight, derived/custom policy validation, narrowed goals, clean no-mutation
  control, application/runtime restart at approval, chat non-authorization, duplicate decision
  replay, verification, and exact ZIP output.
- Check authority: every finding and verification assertion now identifies frozen project policy,
  universal invariant, objective source diagnostic, or external-consumer evidence. Policy findings
  cite exact parameter values and `CONFIRMED_INTENT`, `DERIVED_INTENT`, `FAMILY_DEFAULT`, or
  `USER_OVERRIDE`; the earlier target-intake artifact separately preserves whether a proposal came
  from model inference, explicit user text, or user clarification. Model conclusions cannot waive
  validity, authorization, source-preservation, or verification invariants.
- Strengthened inspection: direct accessor analysis covers cardinality, finite data, unit normals,
  tangent handedness, index ranges, and degenerate triangles. Active-scene/resource diagnostics
  cover empty and unreachable nodes, unused resources, apparent duplicate materials/textures, root
  origins, and a ground-center reference. Newly exposed unsupported domains remain report-only;
  malformed glTF-validity conditions block repair.
- Strengthened verification: accessors, buffer views/buffers, materials, textures, images,
  samplers, animations, skins, cameras, primitives, original node references, extensions/extras,
  and the complete binary payload must remain semantically unchanged. A deliberately parseable
  material mutation fails the universal preservation gate.
- Official validation: the pinned Khronos glTF Validator 2.0.0-dev.3.10 reports zero errors for the
  clean fixture and two `ACCESSOR_MIN_MISMATCH` errors for each untouched Tripo asset. The
  strengthened Shader Lantern run added no errors, passed verification, and explicitly retained the
  source errors plus its generated-tangent warning instead of claiming zero-error conformance.
- Render evidence: the typed four-view comparison reproduces maximum raw-versus-Shepherd MAE of
  0.081863/255 and Shepherd-versus-Blender-re-export MAE of 0.000334/255. The tool reports numeric
  external evidence only and does not replace human appearance adjudication.
- Semantic target intake: ordinary intake begins with one description. The authorized interim
  OpenAI Luna/xhigh provider proposes supported use and plausible semantic height through strict
  structured output; server validation and the 0.8 confidence gate ask only genuinely unresolved
  fields. The user can adjust and must confirm once. Both paths retain provider/model/evidence in
  `target_intake.json`; hosted adjustments survive restart and are exactly once. Mock transport
  covers the paid request contract; the live probe did not run because `OPENAI_API_KEY` was absent.
- Expectation-led intake and inspection: intended use is now visibly context and a support-boundary
  check, not a selectable preset. Confirmation and clarification contain no target-use dropdown;
  corrections are natural-language reinterpretations. The UI lists target-specific assumptions
  separately from universal invariants, then presents deterministic GLB observations and the
  bounded action plan. Assembly reports roots/nodes/meshes/primitives without inventing semantic
  piece count, and blocked jobs direct users back to the creation/export tool with recorded reasons.
- Asset-in-hand entry language: both entry points now use one short instruction: describe the model
  you are working on. Use and scale guidance stays in the example inside the full-width input. The
  primary surface contains no implementation notes, workflow comparison links, or repeated
  explanatory sentence, and fingerprinted static URLs prevent stale layout CSS after an update.
- Local key handling: two one-line PowerShell entry points save the key through a hidden prompt as
  Windows current-user protected ciphertext outside the repository, then unlock it only around the
  web command and restore process state on exit. Windows PowerShell 5.1 parser, DPAPI round-trip,
  real server startup/shutdown, and static security acceptance pass; the scripts never contain or
  echo a key.
- Target confirmation presentation: the proposal uses the wider workspace, a restrained headline,
  and human-readable metric units. Six assumptions and five invariants are compressed into three
  collapsed groups—Purpose, Scale and pose, and Structure—with no more than three facts per expanded group. The only decision is whether
  the agent got it right; its controls are simply **Yes** and **No**. **No** reveals one prefilled
  description for another attempt, using the same 16-pixel regular-weight field styling as entry
  and clarification. A shared workflow-stage renderer, description-field renderer, and
  confirmation-decision renderer now own those repeated display areas across the form-led and
  hosted routes; acceptance rejects duplicate textarea or decision markup outside that component.
  Full-page browser comparison at 1366 × 768 and 390 × 844 confirms identical panel bounds,
  heading typography/position, and active description-field geometry and styling; mobile has no
  horizontal overflow, hosted entry uses the shared field, browser diagnostics are empty, and
  stable scrollbar space prevents width shifts between steps.
- Shared feedback: `/feedback` accepts context from any workflow surface, offers four bounded
  reasons and an optional 1,000-character note, and records a local atomic JSON artifact without an
  external service. Confirmation links include their intent or workspace reference and return path.
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
- Target-state derivation: the user supplies desired height once, not a scale factor or baseline.
  D021 resolves one versioned policy family into a validated job profile. Height comes from the
  confirmed story; bounded height/ground tolerances scale with intended height; explicit
  standing/hanging/hovering language may set grounding; and unspecified rules retain family
  defaults. Advanced values remain schema-validated and changing intent or any rule creates a
  separate inspection/job.
- Existing web workflow acceptance remains: broken-fixture refresh/approve/resume/download; clean
  no-approval completion twice from independent app starts; invalid GLB rejection; unsupported
  inspection-only packaging; exact ZIP audit; source preservation; trusted family baseline; 50 MB
  and GLB magic boundaries; finding-level rule provenance.
- Single-step evidence: the persistent left pane now orients **Describe → Agree → Inspect → Decide
  → Download**. Intake renders only Rules or Upload and every job response renders only its selected
  Inspect, Decide, or Download panel. Every server-rendered state retains one `data-focus-area`.
- Workflow help: a large persistent `?` action sits immediately below **New asset** in both rail
  variants and opens `/how-it-works`. The page uses one continuous four-step explanation, one
  collapsed repair-scope disclosure, and a start action without changing the workflow. Browser
  acceptance at the default viewport and 390 × 844 confirms action order, active state, one focus
  area, no horizontal overflow, and no console warning or error.
- Browser review at 1440 × 900 confirms that Describe, confirmation, and agreed intake use the full
  workspace without horizontal overflow. The full agreed story appears at confirmation and becomes
  a collapsed disclosure during intake so policy controls stay near the fold. At 390 × 844 the left
  workflow rail remains visible, content uses one column, horizontal overflow is absent, and browser
  diagnostics contain no warnings or errors.
- D027–D029 browser review confirms the three-group confirmation, simplified inspection, and shared feedback page at the
  default desktop viewport and 390 × 844. The compact document width is 375 pixels within the
  390-pixel viewport, all decisions and the feedback link remain visible, navigation starts at the
  top, and browser diagnostics contain no warnings or errors.
- Versioned policy intake remains intact: historical repository profiles stay byte-for-byte
  immutable for CLI and evidence reproduction, while new conversational jobs use the immutable
  `unreal-static-game-asset-family-v1` family. `Review all active rules` and `Why these rules?`
  expose the agent proposal progressively; `Adjust supported rules` exposes only enforced
  target-state and report-only budget fields. Frozen/family IDs, explicit differences, per-rule
  sources, version, canonical hash, and finding rule citations remain preserved.
- Web design handoff: `docs/WEB_DESIGN_AND_FLOW.md` records the intent-first information
  architecture, target-story contract, policy derivation, single-step workflow, Bedrock boundary,
  evidence, and limitations. D018 supersedes the primary audience-selector modality while retaining
  the established layout, disclosure, authorization, and deterministic invariant decisions.
- Product inflection review: `docs/INFLECTION_POINT.md` is the single current-versus-envisioned
  handoff. It preserves the existing form-led product as the executable baseline, defines the
  proposed persistent Bedrock/Strands asset conversation, fixes the authority boundary, surfaces ten
  pre-M9 decisions, and proposes a staged transition. ChatGPT Pro completed the requested review and
  recommended a conversation-led, contract-anchored workspace rather than a chat-only product. The
  recorded outcome calls for objective preflight before target confirmation, a visible structured
  Job Contract, derived frozen policy for ordinary users, exact non-chat authorization, durable
  resume, structured provenance, and the unchanged repair pipeline. The direction is accepted in
  D019. Contract version 1.4 now controls objective preflight, visible Job Contract, semantic target
  intake, derived frozen policies, exact structured authorization, durable resume, and minimized
  hosted conversation provenance without authorizing AWS work or additional repair domains.
- D020–D023 local hosted reference: `/workspace` presents one conversation beside a persistent Job
  Contract. Profile-free `PreflightResult` records source identity, structure, bounds, transforms,
  counts, eligibility, and declared material metadata before any policy finding or plan exists.
  Target confirmation separates original intent, requested use, supported job goal, support status,
  and external handoff; resolves the one trusted family from confirmed intent; validates supported
  advanced overrides; and freezes policy identity, family, explicit differences, rule sources,
  version, and canonical hash.
- Durable-resume evidence: private atomic workspace state, structured event/tool ledger, command
  idempotency records, retention/deletion status, deterministic runtime state, and Strands native
  snapshots reconstruct the exact pending interrupt in a new store and a new FastAPI application.
  Replaying the same decision command leaves repaired GLB and result ZIP bytes unchanged. Chat
  evidence questions cannot clear the interrupt.
- Rendered browser acceptance: start, preflight, approval, and completion retain two primary work
  areas (conversation and Job Contract); policy/finding detail stays collapsed; source and candidate
  model previews render after verification; browser diagnostics contain no warnings or errors. The
  Chrome extension needs its optional file-URL permission for browser-driven fixture selection,
  while server upload and route acceptance pass independently.
- D021 browser acceptance: a 1.2 m hanging-lantern story renders one concise agent-resolved proposal,
  correctly removes ground contact, keeps complete rules/reasons/advanced values collapsed, shows
  confirmed height without a second input, prefills bounded advanced values, and advances to upload
  with no named baseline, raw transform, browser warning, or error.
- D022 browser acceptance: initial intake renders only the description; a static-lantern description
  without size renders only the height question; the 1.2 m answer advances to an exact
  confirmation. Desktop and compact views keep one focus area, no horizontal overflow, and no
  browser warning or error.
- D023 browser acceptance: the entry screen contains one question, one text area, one disclosure,
  and one action. The low-confidence offline fallback for “a mountain of goop” renders one concise
  question with only the two missing controls; a complete target renders one large proposal, one
  confirmation action, and collapsed adjustment. At the inspected 2844-pixel viewport, content has
  no horizontal overflow. Semantic proposal routing is covered with an injected model analyzer.
- Distribution audit: `uv build --wheel` succeeded with target-intake, intent, and policy-resolution
  modules, canonical policy-family JSON, clarification/confirmation/intake templates, workflow rail,
  CSS, JavaScript, favicon, and existing deterministic runtime assets included in the wheel. The
  checked-in public target-intake, intent, and provenance schemas remain repository contract
  artifacts alongside the other exported schemas.
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

The D036 local architecture correction is unblocked and precedes AWS work. RW2 requires untouched
Debug Beetle and Cloudforge Workbench exports. Paid or remote M9 work requires
the user to configure or confirm a dedicated `asset-shepherd` AWS profile, selected Bedrock
region/model access, and a budget alert. Read-only preflight found that AWS CLI is not installed on
this workstation (`Get-Command aws` returned no command). A human-cleaned reference and manual-time
record remain required for the full RW4 comparison gate.

## Next action

Implement D036 locally before any Bedrock or deployment work: split observations from contextual
assessments, expose composable typed sensor and action-preview tools, make the real workflow model
choose sensing and disposition, add model-consumable standardized renders, and replace second-plan
verification with declared-action postconditions plus agent reassessment. Preserve the current
mutation scope, exact authorization, durability, and invariant checks. The first regression is the
grounded long-bodied quadruped; it must remain unrotated without an asset-specific exception.

RW2 registration resumes when the user supplies Debug Beetle. No paid invocation or AWS resource
creation is authorized yet.
