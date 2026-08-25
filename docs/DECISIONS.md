# Asset Shepherd Decision Log

Record decisions that materially affect architecture, product behavior, cost, security, or scope.

## Decisions

### D047 — Separate virtual position welding from lossless vertex-tuple compaction

**Date:** 2026-08-24

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 agent-led sensing and disposition / M10 real-world evaluation

**Context**

The Computer Chip inspection contained 5,312 coincident positions. Blender's broad non-manifold
selection fell from 7,743 to 141 after a position weld, but that result alone did not prove the GLB
could be mutated without damaging its texture mapping. The user requested that Asset Shepherd detect
duplicate positions and repair them when possible. The user also clarified that target X/Y/Z metrics
are approximate fitting evidence and must never authorize non-uniform scaling.

**Decision**

Add two distinct deterministic topology facts. A read-only virtual weld groups exact POSITION values
to estimate underlying position topology. A stricter attribute-safe count groups only complete
byte-identical vertex tuples across every primitive attribute. Only the latter may become an
agent-requested `WELD_IDENTICAL_VERTICES` action. It is preauthorized as a lossless representation
compaction, never as topology reconstruction. Position-only welding, hole filling, remeshing, and
normal recalculation remain unavailable.

When confirmed X/Y/Z dimensions differ, treat them as approximate. Choose one deterministic median
uniform factor after any requested orientation change, preserve proportions, and record the residual
extent mismatch on all axes. Never expose or execute non-uniform scaling.

**Evidence and consequences**

The new sensor reproduces the chip evidence exactly: 7,811 source positions, 5,312 coincident
positions, a 2,499-position virtual projection, 91 boundary edges, 50 true non-manifold edges, and
11 inconsistently wound edges. It reports zero attribute-safe merges because all 5,312 duplicates
cross `TEXCOORD_0`; therefore Asset Shepherd does not weld this chip. A synthetic complete-tuple
duplicate compacts from five to four positions while preserving both triangles, all expanded
per-corner attributes, bounds, materials, resources, and glTF validity under independent
verification. Checked-in schemas and the on-demand job details expose the new provenance.

### D046 — Keep target intake API-compatible and move examples on demand

**Date:** 2026-08-24

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 hosted conversation UX

**Context**

Adding tight X/Y/Z targets changed the model-facing Pydantic field from one number to a fixed tuple.
Its generated JSON Schema used `prefixItems`, and the OpenAI Responses strict-output request failed
with HTTP 400 before the model could interpret any description. A successful structured response
could also redundantly populate `endpoint_detail` for a canonical Unity, Unreal, or Godot enum and
then fail the stricter server-owned semantic validator. The description screen exposed its three
examples through an unexplained question-mark control beside the field label.

**Decision**

Represent target dimensions at the model boundary as a closed `{x_cm, y_cm, z_cm}` object, then
convert it to the existing immutable tuple before constructing the target contract. Canonical
endpoint enums discard redundant model-authored detail; only `OTHER` may retain endpoint detail.
Provider failures keep diagnostics in server logs and show concise retry copy instead of raw HTTP
status language.

Replace the question-mark disclosure with a small **Show description examples** text link. It opens
one large native modal that first explains the four useful description clues and why they matter,
then gives exactly three examples: a rigged humanoid, a static prop, and an animated multi-part
system. The default screen does not gain another title or visible explanatory panel.

**Evidence and consequences**

The request-schema regression asserts that no `prefixItems` keyword is emitted. Analyzer tests cover
X/Y/Z conversion, canonical endpoint-detail normalization, safe 400/429 copy, and credential/body
redaction. A configured live OpenAI intake accepted a Unity humanoid description and redirected to
a durable workspace. Browser review confirms the plain link, modal sizing, lead explanation, three
examples, and absence of the former question-mark disclosure. The official OpenAI Responses API
continues to receive one strict JSON Schema request with `store: false`; the frozen target and
downstream deterministic authority boundary are unchanged.

### D045 — Freeze endpoint and three-axis target bounds; keep rejected candidates downloadable

**Date:** 2026-08-24

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 agent-led sensing / M10 evaluation

**Context**

A single target height can misdescribe wide, flat, or deep assets, while an engine-neutral target
omits useful Unity, Unreal, or Godot import expectations. A one-centimeter Computer Chip repair also
exposed two visual-review errors: Blender's fixed near-clipping distance made an isolated candidate
look absent, and a shared-scale source/candidate view could not by itself prove that a much smaller
candidate was missing. Automated rejection then made a mechanically valid candidate unnecessarily
difficult for its human owner to retrieve.

**Decision**

Version 3 target intent freezes the inferred endpoint as Unity, Unreal, Godot, or a described Other,
plus tight final-pose X/Y/Z bounds. The agent extracts these values from the user's description and
asks only when the minimum contract remains ambiguous. These are target-state dimensions, not raw
transform controls. Repairs remain uniform-scale-only; incompatible proportions are reported rather
than silently corrected with non-uniform scaling.

Visual reassessment uses three complementary evidence sets: isolated source views, isolated
candidate views, and a shared-scale comparison. Presence and appearance are judged from isolated
views; relative size is judged from the shared view. The local Blender acceptance camera derives
near/far clipping from measured bounds. Blender remains a local development and acceptance consumer,
not a hosted AgentCore dependency; the competition renderer remains a separate lightweight-runtime
decision.

An executed candidate rejected by automated verification remains directly downloadable under the
agent-assigned asset name. Download does not change the verification record, confer a verified or
project-ready label, or suppress diagnostics. The human may use the candidate or request another
agent turn.

**Evidence and consequences**

Strict schemas, intake tests, provenance tests, and route tests cover endpoint and three-axis target
state. A real 1 cm Computer Chip candidate renders visibly in an isolated 256 px Blender view after
proportional clipping; its deterministic preservation checks pass while its report-only topology
warning remains explicit. Browser acceptance exposes `Download candidate` before human acceptance,
and the route returns the exact candidate bytes as `computer-chip-candidate.glb` with private,
no-store headers. The official Khronos executable was not configured on this workstation, so that
optional validation layer was not rerun for this candidate.

### D044 — Public capabilities use three worker questions; yaw uses labeled visual evidence

**Date:** 2026-08-24

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 agent-led sensing / M10 evaluation

**Context**

Asset workers need a concise explanation of the defects Asset Shepherd looks for and why they
matter. A separate failure mode remained in orientation reasoning: the semantic front of an asset
can be obvious in an image while disagreeing with the file's declared forward direction. Bounds
and dominant extents cannot resolve that question.

**Decision**

Add a brain-icon **What it does** utility page organized around three questions: whether the GLB
will import, look as intended, and remain practical to ship. Keep the public page concise while the
existing authority document retains the exhaustive implementation detail.

Version the standardized render contract. In source glTF coordinates, +Y is up, +Z is forward, and
-X is right. Front/right/back/left renders identify camera positions +Z/-X/-Z/+X respectively.
The workflow agent compares semantic cues across all four views before requesting yaw. A clear
front on +X, -X, or -Z may request the corresponding typed Y-axis quarter turn; an already-correct,
symmetric, or ambiguous front requests no yaw. Deterministic code validates the typed action and
requires all four labeled views, but never invents the rotation. Existing cached renders without
the versioned coordinate contract are regenerated. Correct the former right/left source-axis labels.

**Evidence and consequences**

Route and focus-budget tests enforce one title and three public groups. Prompt and workflow tests
enforce glTF axis semantics, semantic rather than extent-based reasoning, and four-view evidence for
yaw. Blender scaffolding tests lock the source-to-Blender camera conversion. This adds no free-form
matrix input, automated yaw heuristic, or new mutation domain.

### D043 — The agent owns semantic assembly expectations; tools expose mesh health facts

**Date:** 2026-08-24

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 agent-led sensing / M10 evaluation

**Context**

After upload, **Piece count unspecified · valid GLB required** mixed a semantic target question with
an already-completed file-validity check. The inspector also lacked deeper facts about defective
edge relationships, fragmented index topology, unused vertices, and likely vertex-cache cost. Those
facts are useful to the workflow agent, but several are legitimate modeling choices rather than
universal failures.

**Decision**

The intake model derives an expected semantic piece count from the description. It defaults to one
and chooses a larger count only when the request clearly identifies a multi-object deliverable such
as a pair or set. The frozen target and asset-intent records preserve both the count and its concise
evidence. This count is not inferred from nodes, meshes, primitives, or edge-connected components,
and it does not authorize merge, split, or geometry repair.

Add a deterministic, read-only mesh diagnostic tool for triangle primitives. It measures boundary,
non-manifold, and inconsistently wound edges; edge-connected face components; unused and coincident
positions; average vertex reuse; and a FIFO-16 ACMR estimate. Non-manifold and inconsistent shared
edges are objective report-only defects. Unused data and very poor estimated cache locality are
report-only performance attention. Boundaries, component counts, coincident positions, and cache
estimates remain observations for agent interpretation because seams, hard edges, open surfaces,
and target hardware can make them intentional. No topology or optimization mutation is added.

Comparison fits use the viewer's camera interpolation instead of jumping. The optional banana
twirls into the shared scene and flattens before disappearing, with reduced-motion behavior honored.
Public downloads use an agent-derived asset-name slug; the contracted evidence ZIP keeps its
required internal `repaired.glb` name.

This decision supersedes D027 only where it prohibited an agent-authored semantic piece-count
expectation. D027's distinction between semantic pieces and structural counts, and its prohibition
on merge/split repair, remain controlling.

**Evidence and consequences**

Unit tests cover closed, non-manifold, duplicate/unused, and deliberately cache-hostile meshes.
Inspector tests prove typed measurements and report-only findings. Intake, provenance, prompt, and
route tests prove the semantic count is frozen and displayed without reintroducing structural-count
guessing. Browser acceptance proves plain Enter still inserts a line break, Ctrl+Enter submits, and
the comparison banana completes both animations. The diagnostic design follows established
concepts from Khronos glTF Validator, Blender and trimesh mesh diagnostics, and meshoptimizer's
cache metrics; actual target-GPU profiling remains authoritative for performance.

### D042 — Upload-first shepherding and a two-text screen hierarchy

**Date:** 2026-08-24

**Status:** ACCEPTED

**Decision owner:** User

**Milestone:** M9 hosted conversation UX

**Context**

The remaining form-led intake placed description and agreement before file selection, then combined
rules and upload in a nested two-step workspace. Its default view contained nine title-like texts:
the global page title, eyebrow, hero title, target subtitle, story disclosure, substep navigation,
step counter, panel title, and policy-card title. Those layers repeated workflow state instead of
helping the user perform the next action. The hosted rail also still showed Describe before Upload
and treated agreement as a visually separate phase even though objective GLB preflight is valid
without a target.

**Decision**

Make the authoritative public path **Assets → Upload → Describe → Shepherd**. Upload first validates
and stages one GLB and performs objective preflight only. Description then supplies the minimum
target contract. Target agreement and inspection both occur inside Shepherd, followed by any action
review, repair, verification, user feedback, and repeated agent turns. `/` redirects to the hosted
gallery so a stale form-led entry cannot become the apparent primary product.

Give every default screen one global workspace title and, only when useful, one agent-authored
informative sentence. Do not add visible eyebrow labels, step counts, nested section titles, card
titles, subtitles, context bars, or duplicate state summaries. Concise control labels and factual
row labels are not titles. Complete rules, evidence, and provenance stay available through closed
disclosures or the on-demand Job details dialog; a dialog may use the single accessible title it
needs.

Keep the historical form-led routes as the offline acceptance harness, but remove their visible
Rules/Upload sub-navigation and nine-title intake stack. Its deep intake link now renders one agent
sentence, the GLB control, and one collapsed **Review rules** disclosure.

This decision supersedes D041's Describe-before-Upload ordering and D012/D018 ordering for the
authoritative hosted surface. It does not change the agent/tool authority boundary, minimum target
contract, policy schema, supported actions, authorization, verification, or package contract.

**Evidence and consequences**

Route acceptance proves that `/` redirects to `/workspace`, the left rail orders Upload before
Describe, both start screens expose only one task, and neither contains any `h2` or `h3` title below
the one global `h1`. The staged GLB must pass extension, size, magic-byte, and parse validation before
description; refusal removes its temporary copy. The legacy intake likewise has one global title,
no subordinate heading elements, and retains complete profile values plus schema-validated advanced
fields inside disclosures. The seven-slot replacement remains destructive only after the new
durable workspace succeeds.

### D041 — Four-step hosted flow and one explicit approval surface

**Date:** 2026-08-24

**Status:** ACCEPTED

**Decision owner:** User

**Milestone:** M9 hosted conversation UX

**Context**

The hosted start screen combined the gallery, description, file upload, and replacement choice. At
approval, a second context bar and multiple headings repeated workflow position; the checklist
showed six results and then repeated those same six results in a tiny table. Attention icons did
not explain themselves, and the approval prompt said that three changes needed review while showing
only the physical normalization. A separate recorded-evidence question added another unrelated
control.

**Decision**

Use four hosted steps in the persistent left rail: **Assets**, **Describe**, **Upload**, and
**Shepherd**. The gallery only selects a new slot or resumes an existing workspace; description and
upload are separate screens; all inspection, action, approval, repair, verification, feedback, and
repeat turns remain in Shepherd. At seven assets, replacement is selected from the gallery before
description.

Each screen has one global title and no separate workflow context bar or approval subtitle. In Shepherd, show each of the
six checks once. A pass is a checkmark. An attention item uses a colored row and exclamation icon;
hover or keyboard focus on the icon explains the condition. Do not repeat the list as a status
table or display an obvious completed-count label.

At approval, show the exact selected plan in no more than three visible groups: physical
normalization, mesh display names, and node display names. Exact single-name changes stay visible;
larger name groups disclose their individual mappings on demand. Keep only Reject and Approve as
the decision controls. Remove the recorded-evidence question from the hosted product surface;
complete structured evidence remains available through **Job details**.

**Evidence and consequences**

Route acceptance proves gallery-only, description-only, and upload-only states, the four-step rail,
one six-row checklist with six hover explanations, no duplicate result table or count, three visible
change groups, and absence of the recorded-evidence control. Live browser review of the persisted
Polar Robot Puppy approval shows the active Shepherd step, one title, colored attention rows, and
the exact scale, mesh-name, and node-name changes before the decision buttons. Target inference is
performed once during the description transition and carried into upload; durable workspace and
Strands session state still begin after the GLB is accepted.

### D040 — Each named asset is one resumable conversation

**Date:** 2026-08-24

**Status:** ACCEPTED

**Decision owner:** User

**Milestone:** M9 hosted conversation UX

**Context**

The hosted completion view repeated its outcome as a large heading, a status card, and a dense
recap. The persistent Job Contract occupied a narrow right column, while returning users had no
visual list of processed assets. Filenames and opaque IDs stood in for asset identity even though
the intake agent had enough context to name the described model. The existing hosted runtime
already scoped Strands session storage by workspace ID and did not need another conversation store.

**Decision**

Make the hosted home a seven-slot visual asset gallery. The first semantic intake turn assigns a
concise asset name from the user's description; the deterministic offline analyzer supplies a
bounded fallback. A card resumes the exact durable workspace phase and source preview. Creating an
eighth workspace requires the user to select one of the visible seven to replace; no workspace is
silently evicted.

Keep each asset's existing `workspace_id` as its server-side conversation/session authority and
retain the workspace-owned `strands_state` directory. Do not introduce a shared transcript or a
second session database. Move the structured Job Contract into a modal opened by **Job details**.
At completion, show one compact sentence from the workflow agent instead of the prior headline,
status card, and recap; comparison, review, fixed-model download, and evidence remain available.

**Evidence and consequences**

Tests prove stable intake names, seven-slot enforcement, explicit replacement, gallery previews,
exact-state resume, distinct Strands session roots, one completion sentence, the details dialog,
and the existing inline acceptance transition. Existing records without a name derive a bounded
compatibility label and fall back to **Untitled asset** only when none is usable. Replacement is
destructive only after the new upload and preflight have been persisted successfully. Live browser
review showed seven rendered GLB cards,
resumed a pending approval, opened and closed the modal contract, and confirmed that Yes reveals
the fixed-model download at the same URL.

### D039 — Inspection progress and acceptance stay in the conversation

**Date:** 2026-08-24

**Status:** ACCEPTED

**Decision owner:** User

**Milestone:** M9 hosted conversation UX

**Context**

The active conversation route called its first action **Measure my asset**, omitted the progressive
inspection checklist already present in the form-led route, and handled result acceptance with a
full-page redirect that changed little on screen. The wording understated the agent workflow, the
missing checklist hid useful progress, and the acceptance reload interrupted the final handoff.

**Decision**

Call the action **Shepherd this asset**. Reuse the shared six-row inspection checklist in the hosted
conversation, replaying structured results from checking to pass, attention, or blocked status and
keeping row details collapsed. Persist **Yes** asynchronously and replace the question in place with
**Ready to download**, a direct fixed-GLB action, and a secondary evidence-package link. Retain the
ordinary POST/redirect path as the no-JavaScript fallback.

**Evidence and consequences**

Route tests cover the new copy, shared checklist, durable 204 acceptance transition, and accepted
download state. Live browser review confirmed that the URL does not change when Yes is selected,
the question disappears, the fixed-model and evidence actions appear, the six checks resolve, the
390 x 844 layout has no horizontal overflow, and browser diagnostics are empty.

### D038 — Repair is a bounded user-agent loop, not a two-pass workflow

**Date:** 2026-08-23

**Status:** ACCEPTED

**Decision owner:** User

**Milestone:** M9 durable agent conversation

**Context**

The D037 checkpoint completed one agent-authored action and visual reassessment, but its handoff
described the remaining work as a “second repair.” That wording implied a special retry. The product
requires an ordinary conversation: intake, analysis, repair attempt, user feedback, and as many new
evidence/decision turns as the configured usage allowance permits.

**Options considered**

- Add one hard-coded correction attempt after verification.
- Keep each attempt as a separate job and lose conversational/authorization continuity.
- Treat every completed candidate as a versioned state in one append-only conversation, with a
  configurable turn limit and a completely fresh action/approval boundary on every iteration.

**Decision**

Use the third option. A completed turn may be accepted or continued with up to 1,000 characters of
user feedback. Continuation archives all current output and rendered evidence, makes that turn's
candidate the next immutable source, resets per-turn assessment/plan/decision/verification state,
and invokes the same stateful Strands agent. Every consequential mutation therefore needs a new
assessment, typed preview, action hash, interrupt, approval, execution record, candidate
reassessment, and independent verification.

Freeze a per-job maximum from `ASSET_SHEPHERD_MAX_TURNS`, defaulting to five and validating the
range 1–50. The limit is persisted and restored rather than changing with the server environment.
Both the form-led result and durable hosted workspace ask only **Did we get it right?** Yes closes
the conversation; No reveals one feedback field and starts another turn when allowance remains.

Use `turns/turn-NNN/` for immutable prior output, assessments, and model-visible render evidence.
Persist ordered turn records in `conversation.json`, runtime state, hosted structured events, and
the current `provenance.json`. Records link source/output hashes, plan and assessment IDs,
verification state, result-ZIP hash, and continuation feedback. The current seven-file ZIP contract
does not expand; its provenance carries the prior-turn chain.

**Evidence and consequences**

The regression suite completes three ordinary turns, proves that each repaired GLB becomes the next
source, restores the current turn and frozen limit after reconstructing `AgentJob`, and rejects a
turn beyond the allowance. Existing authorization, source-preservation, schema, web, hosted,
restart, and package tests remain passing. `docs/AGENT_LOOP_FLOW.md` records the loops, resources,
tools, allowed mutations, durable state, and stop conditions.

A live hosted OpenAI Responses run also exercised **No** plus feedback after a clean verified turn.
The runtime archived the complete turn-0 package and source renders, promoted its candidate, ran a
fresh turn-1 inspection, and produced new provenance with one ordered prior-turn link. Browser
review passed at desktop and 390 x 844 without overflow or browser diagnostics.

Turn count is the implemented local usage guard. Provider token, time, and cost ceilings remain
deployment configuration and must fail closed. Changing the confirmed target or project rules is
not repair feedback; it still creates a new job and inspection.

### D037 — Live model authors the first repair preview and reassesses the candidate

**Date:** 2026-08-23

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 agent-orchestrated planner checkpoint

**Context**

D036 established that semantic height, pose, grounding intent, and repair choice belong to the
workflow agent. The implementation still filtered a target through a deterministic planner that
equated longest extent with vertical. The resulting quadruped was rotated onto its back, and the
same heuristic then declared the mistake correct. The interim Luna intake call had never inspected
the GLB or viewed a render.

**Options considered**

- Patch the quadruped orientation heuristic while retaining automatic grouped normalization.
- Let the model veto deterministic candidates after they are manufactured.
- Give the live Strands model objective measurements and standardized views, require one typed
  evidence-cited disposition/action request, compute only its exact bounded preview, and require a
  second model-visible source/candidate comparison before invariant verification.

**Decision**

Use the third option. In agent mode, legacy height, dominant-axis orientation, and grounding
findings are removed from the observation surface. The model chooses semantic height axis and each
supported scale, quarter-turn rotation, grounding, and display-name component. The preview layer
rejects malformed, no-op, uncited, repeated, unsupported, or non-repair action requests and never
adds a component. Consequential execution retains the exact Strands interrupt and approval hash.

For the authorized local transition, use the stateful OpenAI Responses adapter with
`gpt-5.6-luna`/xhigh until Bedrock is configured. Four local Blender source renders are tool-visible
evidence for physical conclusions. After execution, four new candidate renders must be compared by
the model and recorded before deterministic verification can run. Both assessments and their
originating Strands tool-call IDs are embedded in final provenance; the contracted ZIP filenames do
not change. The scripted provider remains a legacy/offline test double.

**Evidence and consequences**

The fresh quadruped run identified source Y as its 0.463 m standing height and Z as body length,
producing scale only and preserving its already upright, grounded pose. A separate paid live fixture
run completed inspect, render, plan, approve, execute, candidate render, visual reassessment,
independent verification, and seven-file packaging. The suite passes with 116 tests and one opt-in
skip.

This decision completes the first action loop; D038 generalizes it to an arbitrary bounded number
of versioned feedback/action turns. Ambiguous-orientation and materially changed-goal live
evaluations remain required. The non-fatal OpenAI/httpcore streaming-generator close warning observed after
interrupted Responses runs remains a dependency-level diagnostic to isolate before deployment.

### D036 — The agent owns sensing, assessment, disposition, and repair choice

**Date:** 2026-08-23

**Status:** ACCEPTED

**Decision owner:** User

**Milestone:** M9 hosted agent architecture correction

**Context**

The grasshopper-sized quadrupedal robot run exposed the actual authority error. The source was
already grounded on Y, but the deterministic inspector equated its longest Z extent with semantic
vertical, emitted `ORIENTATION_NOT_Y_UP`, created a rotation, and later verified success by checking
that the same longest extent had moved to Y. The intake model had inferred only use and size; the
scripted workflow did not visually reason about the model or choose the repair. Fixing that one
orientation heuristic would leave the same mistaken architecture in place for scale, grounding,
naming, assembly, and future tools.

**Options considered**

- Add a quadruped-specific orientation exception or improve the dominant-axis heuristic.
- Keep deterministic planning but allow the agent to veto generated candidates.
- Make deterministic components sensors, bounded action capabilities, enforcement, and proof while
  the agent chooses what to inspect, what the evidence means, what disposition to take, and which
  supported action and parameters to request.

**Decision**

Adopt the third option. `docs/AGENT_ORCHESTRATED_WORKFLOW.md` is the controlling start-to-finish
architecture. Sensors return observations without contextual verdicts. The workflow agent forms and
revises target-dependent conclusions, chooses whether to accept, investigate, ask, report, repair,
or stop, and initiates every mutation. The agent may call bounded preview tools for supported scale,
rotation, translation, grounding, and display-name primitives and compose them into an exact proposed
action. Deterministic code calculates consequences, validates schemas and capability limits, binds
approval, applies the authorized action, verifies invariants and declared postconditions, and
packages evidence. It never adds an unrequested variable fix.

Universal invariants remain non-negotiable and may block any call, but even a preauthorized
non-consequential mutation begins with an explicit agent tool call. Consequential actions retain exact
structured user approval. Standardized before/after renders become agent-accessible sensor evidence;
the browser comparison remains available to the user. After each mutation the agent re-observes the
candidate and may continue through fresh sensing and a fresh approval turn within explicit
operational limits.

The scripted provider remains a deterministic test double only. It cannot prove agent behavior. A
representative live workflow model must pass the corrected acceptance gate before M9 is complete.

This decision supersedes the deterministic semantic-planning and fixed-sequence portions of D002,
D018-D023, D026-D027, and D032-D034. Their durable state, target confirmation, narrow repair scope,
content boundary, exact authorization, source preservation, and independent-verification decisions
remain active. D035's viewer implementation remains useful, but its renders must also become recorded
sensing artifacts rather than user-only decoration.

**Evidence and consequences**

The controlling contract is amended to version 1.5, the agent operating contract is rewritten, and
the complete product path plus ten-part acceptance gate are documented. The present deterministic
prototype is now explicitly classified as a repair-engine test harness, not evidence that the
product is agent orchestrated.

Implementation has not been silently claimed. The next local milestone must separate sensor facts
from agent assessments, replace auto-generated candidates with typed action previews initiated by a
real model, provide rendered evidence to that model, and prove multi-turn reassessment. Existing GLB
scope and mutation primitives remain narrow; no topology, material, texture, rigging, animation,
Blender-hosting, or Unreal-plugin scope is added.

### D035 — One shared comparison scene uses the viewer's supported camera and transform syntax

**Date:** 2026-08-23

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 hosted conversation

**Context**

The completed workspace rendered metric axes, banana annotation, and HUD target boxes while both
GLBs were invisible. The HUD uses measured bounds and therefore remained plausible even when the
WebGL camera was invalid. Isolated browser probes proved both GLBs were valid and independently
renderable. The pinned `model-viewer` fork parses `extra-model` offsets with `Number`, so values such
as `1.5m` are invalid, and its former extreme `min-camera-orbit`/`max-camera-orbit` attributes put
the primary camera into a state where a loaded model did not draw.

The same approval state also repeated one decision across a headline, explanatory card, two metric
tiles, and buttons even though the exact component evidence can remain progressive detail.

**Decision**

Keep source, repaired candidate, and banana in the existing single shared `model-viewer` scene.
Supply plain numeric offsets to `extra-model`, including dynamic banana placement; remove the
unsupported orbit-limit attributes; and eagerly load this one result comparison. Keep fit controls,
metric axes, target boxes, shared rotate/pan/zoom, and the banana toggle unchanged.

Present normalization approval as one compact exact question plus Reject/Approve. Put component
evidence behind one `Details` disclosure and remove duplicate before/target tiles and source-file
reassurance.

**Evidence and consequences**

Rendered desktop acceptance shows source and repaired GLBs together at their measured relative
scales. Both, Before, and After fits execute; axes and the 20 cm banana toggle on; dynamic banana
offsets remain numeric; and browser diagnostics report no warning or error. A 390 × 844 pass keeps
the models, controls, HUD labels, and interaction hint within the viewport. Route tests enforce one
viewer, two numeric extra-model offsets, compact approval copy, one detail disclosure, and absence
of the removed reassurance.

The comparison remains a browser preview rather than verification evidence; deterministic and
independent verification continue to decide package readiness.

### D034 — Prose explains; structured controls decide

**Date:** 2026-08-23

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 hosted conversation

**Context**

The version-1 workflow prompt was primarily a seven-step tool script. It protected execution order,
but did not adequately teach the model the user's goal, distinguish explanatory prose from interface
controls, define the product's voice, carry the confirmed target into the run, or resist instructions
embedded in user and asset data. Tool descriptions were too short to tell a hosted model their
prerequisites, important outputs, and failure behavior.

**Decision**

Adopt the version-2 operating contract in `docs/AGENT_OPERATING_CONTRACT.md`. Treat the model as a
technical-art collaborator for one existing GLB. Keep the initial model description as the primary
open text input and use structured choices and buttons for later decisions. Let the model produce
free-text explanations of inference, evidence, failure, and next action, but never let prose approve
a repair, alter the Job Contract, or override a deterministic result.

Keep stable role, authority, tone, cross-tool order, stop conditions, topic limits, and private
content boundaries in the system prompt. Put exact tool behavior in concise tool descriptions. Append
the confirmed target and frozen policy as delimited JSON job data, explicitly untrusted as
instructions. Share the same prompt-injection and content boundary with the interim semantic-intake
model. New runs record prompt version 2 while old version-1 results remain loadable.

**Evidence and consequences**

Focused zero-network tests prove version provenance, stable/dynamic separation, confirmed intent and
policy delivery, prompt-injection treatment, shared refusal behavior, and the unchanged native
Strands approve/reject/verify flow. The public artifact schema accepts prompt versions 1 and 2 and
defaults new records to 2.

This establishes the contract a live Bedrock model must follow; it does not claim that the current
scripted hosted harness produces model-authored prose or that live conversational quality has passed
evaluation. Representative live traces remain required at the existing AWS checkpoint.

### D033 — The Job Contract owns conversation state across model providers

**Date:** 2026-08-23

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 hosted conversation

**Context**

The interim Luna integration uses OpenAI's Responses API, but an API endpoint and a coherent
multi-turn product are different things. The current intake request has `store: false`, supplies no
previous response or conversation identifier, and sends only the normalized asset description.
Luna proposes the typed intake fields once; it does not see GLB measurements, findings, plans,
decisions, verification, or later evidence questions. Meanwhile, the hosted scripted Strands path
already persists snapshots, but the Bedrock factory did not accept the same session configuration.

**Decision**

Keep provider conversation storage non-authoritative. The durable Job Contract, typed artifacts,
minimized event ledger, exact approval state, and Strands snapshot are the coherent picture of the
job. Model turns may consume that state and produce explanations or tool choices, but neither an
OpenAI response chain nor Bedrock-side history may replace it.

Keep Luna's current role explicitly limited to one-shot semantic intake. A future Luna-based full
conversation test must pass forward the relevant structured Job Contract and bounded recent turn
state; merely adding `previous_response_id` is not sufficient. When moving the workflow model to
Strands/Bedrock, construct the live agent with the same explicit session ID and isolated snapshot
storage contract used by the offline hosted runtime.

**Evidence and consequences**

Both scripted and live-agent factories now use one provider-neutral snapshot-session builder. It
requires both a session identity and an isolated storage root or fails closed. The opt-in Bedrock
test supplies those values, while zero-network tests validate the configuration contract without
credentials or model calls.

This wiring makes durable Bedrock conversation available, but the hosted application still uses
the scripted model until the contract's AWS profile, model access, region, cost, and live acceptance
conditions are satisfied. The current Luna intake must not be described as an end-to-end agent
conversation.

### D032 — Post-transform rules are planned up front; failed candidates are reassessed

**Date:** 2026-08-23

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M7 agent correction / M9 conversation and web product

**Context**

A grounded Z-up asset could receive an approved scale-and-orientation normalization whose rotated
bounds crossed below Y=0. The planner considered grounding only when the source inspection already
contained `NOT_GROUNDED`, so it omitted the translation created by its own rotation. Verification
correctly rejected the candidate when a fresh planning pass found one remaining repair. The
scripted agent then called its nominal correction tool, but that tool only reapplied the identical
authorized matrix and could never resolve a newly discovered post-repair condition. The final web
screen collapsed this verification failure into the same **Blocked / inspection-only** copy used
for unsupported source content.

**Decision**

Derive grounding from the bounds produced by the complete proposed scale-and-orientation matrix.
When ground contact is required, include grounding in the one grouped normalization whenever those
post-transform bounds fall outside tolerance, even if the original asset was grounded.

Replace the same-plan retry with one bounded candidate reassessment. The Strands agent calls a
deterministic tool that reloads the failed candidate, runs inspection again, and derives a fresh
registered plan. It never reuses the earlier approval and never executes the new plan silently. A
new consequential transform must be presented through a new explicit approval turn before a future
repair iteration may run. The deterministic core continues to own measurements, matrices, binary
mutation, verification, and packaging; the model owns tool sequencing, explanation, and approval
pause/resume.

Render verification failure as its own result state. Show the exact failed check and measured
post-repair finding, label the ZIP as diagnostics, and expose the failed GLB only as a clearly
marked **candidate not ready** comparison preview. Keep the shared camera, targeting HUD, fit modes,
metric axes, and banana scale aid available for diagnosis. Never package or label that GLB as
project-ready.

**Evidence and consequences**

The exact elephant-scale quadruped source now produces a normalization containing scale,
orientation, and derived grounding. A local rerun completes `PASSED_PROJECT_READY`, measures 3.5 m
on Y, places minimum Y at exactly 0, and produces an empty second plan. A regression fixture starts
grounded and Z-up, proves the source has no `NOT_GROUNDED`, and verifies the repaired result is
Y-up, grounded, and idempotent.

The previously persisted failed workspace remains useful negative evidence. Browser acceptance now
states that 30 checks passed, grounding remained at -1.75 m, and `SECOND_PLAN_EMPTY` expected 0 but
observed 1. It labels the candidate rejected, withholds it from the ZIP, and renders source plus the
rejected candidate in the shared viewer. The bounded-agent test proves verification runs once, the
failed candidate is reassessed once, the old plan is not reapplied, and the job remains failed.

This change does not authorize chained physical mutation under an old decision. A complete second
repair iteration still needs a versioned approval/provenance link before execution; until that
exists, reassessment ends with diagnostics and an explicit fresh-approval requirement rather than
a false retry.

### D031 — Repaired assets share one spatial before/after viewer

**Date:** 2026-08-23

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 conversation and web product

**Context**

Completed repairs were shown in two unrelated viewers. Separate cameras obscured the physical
scale change and made visual comparison harder, especially when normalization made one model tiny
relative to the other.

**Decision**

When at least one repair executes and the candidate passes verification, show source and candidate
in one `<model-viewer>` scene. Preserve each model's real scale and place the candidate to the
right of the source with a scale-relative gap. Provide three explicit fit targets—both, before, and
after—using the same orbit, pan, and zoom camera.

Project each model's world-space bounds into a minimal screen-space schematic overlay. Camera
changes update targeting corners, labels, and leader lines. If either model's longest dimension is
less than 18% of the other's, identify it as **Before model here** or **After model here** rather
than allowing it to disappear visually.

Add two optional scale aids. Metric X/Y/Z rulers follow the selected fit bounds and use 1/2/5
intervals with five major ticks per axis. **Banana for scale** loads a deterministic stylized GLB
at ordinary banana size (approximately 20 cm along its curve). Both aids are display-only and do
not enter repair or verification artifacts.

Serve the existing Google `<model-viewer>` 4.3.1 dependency from the application instead of a
public CDN. Preserve its Apache 2.0 license beside the unchanged distribution.

**Evidence and consequences**

Route acceptance covers the single shared scene, three fit modes, projected HUD hooks, local
viewer dependency, metric ruler logic, and the banana asset's measured size. Browser evidence
covers the very large source versus 1.8-meter candidate: the small candidate remains targeted in
the combined view; After fit recenters it; the axes change to 0.5-meter intervals; and the banana
overlay reports 20 cm. The source GLB, repaired GLB, contracted ZIP, repair authority, and
verification gates are unchanged.

### D030 — Public help explains the task, not the release

**Date:** 2026-08-23

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 conversation and web product

**Context**

The help page ended its workflow explanation with a product-version heading, an implementation
scope inventory, and a repair-domain caveat. Those facts describe the prototype to its builders;
they do not help a person understand what to do with an asset.

**Decision**

Public help is task-oriented and limited to three steps: describe and upload, review what was
found, and download the result. It does not present release numbers, roadmap framing, internal
tool names, provenance terminology, or a generic repair inventory. Limitations appear in the
workflow only when a particular asset or requested outcome makes one relevant.

Remove implementation version labels from the active-rule proposal and user-visible finding
descriptions as well. Versioned policy and artifact metadata remain unchanged in durable records;
only their unsolicited presentation is removed.

**Evidence and consequences**

Route acceptance requires exactly three help steps and rejects the removed scope, version, tool,
and provenance copy. Desktop and mobile browser checks cover the rendered hierarchy and overflow.
Deterministic checks, repair eligibility, authorization, verification, packaged evidence, and
policy versioning are unaffected.

### D029 — Inspect is one progressive result, one summary, and one question

**Date:** 2026-08-23

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 conversation and web product

**Context**

Inspect exposed three dense columns containing target assumptions, measured facts, previews,
findings, policy evidence, and proposed actions. The surrounding page then repeated the target
story and workflow navigation. Accurate evidence was competing with the one conclusion and one
decision the user actually needed.

**Decision**

Present Inspect as exactly three sequential areas. First, replay the completed deterministic work
as one compact check log: each row briefly says **Checking …** and resolves to a green check or an
attention marker. Second, generate a concise structured summary containing measured size,
topology, and resources, one compressed sentence for normal domains, and no more than three grouped
attention areas. Third, ask **Do these issues look fixable?** before exposing the repair decision.
Direct navigation or submission to Decide remains gated until that acknowledgement.

Keep the complete expectations, findings, rule provenance, measurements, plan candidates, stages,
frozen policy, and preview in one closed **More details** table. Remove the repeated target-story
panel, duplicate Inspect/Decide/Download rail, redundant section headings, and public copy about
internal source or guardrail mechanics. Internal authorization, unsupported-domain, mutation, and
verification invariants do not change.

Both upload controls now say **Choose or drop your GLB**. Click-to-choose and Windows Explorer drop
share one validated file state; a drop must contain exactly one `.glb`. If semantic intake is
declined, create no job or uploaded-file copy and show only a concise refusal, such as **Sorry, I
can't engage with this type of content. Let's work on something else.** Exact punctuation is not a
contract.

**Evidence and consequences**

Route acceptance proves the three-area result hierarchy, closed details, acknowledgement gate,
concise decline response, no declined-content storage, and shared chooser/drop implementation. A
real-browser run with the broken fixture confirms the progressive check transition, three grouped
attention areas, hidden 48-row detail table, preserved chooser path, and empty browser diagnostics.
At 1366 × 900 the confirmation question appears in the same working view; at 390 × 844 the page has
no horizontal overflow and the opened table scrolls within its own container. No repair operation,
policy field, model authority, artifact contract, or acceptance behavior is added.

### D028 — Apply progressive rule-of-three disclosure and one contextual feedback path

**Date:** 2026-08-23

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 conversation and web product

**Context**

The target proposal rendered six assumption cards, provenance labels, explanatory text, a separate
evidence disclosure, confirmation, correction, restart, and implementation notes on one surface. Although
the facts were accurate, the interface exposed the implementation taxonomy and required too much
simultaneous reading and choice.

**Decision**

Present exactly three closed groups: **Purpose**, **Scale and pose**, and **Structure**.
Each group shows one agent-written conclusion and reveals at most three supporting facts only after
the user opens it. Replace the competing controls with one question, **Did I get it right?**, and
two answers: continue to inspection or edit the prefilled description and try again. The same text
may be resubmitted to request a retake.

Add one reusable `/feedback` page. Links provide an allowlisted workflow context, an opaque local
reference, and a safe app-local return path. The page offers four bounded reasons and an optional
1,000-character note. Development feedback is written atomically below the configured work root;
no network service, credential, analytics SDK, or new product authority is introduced.

**Evidence and consequences**

Route acceptance verifies the three-group budget, binary decision, reusable feedback context,
reason bounds, note limit, and local JSON record. Desktop and 390 × 844 browser review show the
complete default decision surface without horizontal overflow or browser warnings. Existing typed
target, deterministic inspection, exact repair authorization, source preservation, and independent
verification behavior remain unchanged.

### D027 — Replace use-mode selection with an expectation-to-evidence contract

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 conversation and web product

**Context**

The target-adjustment UI exposed `static game asset`, `rig-ready character`, and `playable animated
character` in a dropdown. That presentation made them look like validation presets with different
repair behavior. They are not. The current repair engine has one static-GLB domain; non-static
intent is retained only to state the narrowed external handoff honestly. The same screen also made
it difficult to distinguish assumptions inferred from a user's description, universal safety
invariants, measured GLB facts, and the resulting plan.

**Decision**

Remove the intended-use dropdown from confirmation, clarification, and the hosted workspace.
Corrections are natural-language edits that run through the same schema-validated analyzer. Before
upload, list every active target assumption with its source and list the universal checks
separately. After inspection, organize the active view into three areas: target expectations,
deterministic GLB observations, and findings plus action plan. Label finding authority in public
language. If the registered plan is blocked, explicitly recommend returning to the model creation
or export tool with the recorded reasons.

Intended use remains typed provenance and a support-boundary input, not a repair preset. Static
intent receives the full supported workflow. Character intent receives static inspection and an
external rigging/animation handoff. Assembly expectations remain explicitly unspecified: the tools
report roots, nodes, meshes, and primitives, but no semantic piece count is invented and no
merge/split repair is added.

**Evidence and consequences**

Route acceptance proves that complete and missing-intent screens contain no target-use selector,
natural-language reinterpretation updates the typed proposal, and inspection renders assumptions,
measured assembly facts, finding authority, candidates, report-only warnings, and blocked handoff.
The full offline suite passes with 100 tests and one opt-in live-provider skip. Desktop and 390 × 844
browser review show the expectation sheet without horizontal overflow; the compact document width
is 375 pixels inside a 390-pixel viewport.

No new repair type, model authority, transform control, topology operation, or GLB mutation is
introduced. A future semantic assembly contract must define measurable evidence before it can
become a finding or repair goal.

### D026 — Check authority is explicit and validation is layered

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** Codex

**Milestone:** M10 evaluation strengthening

**Context**

The product already separated model proposals from deterministic repair authority, but findings and
verification did not make that distinction uniformly visible. The selected Python glTF validator
also covers only part of the specification, and count-only preservation cannot prove that material,
texture, accessor, or binary content remained unchanged.

**Decision**

Classify every finding and verification check as a frozen project-policy assertion, universal
invariant, objective source diagnostic, or external-consumer evidence. Preserve exact policy-rule
sources on findings. Add direct primitive/accessor and resource-graph diagnostics, deep semantic
section and binary-payload preservation checks, an optional pinned official Khronos validator
adapter, and typed equally-framed render comparison. Keep all newly detected topology/resource
issues report-only unless they violate glTF validity or an existing universal safety rule. Add no
repair operation.

The LLM remains limited to proposing supported intended use and semantic target height. Those
values pass a confidence gate and explicit user confirmation before becoming policy. Universal
validity, authorization, and preservation checks cannot be changed by the model, the user's target
description, or advanced policy fields.

**Evidence and consequences**

Acceptance tests distinguish model/user-derived policy findings from universal blockers, corrupt
attribute cardinality and topology intentionally, and prove that a parseable material mutation
fails deep preservation. The official validator reports zero errors for the clean fixture and the
same two pre-existing `ACCESSOR_MIN_MISMATCH` errors for untouched Patchling and Shader Lantern.
The strengthened Shader Lantern workflow introduces no official errors and retains them as explicit
source warnings. Typed render comparison reproduces the established four-view maximum MAE of
0.081863/255 for raw versus Shepherd and 0.000334/255 for Shepherd versus Blender re-export.

The native validator is an optional local/release tool, not a Python or hosted Blender dependency.
If configured, failure to execute it fails verification. A source-retained official error prevents
a zero-error conformance claim but does not authorize out-of-scope accessor repair.

### D025 — Target confirmation uses space for readable scale and optional rationale

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 semantic-intake presentation

**Context**

The concise target confirmation was understandable, but its 920-pixel content cap forced a very
large headline into narrow lines and left substantial workspace unused. Tiny objects were also
shown as decimal meters, such as `0.02 m`, rather than in the unit a person would naturally scan.

**Decision**

Use a wider confirmation canvas and a smaller, bounded headline scale. Format sub-centimeter
targets in millimeters, sub-meter targets in centimeters, and larger targets in meters while
preserving canonical centimeters in the contract. Keep the primary view minimal, but add one
collapsed **Why this target?** disclosure containing the already-recorded use and scale evidence
and a reminder that the proposal is interpretation, not source measurement.

**Evidence and consequences**

Route acceptance covers readable unit selection, model evidence, the source-measurement boundary,
and unchanged adjustment/confirmation behavior. Browser review covers the wider layout, attention
budget, disclosure behavior, and horizontal overflow; the existing compact breakpoint stacks the
decision row and makes its action full-width. No additional model call, policy field, repair scope,
or authorization behavior is added.

### D024 — One-command Windows launcher protects the local OpenAI key

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 local semantic-intake ergonomics

**Context**

The user cannot reliably paste multiline PowerShell commands and should not need to place a raw API
key in command text, shell history, a repository file, or a persistent environment variable.

**Decision**

Provide two repository scripts, each invoked with one line. `Save-OpenAIKey.ps1` reads the key through
a hidden secure prompt and stores only Windows current-user protected ciphertext under local app
data. `Start-AssetShepherd.ps1` unlocks it for the same Windows user, makes it available to the web
process for the duration of the command, restores any prior process state in `finally`, and clears
the temporary byte buffers. No key material or encrypted secret is written inside the repository.

**Evidence and consequences**

Both scripts pass Windows PowerShell 5.1 parser and runtime validation. Static acceptance requires
hidden input, current-user data protection, an external local-app-data path, scoped environment
injection, and cleanup. This is a local Windows development convenience, not the production secret
mechanism; Bedrock deployment must use the approved hosted secret-management design.

### D023 — Provider-neutral semantic intake uses OpenAI Luna until Bedrock

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 conversational intake

**Context**

The D022 explicit-text extractor made the entry screen look like a questionnaire: descriptions such
as “a mountain of goop” produced two required fields even though an LLM can propose a reasonable
game use and semantic scale. The repository already used Strands for workflow sequencing, but the
running intake path did not invoke a model. The user authorized interim paid OpenAI API use with
`gpt-5.6-luna` at `xhigh` reasoning and directed that Bedrock replace it later.

**Decision**

Add a provider-neutral `TargetIntakeAnalyzer` boundary. The normal CLI web process uses the OpenAI
Responses API with `gpt-5.6-luna`, `xhigh` reasoning, low answer verbosity, strict structured output,
and `store: false`; `--offline-intake` retains the deterministic explicit-text acceptance path.
Only the normalized description is sent to the intake provider, never the GLB. Server code validates
the returned `TargetIntakeInference`, applies the existing 0.8 confidence gate, and constructs
`TargetIntakeContract` itself. Provider and model identity are retained in that contract.

The model should propose a supported use and plausible semantic vertical height whenever one
interpretation is useful enough for confirmation. It asks a natural-language follow-up only when a
required field remains genuinely ambiguous. The proposal is not a fact or authorization: the user
may adjust it and must explicitly confirm it before policy inspection. Model output cannot specify
transforms, policy safety settings, repair candidates, approvals, mutation, verification, or
readiness. Bedrock will implement the same interface and schema rather than changing downstream
contracts.

**Evidence and consequences**

Mock-transport acceptance verifies the exact Luna/xhigh structured request, semantic use/scale
proposal, confidence fallback, safe provider errors, and credential-free offline selection. Web and
durable-workspace acceptance verify concise questions, editable proposals, persisted analyzer
provenance, restart-safe adjustments, and exactly-once commands. This changes intake collaboration
only; the deterministic workflow, policy family, explicit physical approval, source preservation,
and repair scope are unchanged.

### D022 — Minimum target-intake contract asks only for unresolved required information

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M8/M9 conversational intake correction

**Context**

The intent flow should feel like an agent understanding what the user is trying to make, not a
fixed questionnaire that repeats information already present in the description. At the same time,
the deterministic policy resolver cannot safely derive a physical normalization without an exact
intended size, and source measurements describe what the file currently represents rather than what
the user intended.

**Decision**

Define a strict, versioned `TargetIntakeContract` as the boundary before target confirmation. Its
minimum required information is a normalized description, one supported intended-use enum, and a
positive intended real-world target height. Each populated target field requires concise evidence,
source, and confidence of at least 0.8; absent, ambiguous, conflicting, or lower-confidence values
are represented as explicit
`missing_fields`. Ask only for those fields. Never ask the user to repeat an already-supported
answer, never infer intended height from measured source bounds, and never treat conversation text
as repair authorization.

The ordinary entry form therefore asks only what the user was trying to make. The local
zero-network reference extracts explicit supported use and measurement phrases, displays only the
unresolved questions, and requires one final confirmation of the complete target. The durable
hosted path writes `target_intake.json`, persists clarification evidence and exactly-once command
state, and consumes the completed draft without re-requesting its values. A future Bedrock model
must produce the same validated schema. Grounding, tolerances, naming, and budgets remain policy
resolution concerns and do not enlarge the minimum questionnaire.

**Evidence and consequences**

Acceptance covers complete extraction, missing-height-only and missing-use-only clarification,
conflicting use language, invalid values, schema inconsistency, final-confirmation gating,
job-snapshot persistence, hosted application restart, and the unchanged approved deterministic
workflow. This decision adds no model call, repair operation, appearance inference, AWS activity,
or editable safety rule. It refines D018–D021 intake without weakening their confirmation, policy,
authorization, or verification boundaries.

### D021 — One parameterized policy family replaces user-visible scale baselines

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M8/M9 policy-resolution correction

**Context**

The intent flow already asks the user what the asset should become and freezes intended real-world
height. Asking the same user to choose between `Human-scale static mesh` and `Compact static mesh`
made them reverse-engineer an implementation detail, while asking for height again contradicted the
confirmed target story. Selecting the nearest preset also discarded useful semantic information in
the description, such as whether an asset is meant to stand, hang, or hover.

**Decision**

Use one immutable, versioned `Unreal Static Game Asset Policy Family` as the parameter source for
new form-led and hosted conversational jobs. The agent proposes a complete job-specific
`ProjectProfile` from confirmed typed intent and bounded semantic derivation. Target height comes
from the already-confirmed story; tolerance scales with intended height; explicit supported
grounding language may set ground-contact policy; and unspecified naming, resource budgets,
orientation, authorization, and safety values retain family defaults. A source asset's observed
defects may inform questions and evidence but may not relax the target policy to make that source
pass.

Show the proposed rules before inspection, keep complete active parameters and their sources
inspectable, and permit advanced edits only for the existing supported `ProjectProfile` fields.
Validate and freeze the result server-side with a resolved identifier, family identifier, explicit
differences from the family, per-rule source, version, and canonical hash. The legacy
`base_preset_id` provenance field mirrors the family identifier for schema compatibility. Changing
intent or any supported adjustment creates a new job. Never expose raw transforms or make safety
classes, source preservation, unsupported repair domains, verification invariants, or
authorization behavior editable.

Historical repository presets remain byte-for-byte immutable and valid for reproducible CLI,
fixtures, and old evidence. They are no longer choices for new conversational jobs. This decision
supersedes only the user-visible preset-selection and nearest-preset portions of D013, D019, and
D020; their safety, durability, Job Contract, and deterministic workflow decisions remain active.

**Evidence and consequences**

Acceptance covers removal of named baseline controls and duplicate height entry, intent-derived
height/tolerances, suspended versus grounded descriptions, family-default fallback, server-side
advanced validation, immutable historical policy bytes, family/resolved provenance, per-rule
source citations, distinct jobs after rule or intent changes, and unchanged inspect through package
behavior. This decision adds no repair operation, appearance inference, paid model call, AWS
activity, or editable safety boundary.

### D020 — Durable local hosted reference uses structured workspace state and Strands snapshots

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** Codex, implementing approved D019

**Milestone:** M9

**Context**

D019 requires the exact approval interrupt and deterministic job to survive browser, application,
and agent-runtime restart without expanding the repair engine or depending on paid infrastructure
during local development. The existing M8 web registry retained Python objects only, while the
deterministic artifacts already contained most stage outputs.

**Decision**

Implement a versioned filesystem-backed hosted reference path at `/workspace`. Persist one private
atomic `workspace.json`, profile-free `preflight.json`, the frozen profile and intent, structured
event ledger, command idempotency records, retention/deletion status, and artifact references inside
each isolated workspace. Store the Strands agent's native session snapshot separately with its
exact interrupt state. Reconstruct `AgentJob` from private runtime state plus validated contracted
artifacts after restart. Keep the M8 form-led routes and outputs unchanged.

Before target confirmation, allow only `PreflightResult`: source identity, glTF structure, bounds,
transform facts, supported-feature counts, resource counts, and declared material metadata. Derive
the closest immutable preset by target height, apply explicit supported overrides, validate the
result as `ProjectProfile`, and freeze its provenance. Treat ordinary dialogue as non-authorizing;
only the exact structured interrupt response may resume repair. Store bounded evidence categories
and references rather than raw questions, routine response prose, hidden prompts, or chain of
thought in hosted provenance.

This local storage shape is a reference and test harness, not the final remote concurrency model.
An AWS deployment must replace local atomic-file coordination with an appropriate isolated durable
store and retain the same schemas, idempotency semantics, privacy boundary, and acceptance tests.

**Evidence and consequences**

Automated acceptance covers profile-free preflight, schema-valid advanced rules, narrowed-goal
agreement, clean no-mutation control, native interrupt restoration in a new store/application,
structured chat non-authorization, duplicate decision replay, verification, and exact ZIP output.
The rendered browser path was checked through preflight, approval, and completion with the source
and candidate previews visible and no console warnings or errors. This decision authorizes no AWS
activity, paid invocation, new repair operation, or public release.

### D019 — Conversation-led hosted workspace with typed target and objective preflight

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9

**Context**

The M8 form-led product safely completes the full static-GLB workflow, but the remaining human
ambiguity is intent: what the asset should represent, its real-world size and use, and which
unsupported goals require an external handoff. D012 and D018 required agreement before upload,
which prevented measured source facts from improving follow-up questions. The user asked for a
Codex-like collaboration around one asset, and a completed ChatGPT Pro review recommended a
conversation-led, contract-anchored workspace while explicitly rejecting a chat-only product.

**Options considered**

- Keep the M8 form-led interaction as the only product interface.
- Replace structured state and approval with an open-ended chat interface.
- Make conversation the primary hosted navigation while retaining a visible Job Contract, typed
  confirmation, deterministic execution, and exact structured approval.

**Decision**

Adopt the third option for the M9 hosted path. Keep the M8 form-led product intact as the reference,
offline acceptance harness, comparison baseline, and fallback.

After minimal context, permit GLB upload and objective measurement-only preflight before final target
agreement. Clearly label this state as measured source facts without an agreed target. Do not create
policy-relative findings, a registered repair plan, an approval interrupt, a readiness result, or
any mutation until the user explicitly confirms typed target state.

Show a persistent structured Job Contract beside the conversation. It contains source status,
target, rules, measurements, findings, plan, decision, verification, and package status. Ordinary
users confirm a schema-valid job copy derived from the nearest immutable trusted preset and explicit
target overrides rather than choosing a named scale baseline. Preserve the resolved policy's ID,
base preset, overrides, version, canonical hash, and complete read-only rules. Advanced users may
edit only fields already supported by `ProjectProfile` and the deterministic engine. Changing
confirmed intent or rules creates a new job.

Preserve `original_intent`, a narrower `supported_job_goal`, and an explicit support status.
Playable-character, rigging, skinning, or animation requests may proceed only after the user accepts
a static-mesh or inspection-only goal; the final result must disclose the external handoff and may
not claim unsupported readiness.

Conversation may decide what to ask and explain only recorded evidence. Appearance-related
statements require deterministic material or texture metadata and must be classified as supported,
contradicted, or not evaluated. The human grants or rejects consequential authorization through the
exact structured interrupt. The deterministic core validates and enforces its binding. Chat prose
and the agent have no authorization role.

Persist enough structured state to survive browser, application, and agent-runtime restart with
exactly-once mutation and packaging. Hosted provenance records confirmed typed state, versions and
hashes, deterministic tool-call ledger, action and decision events, artifact references, and
external handoffs. Do not package chain-of-thought, hidden prompts, routine prose, or a raw
transcript. Prefer structured intent plus a canonical hash in the package; raw description text is
private short-lived job state or an explicit opt-in.

Limit M9 to dialogue, typed-state confirmation, existing narrow tools, exact approval, durable
resume, evidence-grounded follow-up, and the unchanged registered repair pipeline. Defer every new
repair operation, visual-model judgment, model-generated transforms, conversational authorization,
hosted Blender or Unreal workers, multi-asset workspaces, cross-job memory, accounts and teams,
shared profile libraries, arbitrary policy upload, general shell access, and open-ended editing.

This decision supersedes D012 and the ordering portion of D018 for the hosted M9 path. Their current
form-led behavior remains the executable reference until the versioned M9 implementation passes its
gate. D013's frozen-policy and editable-safety boundaries remain controlling.

**Evidence and consequences**

The accepted direction and its seven-part review are recorded in `docs/INFLECTION_POINT.md`.
`docs/PROJECT_CONTRACT.md` version 1.1 incorporates the hosted input, web, Strands, privacy,
durability, and M9 gate changes. The GLB-only boundary, source preservation, registered repair set,
exact human approval, independent verification, seven-artifact package, and real-world validation
addendum are unchanged.

The interaction change remains a hypothesis until controlled comparison shows better target
accuracy, completion time, or comprehension without worse unsafe authorization, false readiness, or
verified-output rate. This decision does not authorize AWS spending, paid model invocation, resource
creation, or any new repair capability.

### D018 — Confirmed asset intent replaces audience-mode selection

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M8 / M9 preparation

**Context**

The three audience presentations helped explore product language but asked who the user was before
capturing what they actually needed. Real-asset diagnosis also showed that intended height and a
description of the desired asset are essential context: measurements alone cannot decide whether a
99-meter lantern should be a prop, or whether a static character was intended to become playable.
The user described the desired experience as working on an asset together in a Codex-like
conversation, eventually using Bedrock rather than Codex.

**Options considered**

- Keep the role selector and add more questions to every audience route.
- Let free text directly select repair operations or allow a model to decide target state.
- Replace the selector with a bounded target-story dialogue, require explicit agreement, and feed
  only confirmed structured fields to the deterministic workflow.

**Decision**

Make `/` ask what the user was trying to make, whether the target is a static asset, rig-ready
character, or playable animated character, and its intended real-world height. Draft an exact
first-person target story and require the user to agree before policy selection or upload.

Freeze the confirmed record with a version, opaque ID, original description, target-use enum,
height in centimeters, exact story, confirmation timestamp, and canonical SHA-256. Write
`intent.json` beside the job inputs and embed the same record in `provenance.json`. The agreed height
becomes the target-state profile parameter; if it differs from a preset default, derive a validated
custom profile copy. Never expose or accept a raw transform through this flow. Changing intent or
rules creates a new inspection/job.

Treat the description as untrusted metadata, not executable instructions, repair authorization, or
deterministic evidence. A later Bedrock/Strands conversation may ask follow-ups and construct the
same schema, but the deterministic engine remains authoritative for measurements, repair planning,
approval, mutation, verification, and readiness. Rigging, skinning, animation, material, texture,
topology, and other unsupported repair domains remain out of scope.

Retire the audience selector from the primary UI and redirect legacy `/stories/{role}` bookmarks to
the new entry point. Preserve the two-column shell, one-visible-step attention budget, versioned
policies, grouped normalization approval, and Inspect → Decide → Download job flow. This decision
supersedes the role-navigation portions of D008, D010, and D014–D016 without invalidating their
progressive-disclosure or layout evidence.

**Evidence and consequences**

Acceptance covers invalid-intent rejection before job creation, explicit agreement before upload,
non-static scope disclosure, canonical hash validation and tamper rejection, frozen intent in job
and package provenance, height-derived target policy, distinct jobs for intent or rule changes,
legacy-route redirects, and the existing approved, clean, invalid, and inspection-only workflow
paths. The current local path remains deterministic and zero-network. Adaptive Bedrock follow-ups,
semantic comparison of a description to appearance, persistent conversations, and AWS deployment
remain future work behind the existing M9 credential and cost-control checkpoint.

### D017 — Scale-oriented labels preserve immutable legacy profile identity

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M8

**Context**

The first preset appeared in the UI as `Unreal Indie Robot`, which suggested a robot template or a
different repair feature set. Direct comparison of both profile documents showed that engine and
asset type, orientation and grounding, naming, budgets, auto-renaming, and approval behavior are
identical. Only target height and tolerance differ.

**Options considered**

- Keep the asset-specific names and explain them in more text.
- Rename the profile IDs and JSON content, invalidating immutable hashes and existing provenance.
- Use truthful human-readable scale labels in the web presentation while retaining canonical
  profile bytes and identifiers as legacy evidence.

**Decision**

Present `unreal-indie-robot-v1` as **Human-scale static mesh**, with a 1.8 m target and 1.7–1.9 m
accepted range. Present `small-stylized-static-mesh-v1` as **Compact static mesh**, with a 1.2 m
target and 0.9–1.5 m accepted range. Ask users to choose the asset's intended scale. State through
the collapsed rule review that all other current behavior is identical. Do not modify either preset
file, canonical hash, profile ID, frozen job policy, or historical validation artifact.

**Evidence and consequences**

Web acceptance requires both scale-oriented labels and ranges and rejects the old asset-specific
display name. Profile IDs remain trusted server inputs and remain visible in expanded provenance.
Choosing a preset changes only `HEIGHT_OUT_OF_RANGE` evaluation, the derived scale factor, and any
resulting physical-normalization proposal; it does not unlock different repair capabilities.

### D016 — Large-type, disclosure-first presentation

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M8

**Context**

The clarified application frame matched the requested geometry, but the workspace still rendered
too much explanatory and policy text at small sizes while leaving useful whitespace around it. The
user asked for less default text, larger content that uses the workspace, and hover or expansion for
details.

**Options considered**

- Increase every font without changing information density.
- Remove policy and finding evidence from the product.
- Keep the complete evidence in the document, but expose only the current choice or finding title
  by default and enlarge the primary interaction surfaces.

**Decision**

Make the Help workspace one large question plus three large choice cards. Move each audience's
question to the choice's hover title and remove repeated explanatory paragraphs. Enlarge the
audience heading, panel headings, workflow labels, navigation tiles, policy choices, metrics, and
finding titles. Collapse preset summaries and complete active parameters under `Review rules`,
finding descriptions and policy provenance under `Details`, and upload behavior under
`Upload details`. Keep all content in accessible server-rendered HTML and preserve the single-step
workflow.

**Evidence and consequences**

Acceptance asserts that intro/promotional copy and secondary workflow captions are absent by
default, both policy summaries remain inside collapsed reviews, and every finding retains a detail
disclosure. Desktop browser evidence measures a 1160 px chooser with three 376 × 260 px choices and
a 112 px question; the Rules step shows only two policy names, two review controls, customization,
and the next action. Inspect shows four enlarged metrics and ten compact finding headings, with
policy evidence restored when a detail is expanded. Compact review retains a 76 px left pane, 32 px
workflow headings, one-column 274 px policy cards, and zero horizontal overflow. Backend behavior,
policy completeness, provenance, authorization, repair, and package output are unchanged.

### D015 — Clarified two-column frame replaces narrow-rail proportions

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M8

**Context**

D014 correctly established five persistent presentation modes and a one-step workspace, but its
112 px icon rail did not match the user's intended spatial hierarchy. A follow-up wireframe made the
layout explicit: a dedicated logo cell above a wider three-tile style selector on the left, a title
cell above the workspace on the right, and aligned dividers forming a two-by-two application frame.

**Options considered**

- Keep the narrow icon rail and treat the clarification as documentation only.
- Move the selector into the workspace or redesign the workflow itself.
- Preserve D014's behavior while widening and restructuring the left pane to match the clarified
  frame.

**Decision**

Use a 248–320 px desktop navigation pane below the placeholder logo cell. Make Game developer,
3D artist, and Technical artist prominent full-width tiles. Keep Help me choose and Advanced user
as smaller secondary tiles in the same pane. Align the 96 px logo cell exactly with the workspace
title header. At compact widths preserve the left-side orientation as a 64–76 px icon pane with an
aligned 72 px header. Do not change role routes, policy controls, workflow steps, job state, repair
authorization, or product scope.

**Evidence and consequences**

Web acceptance asserts exactly three primary style tiles, two secondary guidance tiles, five modes,
dynamic titles, and the one-focus-area budget. Live browser measurements confirm the equal-height
logo/title row, 320 px desktop and 76 px compact navigation widths, one visible workflow area, and
zero horizontal overflow. The wider pane consumes more desktop width, deliberately giving the
style selector the prominence shown in the user's wireframe; compact screens retain the prior
icon-only behavior.

### D014 — Persistent five-mode rail with a single-step workspace

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M8

**Context**

The progressively disclosed role-first site still spent substantial horizontal space on repeated
audience framing and presented source preview, result, and technical evidence together on job
pages. The user requested a more efficient application shell: three audience styles permanently on
the left, Help me choose and Advanced user beside them, and only one workflow step visible in the
main workspace at a time. The supplied visual reference rendered as a uniform black image, so the
written layout specification was the only actionable design input.

**Options considered**

- Keep the existing centered role chooser and two-column story hero, then shorten its copy.
- Create five separate products or expose advanced transform operations.
- Keep one shared workflow, add a persistent icon rail for five presentation modes, and make
  Rules/Upload plus Inspect/Decide/Download explicit single-visible-step workspace navigators.

**Decision**

Use a fixed left rail with placeholder `LOGO` text; Game developer, 3D artist, and Technical artist
style icons; and separate Help me choose and Advanced user icon tiles. Every icon has an accessible
label, native title, and hover/focus hint. The workspace header is exactly
`Asset Shepherd -- [style]`, with the style updated by the active mode.

Render only Rules or Upload during intake. Render only the selected Inspect, Decide, or Download
job view, using a read-only query parameter over the same frozen in-process job. Default directly
to Decide while approval is pending and Download after completion or blocking. Advanced mode uses
the same supported profile-copy form and deterministic workflow; it does not unlock raw transforms,
safety policy, unsupported repair domains, verification invariants, or source mutation.

**Evidence and consequences**

Parameterized web acceptance runs the complete approved broken-fixture workflow through all three
audience styles and Advanced mode. Additional assertions cover all five rail modes, dynamic titles,
hidden Upload startup state, explicit job views, exactly one focus area per server-rendered state,
policy provenance in Inspect, authorization in Decide, and verification/package evidence in
Download. The original role routes, profile schema validation, native Strands interrupt, grouped
normalization approval, source preservation, and seven-artifact package contract remain unchanged.

The left rail remains visible at narrow widths and therefore consumes a small fixed slice of mobile
space. This is intentional: the user explicitly chose persistent orientation over moving the mode
navigator to a bottom bar.

### D013 — Freeze versioned policy copies per inspection job

**Date:** 2026-08-21

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M8

**Context**

The explicit rules-then-upload intake prevented users from confusing a profile with a model, but a
profile was still presented mostly as a short radio label. Job provenance recorded only its ID and
version, findings exposed only a bare rule path, and the web job read the repository preset directly.
The user asked to make profiles first-class versioned project policies, preserve presets as
immutable, support bounded customization, and prove exactly which frozen rules governed a job.

**Options considered**

- Keep presets read-only and add descriptive copy only.
- Allow arbitrary profile JSON or raw transform input in the browser.
- Build a general policy-management service with mutable saved profiles.
- Keep the existing role/intake flow, show complete preset policy evidence progressively, validate
  only supported target-state overrides, and freeze the resolved copy inside each new job.

**Decision**

Keep repository JSON profiles immutable and expose them as presets with concise summaries and a
collapsed full rule review. Add one collapsed `Customize a copy` section inside the existing intake
focus area. Allow only height/tolerance, Y-up and ground-contact target state, an engine-compatible
bounded naming pattern, and report-only budgets. Do not expose matrices or make repair safety,
authorization classes, vertical inference, uniqueness guarantees, verification invariants,
unsupported repair domains, engine/type, or source preservation editable.

Every upload writes a resolved `profile.json` into its opaque job workspace. A custom policy receives
a deterministic frozen ID derived from its base preset and explicit overrides. Provenance records
that ID, the base preset, only changed values, profile version, and canonical SHA-256. Findings retain
their primary rule path and add the exact frozen policy parameter values that caused them. Existing
jobs have no policy mutation route; changing rules requires a new upload-backed inspection/job.

**Evidence and consequences**

Web acceptance covers preset summaries and collapsed reviews, successful validated custom copies,
invalid numeric and naming-rule rejection before job creation, unchanged repository preset bytes,
canonical-hash agreement, explicit override recording, finding rule citations, and distinct job and
inspection records for different policies over the same source. Existing three role routes, the
two-focus-area intake, single grouped normalization approval, clean/blocked/error behavior,
independent verification, source preservation, and seven-artifact ZIP remain unchanged.

Custom copies are deliberately job-scoped rather than a reusable policy library. This avoids adding
accounts, mutable shared policy state, or deployment architecture before M9 while making every
current result reproducible from its frozen policy evidence.

### D012 — Require an explicit validation-rule choice before GLB upload

**Date:** 2026-08-21

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M8

**Context**

The intake card presented a dropdown labeled `Project target` above the GLB upload. A first-time
user reasonably could not tell whether the dropdown selected an example asset, replaced the upload,
or configured the inspection. It also silently defaulted to the first profile, making an unintended
1.8-meter character target possible for a prop such as Shader Lantern.

**Options considered**

- Keep the dropdown and add a short helper sentence.
- Preselect a profile based on the user's story route or uploaded filename.
- Show both trusted profiles directly, require an explicit choice, and separate rules from the
  actual file as two numbered steps.

**Decision**

Replace the dropdown with two visible radio choices and no default. Label step 1 `Choose validation
rules` and explicitly state that it does not choose a model. Label step 2 `Upload the GLB you want
checked` and state that this is the actual 3D model. Keep both steps inside the single intake focus
area and preserve the same trusted profile IDs, upload boundary, and workflow behavior.

**Evidence and consequences**

All three story routes render the same two-step intake and tests assert the explanation, two
required profile choices, absence of the ambiguous label, and unchanged end-to-end workflow. Live
desktop and phone-width review shows no horizontal overflow; selecting the small-stylized profile
sets `small-stylized-static-mesh-v1`; and the console has no errors or warnings. Users must now make
one deliberate rule choice before submission, trading a single click for protection against a
silent, inappropriate scale target.

### D011 — Approve Shader Lantern normalization and preserve its report-only warning

**Date:** 2026-08-21

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** RW2 / M10

**Context**

Shader Lantern's frozen blind plan correctly stopped at a consequential physical-size decision. The
raw export represented a 99.908905-meter object, while the user has now stated that the intended
real-world height is 1.2 meters and approved `normalize-root-v1`. The same plan contains two safe
display-name repairs and a 1,564-triangle budget overage that is explicitly report-only.

**Options considered**

- Reject or defer normalization despite the supplied intended height.
- Execute the approved scale and safe display-name repairs while preserving all authored content.
- Expand scope into topology reduction or attempt to recreate transparent/emissive effects visible
  in the Tripo preview but absent from the exported GLB.

**Decision**

Execute the approved `0.0120109414×` uniform root normalization and both policy-safe display-name
repairs. Preserve geometry, topology, materials, images, textures, and samplers exactly. Leave
`TRIANGLE_BUDGET_EXCEEDED` unresolved and report-only. Treat the source export's opaque,
non-emissive material state as a disclosed corpus limitation rather than inventing preview-only
content. Use a Blender re-export as the third Unreal diagnostic arm and label it as a control, not a
human-cleaned reference.

**Evidence and consequences**

Independent verification measures a grounded 1.2-meter candidate with unchanged 77,545 vertices,
101,564 triangles, one material, and three textures; its second plan is empty and its only remaining
warning is the triangle overage. Raw and repaired GLBs have byte-identical binary geometry and
material/texture/image/sampler/accessor records. Blender 5.1.2 imports both with matching resources
and near-zero rendered difference, successfully re-exports the repaired candidate, and Unreal 5.8
imports raw, repaired, and the Blender control with zero errors. The isolated Unreal visual pass
finds no appearance, texture, normal, opacity, or emissive-behavior regression. The full RW4
three-way gate remains incomplete because no human-cleaned Lantern reference or manual-time record
exists.

### D010 — Progressive disclosure limits every web state to three primary focus areas

**Date:** 2026-08-21

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M8

**Context**

The first story chooser asked a new visitor to understand eleven separate visual and textual areas
before choosing a role. Its three route cards also embedded mini workflows, promises, and product
boundaries, while later screens exposed stage rails, metrics, previews, decisions, findings, and
verification simultaneously. The behavior was correct, but the presentation made the product feel
more complicated than the three actions a user actually performs.

**Options considered**

- Shorten individual paragraphs while retaining the same card and panel hierarchy.
- Remove role-specific journeys and return to one generic technical-art page.
- Keep the three functionally equivalent role routes from D008, but reveal only the next useful
  action and collapse detailed evidence behind one explicit disclosure.

**Decision**

Make the role question the first visible content on `/`. Limit the chooser and each intake to two
primary focus areas. Limit approval, blocked, and completed job states to three: the decision or
result, the model preview, and one collapsed technical-details disclosure. Use the short visible
sequence `Inspect → Decide → Download/Package`; retain all seven contracted stages, findings,
checks, metrics, and session behavior inside technical details. Keep all workflow behavior, safety
policy, output artifacts, and role distinctions unchanged.

**Evidence and consequences**

Automated acceptance tests count `data-focus-area` regions and fail any rendered state above three,
while still completing the exact approval and seven-file ZIP workflow through every role. Desktop
and 390 × 844 browser review confirms the chooser starts with `Which best describes you?`, all three
role pages render without horizontal overflow, and pending/completed states expose only their three
primary areas. The source, Strands interrupt, deterministic repair, independent verification,
preview routes, and download package are unchanged. Detailed evidence now requires one intentional
click, which is the deliberate tradeoff for a much clearer first scan.

### D009 — Track Shader Lantern and preserve its pending blind decision

**Date:** 2026-08-21

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** RW2 / M10

**Context**

The user supplied the untouched Shader Lantern GLB and its authenticated Tripo workspace reference.
The 12.8 MB file was generated through the same paid Tripo account for which the user confirmed
commercial public-use rights. Blind inspection found a standards-compliant but implausible
99.908905-meter represented height and proposed a consequential scale normalization to the selected
general small-asset profile's 1.2-meter target. The user has not yet stated the lantern's intended
real-world height.

**Options considered**

- Guess the intended physical size and approve the root normalization.
- Reject the proposal on the user's behalf and complete a name-only result.
- Preserve the registered source and frozen inspection/plan at the approval boundary until the user
  approves or rejects the exact transform.
- Keep the rights-confirmed input private despite its modest size and reproducibility value.

**Decision**

Track the byte-identical raw GLB as the second distributable corpus input and freeze its blind result
at `normalize-root-v1`. Do not open the Lantern in Blender, Unreal, or a visual preview and do not
execute even safe names until the human physical-size decision is recorded. Record only workspace
settings actually exposed by the authenticated item page; mark Smart Mesh version and speed preset
as unverified.

**Evidence and consequences**

The raw SHA-256 is
`be2c9cab8d4e51f7a948c7c54db7a10c932f24faf69bc3166ff724ccc00c49b9` before and after
registration. Blind evidence reports a valid static GLB with 77,545 vertices, 101,564 triangles,
three embedded 4096² PBR images, no rig/animation/morph targets, two safe name candidates, a
report-only 1,564-triangle budget overage, and the pending reversible `0.0120109414` scale. This
preserves the addendum's prediction-before-diagnosis discipline and makes the missing user decision
explicit instead of disguising it as autonomy.

### D008 — Three story-first web concepts share one product core

**Date:** 2026-08-21

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M8

**Context**

The first M8 surface exposed the complete workflow but explained it with one generic technical-art
layout. A new game developer, 3D artist, and technical artist arrive with different questions: ship
readiness, preservation of artistic intent, and policy evidence. A single information hierarchy made
the underlying product harder to understand even though the workflow itself was correct.

**Options considered**

- Replace the existing page with one compromise layout for every audience.
- Fork the backend or available capabilities by audience.
- Build three complete presentation concepts that reorder and rephrase the same profile, upload,
  Strands interrupt, deterministic repair, verification, preview, and result package.

**Decision**

Make `/` a transparent three-concept chooser and provide full routes for game developer, 3D artist,
and technical artist journeys. Store the selected story with the in-process job so refreshes and the
approval/completion page preserve that mental model. Keep all behavior, safety boundaries, profiles,
actions, output artifacts, and local zero-network provider identical.

**Evidence and consequences**

Parameterized acceptance tests run the complete broken-fixture approval and exact seven-file ZIP
audit through every story. Clean, invalid, and inspection-only paths remain covered. Live Chrome
review passed for all three desktop layouts; 390 × 844 responsive review found no horizontal
overflow; Patchling's textured before/after previews render in the artist flow; and the application
console is clean. The repository deliberately keeps all three concepts available for user comparison
rather than declaring a canonical audience hierarchy before review.

### D007 — Track Patchling as the first distributable real-world input

**Date:** 2026-08-21

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** RW1 / M8 / RW5

**Context**

The addendum requires the final public repository to contain enough original or distributable assets
to reproduce at least one complete demo workflow. D003 intentionally ignored all real-asset binaries
until rights and repository-size policy were known. The user has now confirmed that Patchling was
generated under a paid Tripo account with commercial/public-use rights, and the immutable GLB is
4,860,944 bytes.

**Options considered**

- Keep every real-world binary private and defer reproducibility to an external handoff.
- Track Patchling with Git LFS despite its modest size.
- Track only the byte-identical Patchling raw GLB in ordinary Git, while continuing to ignore
  repaired outputs, ZIPs, DCC files, Unreal content, and screenshots.

**Decision**

Add an exact `.gitignore` exception for `patchling_01/raw/asset.glb` and track that file in ordinary
Git. Continue ignoring all other raw corpus assets until their individual rights and size are
confirmed. Keep generated outputs reproducible from the raw input, profile, approvals, and code.

**Evidence and consequences**

The tracked file's SHA-256 remains
`dc2f03ae8ed368f46c2a4ac9e2ebb71f23e980b0c9e6913c685d011e273f418d`, matching the download,
registration record, frozen blind inspection, and pre/post registration checks. Its size is well
below GitHub's ordinary file limit and does not justify LFS overhead. Public reproduction no longer
depends on the owner's authenticated Tripo workspace link.

### D006 — Server-rendered local web product with in-process Strands sessions

**Date:** 2026-08-21

**Status:** ACCEPTED

**Decision owner:** Codex

**Milestone:** M8

**Context**

M8 needs a coherent upload-to-download product that presents structured findings, preserves the
native Strands approval interrupt across browser refreshes, renders before/after GLBs, and does not
pull deterministic repair behavior into a browser-specific layer. The local milestone does not yet
authorize durable AWS session infrastructure.

**Options considered**

- Build a separate JavaScript SPA and API, adding a Node toolchain and duplicated state model.
- Use a server-rendered FastAPI/Jinja surface over the existing typed Python workflow, with a small
  in-process registry and isolated ignored job directories.
- Skip a local product and expose only JSON endpoints or the CLI.

**Decision**

Use FastAPI, Jinja, and Uvicorn for the local product. Keep one `AssetShepherdAgent` instance per
opaque UUID job in a thread-safe in-process registry. Save uploads under a generated job directory,
never under a browser filename; enforce the contracted `.glb`, magic-byte, and 50 MB boundaries;
and expose only source, verified candidate, and result-ZIP routes. Use the real Strands loop with the
zero-network scripted model by default so local review needs no credentials. Use a pinned official
`<model-viewer>` browser component for interactive GLB previews without sending model files to an
external service.

**Evidence and consequences**

Automated web tests cover approve/refresh/resume, clean no-approval completion twice from separate
app starts, invalid upload rejection, inspection-only unsupported content, source preservation, and
ZIP contents. Live Chrome review shows the broken robot before/after difference and Patchling's
textured no-regression path at desktop and mobile widths with no console errors.

The in-process registry survives browser refresh but not a server restart; this is stated in the UI
and README. Durable sessions belong to M9 rather than being invented locally. The browser component
and web fonts require ordinary internet access for their pinned static scripts/styles, but GLB data
remains on the Asset Shepherd origin. A future deployment may self-host those static dependencies if
release reliability requires it.

### D005 — Keep Patchling single-material and move PBR diversity to the corpus

**Date:** 2026-08-21

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** RW1 / RW2 / M10

**Context**

Patchling is visually strong and survives the deterministic pipeline without corruption, but the
untouched Tripo export contains one opaque material with a single embedded base-color texture. It
does not supply the preferred distinct material surfaces, emissive channel, transparency, normal
map, or metallic-roughness texture. The user approved continuing if the one-material limitation
could be handled honestly.

**Options considered**

- Modify Patchling to manufacture additional materials or PBR channels.
- Reject an otherwise strong hero asset solely because it misses a corpus selection preference.
- Preserve Patchling exactly as generated, use it as the visual hero and resource-preservation case,
  and require later Asset Flock members to cover multi-material and richer PBR stress dimensions.

**Decision**

Keep Patchling's material structure unchanged. Material creation, merging, texture generation, and
artistic editing remain outside Asset Shepherd's scope. Retain Patchling as the current demo
candidate, disclose its material limitations, and make Shader Lantern the next requested asset with
transparency and emissive behavior as primary selection criteria.

**Evidence and consequences**

The raw and Shepherd GLBs have identical geometry, bounds, material, texture, and image counts in
both deterministic inspection and Blender 5.1.2. This avoids an unsafe or scenario-specific repair
while preserving a memorable mascot. Patchling alone cannot support claims about broad PBR
preservation; those claims remain blocked until the minimum corpus supplies explicit evidence.

### D004 — General compact-static-mesh profile prevents Patchling over-scaling

**Date:** 2026-08-21

**Status:** ACCEPTED

**Decision owner:** Codex

**Milestone:** RW1 / M10

**Context**

The first untouched Patchling measurement used the existing Unreal indie robot profile, whose
1.8-meter target produced a high-confidence proposal to scale a 0.998-meter asset by 1.8035225. The
real-world addendum explicitly defines Patchling's preferred represented height as 0.9–1.5 meters.
Approving the proposal would therefore have violated the intended asset scale even though the
repair mechanism itself behaved correctly for its supplied profile.

**Options considered**

- Approve the 1.8-meter normalization because it was proposed by the existing profile.
- Reject normalization only for the named Patchling asset in product code.
- Create a versioned, general compact-stylized-static-mesh profile that encodes the addendum's
  already-approved range as a 1.2-meter target with ±0.3-meter tolerance.
- Remove scale inspection from real-world validation.

**Decision**

Preserve the initial prediction as profile-mismatch evidence and do not execute its normalization.
Use `small-stylized-static-mesh-v1` for the canonical blind run. The profile is ordinary typed data,
is applicable to compact mascot-style static meshes, and contains no asset-ID dispatch. Do not add
a Patchling special case or change the repair engine.

**Evidence and consequences**

The canonical rerun proposes only two policy-safe display-name repairs. Verification preserves the
0.998-meter height, geometry, material, texture, source hash, and independent bounds, then produces
an empty second plan. Blender imports raw and repaired outputs with identical metrics and no missing
image. The incident demonstrates that approval safety depends on correct project intent and that
high-confidence measurements do not make an unsuitable profile correct.

### D003 — Separate, metadata-tracked validation corpus with ignored binary evidence

**Date:** 2026-08-21

**Status:** ACCEPTED

**Decision owner:** Codex

**Milestone:** RW0 / M10

**Context**

The real-world addendum requires immutable Tripo exports, reproducible controlled mutations, typed
ground truth, independent Blender evidence, and an isolated Unreal comparison without expanding the
hosted product or prematurely publishing large or rights-uncertain binaries.

**Options considered**

- Commit every raw and generated binary immediately. This would make rights and repository size
  difficult to control before the first real asset is reviewed.
- Use undocumented external files only. This would prevent judges from reproducing the workflow.
- Track schemas, prompts, provenance, manifests, adjudication, reports, and automation; ignore raw
  and generated binaries until rights and size policy are known; require at least one distributable
  complete workflow before public release.
- Put mutation and DCC behavior into the Asset Shepherd repair runtime. This would blur ground truth
  with the system under test and violate scope protections.

**Decision**

Keep validation code and evidence under a distinct `validation` layer. Track typed Draft 2020-12
schemas, human facts, mutation ground truth, templates, and reproducible scripts. Ignore raw Tripo,
derived GLB, `.blend`, Unreal binary content, caches, and screenshots by default. A raw asset may be
registered only after required provenance and public-use confirmation are complete; registration
hashes and validates the GLB without mutating it. Controlled mutations operate only on copies and
remain separate from product repair code. Blender and Unreal are local independent consumers, never
hosted dependencies or product plugins.

**Evidence and consequences**

Incomplete provenance is rejected while the raw hash stays unchanged. Fixture mutations preserve
geometry and source hashes and produce typed manifests whose expected findings are independently
confirmed by the inspector. Blender 5.1.2 and an isolated Unreal 5.8 project both execute the
checked-in harnesses successfully. The public repository does not yet contain a real benchmark
binary; Patchling rights and size must be confirmed before one is deliberately added. No product
behavior, repair policy, AWS architecture, or supported input format changes as a result.

### D002 — Single Strands agent with state-bound tools and native tool interrupt

**Date:** 2026-08-21

**Status:** ACCEPTED

**Decision owner:** Codex

**Milestone:** M7

**Context**

M7 requires genuine Strands orchestration without allowing model output to become an authorization
or filesystem boundary. It also needs deterministic offline tests, a real approval pause/resume,
observable metrics, and live-provider configuration without a hard-coded model ID.

**Options considered**

- Expose one tool that runs the whole deterministic workflow. This would make the agent ornamental
  and hide plan selection, approval, and verification sequencing.
- Use a pre-tool hook to interrupt repair. Hooks are viable, but a state-bound approval tool keeps
  the approval card and response immediately adjacent to the consequential operation.
- Use six narrow state-bound tools on one primary Strands agent, with native tool interrupts and a
  one-attempt correction tool.
- Make paid Bedrock calls mandatory in unit tests. This would make the gate credential-dependent and
  violate the offline-test contract.

**Decision**

Use one primary Strands agent with a version-1 system prompt and six path-free tools bound to an
`AgentJob`. Use `ToolContext.interrupt` for the combined normalization approval and resume only with
the exact Strands interrupt ID. The deterministic core validates candidate selection, approval,
repair, verification, retry count, and packaging. Keep a scripted model provider as a zero-network
development harness over the real Strands event loop. Configure the live Bedrock model ID and region
through environment variables and keep its integration test opt-in.

**Evidence and consequences**

Approve and reject runs both traverse the real Strands loop, stop once, resume the interrupted tool,
and produce the exact seven-file deterministic package. The approved GLB is byte-identical to the M6
output. Missing or mismatched approval records fail before mutation. A controlled first verification
failure originally caused one same-plan retry; D032 supersedes that behavior with one fresh
candidate inspection and unexecuted plan assessment. Strands metrics expose tool outcomes,
interrupts, and final state in `agent_result.json` outside the contracted ZIP.

The offline harness does not prove paid-model behavior; the environment-configured Bedrock test is
opt-in and remains unexecuted until user-owned account configuration and cost controls are available.
Durable interrupt persistence is deferred to the local web milestone rather than silently adding a
session architecture during M7.

### D001 — Lightweight GLB implementation stack

**Date:** 2026-08-21  
**Status:** ACCEPTED  
**Decision owner:** Codex  
**Milestone:** M2

**Context**

The deterministic core must inspect and safely modify GLB structure, evaluate world transforms,
preserve embedded resources, and reload the result without requiring Blender. The implementation
also needs an independent geometry check and must remain viable on Python 3.12, Linux, and likely
ARM64 deployment targets.

**Options considered**

- Use `pygltflib` for glTF structure and binary-resource access, NumPy for explicit transform and
  accessor math, Trimesh for independent geometry reloads, and Pillow for embedded images.
- Use Trimesh alone for both import and export. Its geometry API is strong, but exporting an imported
  scene may restructure glTF data that Asset Shepherd only intends to rename or parent.
- Use `gltflib` as the structure library. It is viable, but the spike found no capability advantage
  over `pygltflib` for the required extension dictionaries, binary blob access, and deterministic
  serialization.
- Use Blender as the mutation runtime. This conflicts with the lightweight hosted-runtime goal and
  is unnecessary for the contracted MVP repairs.

**Decision**

Use `pygltflib` as the structure-preserving GLB adapter, NumPy for deterministic geometry and
transform calculations, Trimesh only as an independent reload/geometry cross-check, and Pillow for
image metadata. Validation is layered: GLB header checks, `pygltflib`'s provisional structural
validator, deterministic reference and invariant checks, and an independent Trimesh reload. The
official Khronos validator remains a desirable additional release check, but its official Node/native
distribution is not a portable Python runtime dependency.

**Evidence and consequences**

The checked-in M2 spike creates a GLB with indexed geometry, an embedded PNG, a material and texture,
extras, and an unknown vendor extension. It loads the asset, traverses world transforms, measures
bounds, renames a node, inserts a reversible root transform, saves, reloads, validates, and confirms
the same transformed bounds through Trimesh. Vertex, triangle, material, texture, and image counts
remain stable. A uv foreign-platform dry run resolves all selected packages for CPython 3.12 on
manylinux ARM64. The selected packages use permissive licenses compatible with this MIT project.

`pygltflib` does not promise lossless preservation of arbitrary unknown JSON properties outside
standard `extensions` and `extras` containers, and its validator explicitly covers only part of the
glTF specification. Asset Shepherd will therefore refuse repair when required extensions are
unsupported, keep count/reference invariants, preserve the original, and require independent reload
and inspection before project-ready status. No claim of universal lossless round-tripping is made.

## Template

### DXXX — Title

**Date:** YYYY-MM-DD  
**Status:** ACCEPTED | SUPERSEDED | REJECTED  
**Decision owner:** Codex | User  
**Milestone:** M#

**Context**

What decision was required.

**Options considered**

- Option A
- Option B

**Decision**

What was selected.

**Evidence and consequences**

Why, what it enables, and what tradeoffs remain.
