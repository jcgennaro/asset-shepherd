# Asset Shepherd Decision Log

Record decisions that materially affect architecture, product behavior, cost, security, or scope.

## Decisions

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
failure causes exactly one same-plan retry. Strands metrics expose tokens, duration, tool outcomes,
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
