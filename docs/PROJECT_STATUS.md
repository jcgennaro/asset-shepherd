# Asset Shepherd Project Status

**Last updated:** 2026-08-29
**Current commit:** Bedrock and AgentCore deployment procedure (this file is included)
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
| M9 Hosted Bedrock conversation and deployment | IN_PROGRESS | D019 durable workspace; D036 authority contract; D037 agent-authored planning; D038 bounded multi-turn loop; D039 hosted handoff; D040 named asset gallery; D041 explicit approval; D042 upload-first flow; D043 semantic assembly and mesh health; D044 coordinate-aware yaw sensing |  | Repeated feedback/action/approval turns, per-asset session state, resumable seven-slot workspace, and one-task-per-step hosted UX are implemented locally; remaining D036 live evaluations precede Bedrock/deployment |
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

M9 remains at the D036 acceptance gate. D037 replaces the first target-dependent planning pass with
a live model-authored assessment and exact typed action preview. Agent-mode inspection exposes
measurements without legacy height/orientation/grounding verdicts; the agent selects semantic axes
and requested scale, rotation, grounding, pivot, and naming components; deterministic code adds
none. An
executed action cannot verify until the agent compares recorded source and candidate renders.

D038 and D063 make that action cycle repeatable rather than adding a special second pass. After
Shepherd, the user chooses the current input or candidate as Iteration 1; Refine archives each pass,
shows 4.1/4.2/4.3 in the rail, and invokes the same workspace-scoped agent with fresh sensing and
authorization. Remaining D036 work is representative
ambiguous-orientation and changed-goal live evaluation. Deterministic code remains the measurement,
enforcement, exact-mutation, invariant-verification, and packaging layer.

## Latest evidence

- D070 deployment procedure: `docs/BEDROCK_DEPLOYMENT_RUNBOOK.md` separates the M9 move into a local
  Bedrock provider gate, cloud-portability gate, and remote-product gate. It preserves
  `workspace_id` as the per-asset session authority, selects Strands S3 snapshots plus private S3
  artifacts and conditional DynamoDB workflow state, keeps the interactive web app separate from
  AgentCore, and makes the local Blender visual-sensing dependency an explicit portability gate.
  Step 1 begins with credential-free workstation inspection; paid calls and resource creation still
  require identity, model/region, budget, and cost checkpoints.
- D070 Step 1.1 preflight: WinGet reports a per-user AWS CLI v2.36.34 installation and the executable
  runs successfully by absolute path. The current Codex process inherited an older PATH and cannot
  resolve `aws`; a fresh terminal should. No AWS config or credentials file exists yet, so no caller
  identity, region, model access, or budget assertion has been made.

- D069 comparison-control consolidation: comparison viewers now replace the passive square glyph
  and separate Both/Before/After buttons with one square **Cycle viewpoint** action. It advances
  Both → Before → After → Both through the existing smoothly interpolated fit path and updates its
  hover and accessible text with the current and next view. Source-only viewers retain one direct
  fit-to-window button. Live browser acceptance on the completed Humanoid Woman workspace exercised
  all three transitions and returned to Both with no console errors. That real run also reduced a
  76.6 × 97.8 × 26.3 m source to a proportionally fitted 0.787 × 1.01 × 0.271 m candidate while
  preserving appearance, pose, grounding, resources, and protected topology seams. The common gate
  passes with 177 tests, one opt-in skip, lock validation, Ruff, formatting, and zero Pyright
  findings.

- D068 refinement interaction correction: the generic disclosure widget has been removed. The
  blocked result initially presents one standard, center-aligned **Refine…** button. Activating it
  removes that button, focuses one full-width 148 px multiline editor, and places **Start refining**
  in the original action position beside the secondary diagnostics and Gallery controls. The field
  retains an accessible label without adding another visible title. Live browser inspection of the
  persisted riding-crop workspace confirms the pre-click and post-click DOM states and the expanded
  visual layout. The common gate passes with 177 tests, one opt-in skip, lock validation, Ruff,
  formatting, and zero Pyright findings.

- D068 safe component-selection recovery: a persisted riding-crop pass measured three exact,
  safely removable components but the agent treated uncertainty about the intended survivor as an
  unsupported repair. Prompt v13 now directs the agent to use all four views, propose plausible
  exact component IDs with reduced confidence, and defer the consequential choice to the existing
  per-component review. Component selection precedes normalization so stray-body bounds do not
  defeat the useful first repair. The saved workspace now says the pass stopped before choosing
  labeled forms, distinguishes this from a truly unsupported GLB layout, and exposes **Refine
  current iteration** over the preserved input. Browser inspection on port 8011 confirms the
  corrected Asset Shepherd message, inspection action, and recovery control. No mutation was
  automatically submitted. The common gate passes with 177 tests, one opt-in skip, lock
  validation, Ruff, formatting, and zero Pyright findings.

- D067 pending-origin preview: approval pages no longer imply that an unexecuted pivot repair has
  already happened. The current iteration retains a labeled **Current origin** marker, while the
  typed normalization payload supplies a distinct **Proposed origin** marker at its exact
  source-space target. The Asset Shepherd sentence is explicitly prospective until approval. On
  the live Equestrian Riding Crop workspace, browser inspection confirms the proposed marker at
  `(-0.0332031623, 0.6083984673, 0.0) m`, visually centered in the surviving component's bounds,
  with the authored origin still shown below it. The common gate passes with 176 tests, one opt-in
  skip, lock validation, Ruff, formatting, and zero Pyright findings.

- D066 incomplete-planning recovery: the live Responses trace for the failed Equestrian Riding
  Crop run showed a valid return-to-creation conclusion trapped by an empty optional pivot ID and
  report-only screenshot citations, then repeated until the 12-call bound. The deterministic
  boundary now treats a blank optional ID as absent and validates any cited source views regardless
  of disposition. A pre-approval failure preserves the measured job and offers **Retry Shepherd**
  through a fresh bounded invocation; post-action recovery remains **Finish this iteration**. The
  original workspace was recovered from the model's recorded proposal without another mutation or
  user re-entry and now packages a BLOCKED diagnostic result with no error. Browser inspection on
  port 8011 shows the Asset Shepherd explanation, check table, diagnostics download, and Gallery
  action instead of the generic Stopped alert. Targeted agent, hosted-state, and web coverage passes
  with 72 tests and one opt-in skip. The full common gate passes with 176 tests, one opt-in skip,
  lock validation, Ruff, formatting, and zero Pyright findings.

- D064/D065 pivot and speaker checkpoint: a new read-only sensing tool returns source-hash-bound
  origin candidates for authored origin, bounds centers/corners, surface centroid, long-axis end
  regions, and a uniform-volume centroid only for topology proven closed and consistently wound.
  The live agent can select only one registered ID after citing all four coordinate views; the
  deterministic planner resolves coordinates, previews the exact root translation, requires
  approval, and independently verifies the measured point at origin. The surviving riding-crop
  candidate produces distinct Z-min and Z-max end-region centers, addressing the prior
  handle-center capability gap without arbitrary XYZ. Prompt v12, schemas, and regression tests
  cover the boundary. Agent-authored workflow prose now uses one consistent Asset Shepherd speech
  bubble on Upload, Describe, target confirmation, approval, completion, and refusal screens.
  Browser inspection confirms the speaker treatment, border, background, and bubble tail. The
  common gate passes with 175 tests, one opt-in skip, lock validation, Ruff, formatting, and zero
  Pyright findings.

- D063 Refine-loop checkpoint: the first Shepherd result now offers an explicit survivor choice
  between its input and candidate. The selected immutable GLB becomes Iteration 1; subsequent
  passes appear as 4.1, 4.2, and later Refine sub-items and record selection plus source hash in the
  append-only turn chain. The hosted source route and viewer use that selected iteration rather
  than the original upload. Indexed world bounds now ignore deleted-but-unreferenced tuples while
  retaining them as a separate cleanup finding. Trimesh verification independently measures only
  face-referenced geometry, so exact component removal verifies without conflating retained binary
  payload with renderable bounds. Prompt v11 makes post-deletion bounds and origin evidence stale,
  requires candidate-relative reassessment, and reserves any pivot correction for a fresh approved
  Refine proposal. A stable per-workspace agent ID restores interrupts across candidate filename
  changes, and an interrupted post-action pass exposes a non-mutating Finish-this-iteration recovery
  action. Browser acceptance on the persisted riding crop shows one component, a 35.4 × 27.1 ×
  97.5 cm box, the still-independent origin, and Step 4.1 Iteration 1. The interrupted approved
  cleanup then finished without repeating mutation, independently verified, packaged, and rendered
  an Iteration 1/Iteration 2 comparison containing only the surviving crop. Blender comparison
  framing now refreshes translated world matrices before camera fitting, eliminating the clipped
  evidence that had blocked recovery. The common gate passes with 173 tests, one opt-in skip, lock
  validation, Ruff, formatting, and zero Pyright findings.

- D062 component-review presentation follow-up: the source viewport now keeps every detected
  component's live wireframe bounds and C-label visible by default, so the C1/C2/C3 choices map
  directly to the model without hover. A stable six-color palette now gives each action item and its
  corresponding 3D box the same color; hovering or focusing one choice strengthens both together
  while every other labeled box stays visible. Chrome acceptance on the persisted three-part
  riding-crop workspace confirms cyan C1, gold C2, and magenta C3 correspondence, synchronized C3
  focus, and no console errors. Upload also includes one collapsed `What about FBX?` note that keeps
  GLB primary while answering the predictable format question without another heading. The common
  gate passes with 170 tests, one opt-in skip, lock validation, Ruff, formatting, and zero Pyright
  findings.

- D062 bounded component-selection checkpoint: static indexed triangle primitives now expose stable
  exact position-projected bodies rather than guessing semantic pieces from node or primitive
  counts. Scale-relative near-contact probes can group bodies separated by tiny gaps, but remain
  read-only hints and never alter exact IDs or authorize a repair. The workflow agent must cite four
  source views and select exact IDs; the single topology row shows all bodies, highlights their live
  world-space wireframe bounds, and lets the user keep, remove, or comment on each selection. A
  changed selection returns to the same agent without mutation. Approval filters only the selected
  index triples in proven-safe, unskinned, one-instance layouts; it refuses unknown IDs, total
  deletion, morphs, compression, sparse/extended accessors, malformed data, and pending degenerate
  cleanup. Independent verification proves the exact triangle delta and retained component count.
  Synthetic three-body removal and near-gap false-positive coverage pass. A live browser run with
  three separated tetrahedra completed upload → description → agent sensing → exact component
  proposal → per-body approval → removal → independent visual reassessment: the agent retained C1,
  removed C2/C3 (eight triangles), and verified one remaining four-triangle body. Per-view
  orthographic evidence fitting prevents long, thin layouts from becoming invisible in side views;
  the regenerated right view spans 71.5% of the frame instead of a few pixels. The common gate
  passes with 170 tests, one opt-in skip, lock validation, Ruff, formatting, and zero Pyright
  findings. Broader corpus acceptance remains in the D062 follow-up gate.

- D061 degenerate-geometry cleanup checkpoint: objective inspection now distinguishes a safely
  cleanable indexed triangle-list layout from an unsupported topology layout. A live agent may
  request one separate consequential action that removes only proven zero-area triangle triples and
  compacts only complete vertex tuples no surviving triangle references. The exact affected
  primitive and before/after counts are approval-bound; execution retains the source binary as an
  immutable prefix and remaps every aligned attribute together. Independent verification compares
  all surviving expanded corners, confirms the exact triangle/vertex deltas, and requires zero
  remaining degenerate or unused records. The checked-in failure fixture moves from 12 triangles / 24
  positions to 11 / 23 when approved; rejection preserves the original bytes and both findings. The
  single inspection table now exposes those defects and the exact action instead of hiding them
  behind generic topology counts; completed summaries retain unresolved warnings. Browser
  acceptance verifies the persisted warning case. The common gate passes with 165 tests, one
  opt-in skip, lock validation, Ruff, formatting, and zero Pyright findings.

- Geometry-failure and pivot-visibility checkpoint: two reproducible, parseable synthetic GLBs now
  exercise distinct post-upload failure behavior. `degenerate_triangle.glb` reports objective
  degenerate/unused geometry and remains otherwise eligible;
  `malformed_attributes.glb` exposes a POSITION/NORMAL cardinality violation and blocks repair.
  Adjacent typed manifests freeze their hashes and expected findings, and regeneration is covered
  byte-for-byte. The shared source/comparison viewport now projects a minimal `ORIGIN` crosshair at
  the GLB coordinate origin (and separate before/after origins after a repair), using the same live
  hotspot/HUD update path as the rotating 3D bounds. This completes the visible part of D053: the
  agent still selects Preserve, bounds-center, or footprint-center-bottom from intended use; the
  user accepts, rejects, or comments on that Size and pose proposal; no automatic center default or
  options menu was introduced. Browser inspection confirms the marker and 12-edge bounds render
  together. The common gate passes with 162 tests, one opt-in skip, lock validation, Ruff,
  formatting, and zero Pyright findings.

- Idle-orbit HUD registration: while the source viewer auto-orbits during active Shepherd work, one
  animation-frame loop now reprojects the complete SVG HUD from the viewer's live hotspot positions.
  The measured 3D bounds, dimension label, optional metric axes, banana target box, and banana leader
  therefore remain registered with their 3D targets instead of waiting for a user-generated
  `camera-change` event. The loop runs only while `auto-rotate` is active, stops for hidden or
  disconnected views, respects reduced-motion behavior, and retains event-driven rendering when
  idle. Targeted viewer coverage, Ruff, formatting, and Pyright pass.

- D060 unsupported-repair presentation: the persisted three-form riding-crop case now presents the
  agent's `RETURN_TO_CREATION_TOOL` disposition as a red blocked sentence and inspection lane. The
  table exposes the objective/semantic mismatch—three disconnected forms versus one expected
  piece—and states that no supported action can remove them. It no longer offers a continuation
  control when no candidate GLB exists; diagnostics and Gallery remain available. Name findings no
  longer render beside a contradictory “need no change” sentence. A focused regression and browser
  acceptance exercise the actual saved workspace. Geometry deletion remains deferred as a future,
  exact-component, explicit-approval repair domain under D060; its proposed sensor, component IDs,
  UI, mutation boundary, verification, and post-MVP acceptance cases are captured in
  `docs/FUTURE_COMPONENT_HANDLING.md`. The common gate passes with 157 tests, one opt-in skip, lock
  validation, Ruff, formatting, and zero Pyright findings.

- D059 gallery status checkpoint: every persisted asset card now shows one plain-language workflow
  state with a visible dot and text, rather than exposing the internal phase enum. Pending
  description is `Step 2 · Describe`; approval is `Step 3 · Review`; verified completion is `Step 3
  · Ready`; unresolved work is `Step 3 · Blocked`; and runtime failure is `Step 3 · Failed`.
  Neutral, amber, green, and red treatments supplement rather than replace the words. A file rejected
  during Upload does not create a project card or consume one of the seven slots; its concise error
  remains on Step 1. Route and mapping coverage exercise every durable state, and browser acceptance
  confirms the status remains readable without adding another panel or heading. The common gate
  passes with 156 tests, one opt-in skip, lock validation, Ruff, formatting, and zero Pyright
  findings.

- D058 working source and upload-preflight checkpoint: the source-only 3D viewer remains visible
  beside observable tool activity throughout Shepherd work and orbits slowly unless the user prefers
  reduced motion. With no candidate present it removes the redundant `Before` leader, retains the
  measured 12-edge world-space wireframe bounds, and labels that box with adaptive metric X/Y/Z
  dimensions. Objective preflight now rejects non-positive extents and world bounds whose largest
  extent exceeds the smallest by more than 10,000:1 before intake or agent work. Four sub-kilobyte
  fixtures exercise gibberish, truncation, malformed GLB JSON, and an FBX-shaped upload: every case
  stays on Upload, creates no workspace source, and exposes no parser internals. FBX remains outside
  the GLB-only submission scope. Browser acceptance confirms the source-only dimensions, 12-edge
  bounds, absent leader, and idle orbit state. The common gate passes with 151 tests, one opt-in
  skip, lock validation, Ruff, formatting, and zero Pyright findings.

- D057 navigation and source-context checkpoint: Gallery and Workflow are now separate high-level
  rail choices. Gallery is not numbered; a selected asset exposes only **1 Upload, 2 Describe, 3
  Shepherd**. The staged immutable GLB appears from Describe onward in the existing local viewer,
  with optional metric axes and banana reference. Its eight measured world-space AABB corners are
  joined as 12 projected wireframe edges that track camera motion instead of a flat HUD bracket.
  Desktop and 375 px browser checks show no horizontal overflow; the axes and banana toggles work,
  and the wireframe path retains 12 segments after rotation. A separate real Tripo-to-Unreal asset
  was reported usable without game-developer complaints; this remains informal field evidence. The
  common gate passes with 148 tests, one opt-in skip, lock validation, Ruff, formatting, and zero
  Pyright findings.

- D056 phase-aware action report: the shared five-lane inspection table now labels its final column
  `Proposed action` before authorization and `Action taken` after execution. Executed repairs become
  `!→✓` only when independent verification confirms their postcondition; the hover explanation
  identifies them as addressed and names the applied action. Rejected, report-only, unresolved, and
  verification-failed work retains attention styling and plainly records that no verified correction
  occurred. Route coverage exercises both a successful candidate and a forced verification failure;
  browser acceptance confirms the final table and hover explanation without horizontal overflow.
  The common gate passes with 148 tests, one opt-in skip, lock validation, Ruff, formatting, and zero
  Pyright findings.

- D055 proposal feedback and working-state checkpoint: each active repair lane now offers
  Accept/Reject/Comment before execution. All accepted lanes retain one exact `Approve`; any
  rejection or comment produces one `Revise plan` action, archives the pending plan and assessment,
  records typed feedback, performs no mutation, and resumes the same workspace-scoped Strands
  conversation. Pass and report-only rows have no controls. While that agent request is in flight,
  stale questions and response controls are hidden and only observable tool activity remains. A
  live browser check exercised the Size and pose comment field and button transition; the agent
  honored “keep the present scale” and formed a names-only replacement plan. Display-name-only
  candidates now use exact independent payload/inventory verification without a meaningless visual
  gate, while physical and topology mutations still require before/after reassessment. Regression
  coverage proves no candidate GLB exists during revision. The common gate passes with 148 tests,
  one opt-in skip, lock validation, Ruff, formatting, and zero Pyright findings.

- D054 multi-turn and observability checkpoint: a later repair now composes its delta into the exact
  immediately proven Asset Shepherd normalization root instead of adding another wrapper. Lineage
  requires the prior candidate hash, archived plan/provenance, active-root structure, identity, and
  matrix to agree; the plan records before/after matrices and independent verification permits only
  that mutation. A two-consequential-turn regression preserves node count and exactly one
  normalization root.
- Standardized source, candidate, and shared-scale renders now include object masks and fail closed
  unless every PNG decodes, contains useful foreground, has adequate projected span, stays below
  the maximum frame fill, and retains a clear margin. A real Blender fixture run measured 3.4–7.1%
  foreground, 43–44% projected span, and 26–27% minimum margin. The workflow model receives these
  quality metrics with all three render sets rather than trusting file existence.
- Hosted agent transitions now show the current and two most recent observable Strands tool actions
  instead of `Working…`. The per-workspace no-store activity record deliberately excludes reasoning
  tokens and model prose. Approval-table text is approximately 17 px with tighter spacing; 3D HUD
  labels are 13 px desktop and 11 px compact. Browser inspection confirms one title and one table.
  The common gate passes with 146 tests, one opt-in skip, Ruff, formatting, lock validation, and zero
  Pyright findings.

- D053 pivot placement: objective sensing now reports the asset origin, world-bounds center,
  footprint center-bottom, and root world origins without choosing a target. Prompt version 7 lets
  the workflow agent preserve the authored pivot or request one of two bounded center targets based
  on confirmed use and rendered/measured evidence. The deterministic planner derives the exact
  translation, rejects bounds-center plus grounding, records pivot and grounding separately, and
  independently reloads the written candidate to verify the requested anchor at the origin. Pivot
  remains part of the one grouped Size and pose approval lane. The stable live prompt is about 9.3K
  characters before job context; future specialist guidance may be delivered just in time without
  making authority or safety rules optional. The common gate passes with 143 tests, one opt-in skip,
  Ruff, formatting, lock validation, and zero Pyright findings.

- D052 persistent gallery home: Assets is now a clear header and workflow-rail destination during
  every hosted step. Returning does not mutate the active workspace, and each gallery card resumes
  the exact persisted phase. Uploads awaiting description are gallery-visible and survive an
  application restart. Redo reuses the original GLB and prior description while preserving the
  saved run until the replacement workspace is successfully created. Route tests prove a new
  workspace ID and byte-identical source; browser review confirms the seven-card gallery remains
  compact and readable.

- D051 single approval surface: the approval screen now has one semantic table with one row for
  each of five check lanes and columns for the finding, status, and proposed action. The duplicate
  repair list and synthetic `Repair plan` lane are gone. Attention icons retain hover/focus
  explanations, adaptive metric units make small targets readable, and the Computer Chip topology
  row explicitly says that no weld is proposed because 5,312 coincident positions preserve
  `TEXCOORD_0` seams. Desktop and 390 px browser checks show one table with no horizontal overflow
  or console errors. Local OpenAI Responses calls now consume a complete response inside the client
  context, eliminating the observed non-fatal stream-finalization warning while retaining response
  IDs and tool calls.

- D050 proportional box fit and transparent weld disposition: unequal X/Y/Z targets now resolve to
  the geometric mean of their per-axis ratios, the scale-invariant least-squares optimum in log
  space. One uniform transform still preserves proportions, while prompt version 6 forbids treating
  an expected residual as a failed exact-axis requirement. The supplied Computer Chip candidate's
  SHA matches the rejected run; fresh inspection measures 5.000 × 4.452 × 1.732 cm and confirms no
  weld occurred because all 5,312 coincident positions cross `TEXCOORD_0`. Topology hover evidence
  now says when welding is unavailable, and an actual safe compaction appears in the visible repair
  list. Endpoint clarification uses one sentence and product-neutral animated engine glyphs because
  third-party logo animation is not assumed to be licensed.

- D049 concise task screens and intake reliability: the Describe textarea no longer carries a
  visible `Model description` caption; its accessible name remains intact. The controlling contract
  now forbids visible subtitles or field captions that simply rename the only task or control.
  Low-confidence model output that leaves a field null while explaining its absence is normalized
  at the provider boundary, so the reproduced Computer Chip response advances with only `endpoint`
  missing instead of returning HTTP 400. Contradictory high-confidence nulls still fail validation.
  The exact description succeeds against configured Luna, desktop browser review confirms the
  caption is absent, and the common gate passes with 136 tests, one opt-in skip, Ruff, formatting,
  and zero Pyright findings.

- D048 attribute-seam presentation: protected UV, normal, tangent, color, and skinning splits are
  now described as expected glTF representation rather than defects or user repair decisions. The
  agent is instructed to ignore those counts when deciding whether the asset needs work and instead
  assess the residual position-projection boundary, non-manifold, and winding evidence. On-demand
  job details and the Markdown inspection report show those concepts separately. Position-only
  welding remains unavailable and the exact complete-tuple compaction gate is unchanged. Prompt
  version 5, route coverage, and schema provenance are current; browser review passed, and the
  common gate passes with 135 tests, one opt-in skip, Ruff, formatting, and zero Pyright findings.

- D047 seam-aware duplicate positions: every triangle primitive now records exact coincident-position
  groups, a position-only virtual-weld topology projection, complete-tuple mergeability, and the
  attributes that prevent a merge. The Computer Chip reproduces the independent Blender probe:
  5,312 coincident positions; virtual topology moves from 7,735 boundary plus 8 true non-manifold
  edges to 91 plus 50; all 5,312 remain protected by `TEXCOORD_0`, so no chip weld is registered.
  The live agent may explicitly request lossless compaction only when every vertex attribute is
  byte-identical. Append-only GLB rewriting and expanded per-corner verification prove a synthetic
  five-to-four vertex repair preserves triangles, bounds, attributes, and resources. Approximate
  target X/Y/Z boxes originally resolved to one median uniform factor with residuals recorded; D050
  supersedes that metric with a whole-box log-space optimum. Non-uniform scaling remains forbidden.
  Ruff, Pyright, 135 tests, schema regeneration, and browser review pass.

- D046 intake reliability and examples: the model-facing X/Y/Z shape now uses a closed object rather
  than a fixed tuple that emitted unsupported `prefixItems`; the deterministic target contract still
  freezes the canonical three-value tuple. Canonical Unity, Unreal, and Godot responses discard
  redundant endpoint detail before semantic validation. Provider diagnostics remain server-side and
  public failures use concise retry language. A configured live OpenAI request advanced a Unity
  humanoid description to its durable workspace. The description screen replaces the ambiguous
  question-mark control with one text link and a larger modal that leads with what to include and why,
  followed by exactly three examples. Targeted analyzer/route tests and desktop browser review pass.

- D045 endpoint, bounds, and candidate handoff: semantic intake now freezes Unity, Unreal, Godot, or
  a described Other endpoint and tight final-pose X/Y/Z bounds. Uniform scaling remains the only
  supported scale mutation. Source and candidate visual sensing now records isolated renders plus a
  shared-scale comparison; local Blender evidence derives camera clipping from asset bounds, while
  Blender remains excluded from the hosted runtime. The rejected 1 cm Computer Chip candidate is
  visible in its isolated render, retains all deterministic preservation passes, and remains
  downloadable before human acceptance as `computer-chip-candidate.glb`; its topology warning and
  rejected verification state are preserved.

- D044 capabilities and yaw: a brain-icon **What it does** page reduces the worker-facing scope to
  import, appearance, and shipping practicality, with one sentence and three groups. Standardized
  visual evidence now carries a versioned glTF source-axis contract: +Y up, +Z forward, and -X
  right; front/right/back/left camera positions are +Z/-X/-Z/+X. Prompt version 4 requires the agent
  to infer front from semantic cues across all four views, while deterministic registration rejects
  a Y-axis yaw decision that omits any labeled view. Ambiguous or symmetric fronts remain unchanged.
  Browser review at the default viewport and 390 × 844 confirms one page title, exactly three
  capability groups, no horizontal overflow, and no console warnings.

- D043 semantic assembly and mesh health: the intake agent now freezes an expected semantic piece
  count and evidence, defaulting to one unless the description clearly names a pair or set. The UI
  no longer couples assembly intent to a redundant GLB-validity message. Deterministic triangle
  diagnostics expose non-manifold and inconsistently wound edges, edge-connected face components,
  unused/coincident positions, vertex reuse, and FIFO-16 ACMR. Objective defects and narrow
  performance risks are report-only; ambiguous topology facts remain evidence for agent judgment,
  and no geometry rewrite or optimization action was added. Textareas submit on Ctrl+Enter while
  plain Enter remains a line break. Comparison fits now interpolate, the banana twirls in and melts
  out with reduced-motion support, and public GLB/ZIP attachments use the agent-assigned asset name.
- D042 upload-first hierarchy: the authoritative public rail is now **Assets → Upload → Describe →
  Shepherd**, and `/` redirects to its seven-slot gallery. A GLB must pass bounded container
  validation and objective preflight before the separate description screen. Target agreement and
  inspection are one Shepherd stage. Start screens have one global title plus at most one agent
  sentence; route tests reject subordinate heading stacks. The historical form-led deep intake now
  has one sentence, one upload control, and one collapsed rules disclosure instead of its nested
  substeps and nine title-like texts. Refusal removes the temporary staged GLB; replacement remains
  destructive only after the new durable workspace succeeds.
- D041 approval simplification: approval has one title,
  one six-row checklist, one exact three-group change list, and Reject/Approve. Attention rows are
  color-highlighted and their icons explain the condition on hover or keyboard focus. The duplicate
  result table, completed count, context bar, hidden plan details, and recorded-evidence question are
  removed. Live browser review of Polar Robot Puppy shows the exact 0.463 m → 1.500 m scale change
  and both automatic name mappings before approval.
- D040 named-asset workspace: the first intake turn now assigns a concise asset name used in the
  gallery, page title, and workspace context. `/workspace` shows up to seven source previews that
  resume the exact durable phase. An eighth upload requires an explicit replacement choice. Each
  `workspace_id` continues to own its existing `strands_state` session directory. The completion
  view is reduced to one agent-authored sentence; **Job details** opens the full structured contract
  on demand instead of occupying a permanent right column. Live browser review rendered all seven
  GLB previews, resumed a pending approval, exercised the modal, and confirmed the same-URL Yes →
  download transition.
- D039 hosted handoff: **Shepherd this asset** replaces the sensor-centric entry label. The
  conversation route now reuses the six-row structured inspection checklist and its checking-to-
  result replay instead of skipping directly from target confirmation to approval or completion.
  **Yes** persists acceptance through a progressively enhanced POST and changes the existing panel
  in place to **Ready to download**, with a direct fixed-GLB action and secondary evidence package;
  the redirect fallback remains. Live desktop and 390 x 844 checks confirmed an unchanged URL, no
  horizontal overflow, and no browser warnings or errors.
- D038 bounded conversation loop: form-led and durable hosted results now ask **Did we get it
  right?** Yes records durable acceptance; No opens one 1,000-character feedback field and begins a
  fresh agent turn. There is no hard-coded second attempt. The per-job limit is frozen from
  `ASSET_SHEPHERD_MAX_TURNS` (default 5; range 1–50). Completed outputs, assessments, and source/
  candidate renders move to `turns/turn-NNN/`; `conversation.json`, runtime state, hosted events,
  and current packaged provenance link the ordered turns. A three-turn regression proves the
  candidate/source transition, contiguous provenance, and remaining-limit calculation. Restart
  reconstruction restores the exact current GLB and frozen limit.
- D038 live continuation: the hosted OpenAI Responses workspace completed turn 0 on
  `clean_robot.glb`, accepted **No** plus feedback, archived the complete turn-0 output and four
  source renders, promoted the verified candidate to turn 1, and completed a fresh agent inspection
  and package. Turn-1 provenance records `conversation_turn_index: 1` and one prior turn with its
  source/output hashes, assessment/plan IDs, verification state, result-ZIP hash, and continuation
  feedback. Desktop and 390 x 844 browser checks expose one compact Yes/No review, reveal one
  feedback field only after No, have no horizontal overflow, and emit no browser warning or error.
- `docs/AGENT_LOOP_FLOW.md` diagrams intake → observe → assess → preview → approve → mutate →
  re-observe → verify → user feedback, including both loops, required resources, agent-visible
  tools, exact mutation boundary, durable artifacts, and stop/usage conditions.
- D037 live first-action loop: OpenAI Responses with `gpt-5.6-luna`/xhigh inspected the generated
  standing-robot fixture, requested source renders, identified source Y as semantic height, left
  rotation at zero, and requested scale, grounding, and index-preserving names. After approval it
  requested four candidate renders, recorded a 0.99-confidence source/candidate comparison, then
  independently verified and packaged `PASSED_WITH_REMAINING_WARNINGS`. Packaged provenance records
  planning tool call `call_nMY8tRPv1OATd9D2ZdQGTr2Y`, reassessment tool call
  `call_dKE85X4neVQgtd12pwNQxoPd`, both typed assessments, the approval, exact actions, and the
  `AGENT_VISUAL_REASSESSMENT` verification check. The seven-file ZIP contract remains unchanged.
- Long-bodied quadruped regression: a fresh browser run on source hash `fa757b02e150…` measured
  `0.471 × 0.463 × 0.998 m`, cited all four source views, identified Y as the 0.463 m semantic
  height and Z as body length, and produced a pure 7.5611814× scale preview for the confirmed 3.5 m
  target. Rotation is null/zero and grounding is false. The visible decision says **Normalize
  physical scale**, **Before height 0.46 m**, and **After height 3.50 m**.
- Agent-mode verification now checks exact approved preview bounds rather than dominant-axis policy
  heuristics, never invokes the legacy second planner, and requires a recorded visual candidate
  reassessment after executed actions. Agent assessment and candidate reassessment schemas are
  public; both are embedded in `provenance.json` with their initiating Strands tool-call IDs.
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
  sensing evidence, and adds the D036 gate to M9. D037 implements the first action/reassessment
  slice; the remaining gate is still tracked explicitly.
- Comparison-viewer recovery: the pinned `model-viewer` extension requires plain numeric
  `extra-model` offsets and enters a bad camera state when given the former unbounded
  `min-camera-orbit`/`max-camera-orbit` values. Both attributes are removed, initial and dynamic
  offsets are unitless, and the one shared WebGL scene now visibly renders source, repaired, and
  optional banana GLBs. Browser acceptance exercised Both/Before/After fits, metric axes, banana,
  desktop, and 390 × 844 layouts with no warning or error.
- Approval presentation now asks one compact question and immediately lists the exact physical and
  automatic display-name changes before Reject/Approve. The redundant source-file reassurance,
  duplicate metric tiles, hidden component disclosure, second checklist table, and recorded-evidence
  selector are removed.
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
- Tests: `uv run pytest` — 128 passed and the opt-in live-provider test skipped. D019–D044 acceptance
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
  bounded action plan. The intake agent records a semantic piece-count expectation while inspection
  keeps roots/nodes/meshes/primitives as separate structural facts; blocked jobs direct users back
  to the creation/export tool with recorded reasons.
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
- Single-step evidence: the authoritative left pane orients **Assets → Upload → Describe →
  Shepherd**. Agreement, inspection, decision, verification, and continuation stay inside Shepherd.
  The internal M8 harness remains covered without being the public entry. Every server-rendered
  state retains one `data-focus-area`.
- Workflow help: a large persistent `?` action sits immediately below **New asset** in both rail
  variants and opens `/how-it-works`. The page uses one agent sentence, three concise actions, and a
  start action without changing the workflow. Browser
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

The remaining D036 local acceptance work is unblocked and precedes AWS work. RW2 requires untouched
Debug Beetle and Cloudforge Workbench exports. Paid or remote M9 work requires
the user to configure or confirm a dedicated `asset-shepherd` AWS profile, selected Bedrock
region/model access, and a budget alert. AWS CLI v2.36.34 is installed per-user, but the current
process has a stale PATH and no AWS config or credentials file exists. A human-cleaned reference and
manual-time record remain required for the full RW4 comparison gate.

## Next action

Execute Step 1 of `docs/BEDROCK_DEPLOYMENT_RUNBOOK.md`: confirm AWS CLI v2, configure or verify the
dedicated `asset-shepherd` identity, select an account-available multimodal/tool-capable Bedrock
model and region, and confirm a budget alert. Before the Step 2 Bedrock gate, close the remaining
D036 changed-goal and ambiguous-orientation behavior cases and exercise a consequential continuation
turn whose fresh assessment requests a new action and approval. Preserve the current mutation scope,
exact authorization, durability, and invariant checks; do not restore deterministic target-dependent
planning.

RW2 registration resumes when the user supplies Debug Beetle. AWS resource creation is not
authorized yet; local OpenAI validation uses only the explicitly configured interim provider.
