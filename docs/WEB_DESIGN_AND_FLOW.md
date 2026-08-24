# Asset Shepherd Web Design and Flow

This document records the implemented local web shell and the corrected D036 product flow. The
current routes and durable state are reusable, but the deterministic findings-and-plan path is now a
legacy harness. `AGENT_ORCHESTRATED_WORKFLOW.md` controls the model/tool authority boundary.

## Product mental model

Asset Shepherd works with a user on one asset. Conversation carries the collaboration; structured
controls carry authorization:

```text
Describe the intended asset and target state
  -> Review and agree on one target story
  -> Upload the source GLB
  -> Agent chooses sensors and assesses the evidence
  -> Agent accepts, asks, reports, stops, or previews a supported action
  -> Approve or reject the exact consequential action, if proposed
  -> Agent executes, re-observes, and may iterate
  -> Verify invariants and download the evidence package
```

The implemented first two steps use a bounded semantic intake provider. The corrected workflow must
then give a real workflow model the confirmed target, durable job state, typed sensor/action
capabilities, and recorded render evidence. Deterministic tools own measurements, exact action
consequences, authorization enforcement, mutation, invariant verification, and artifacts. The agent
owns target-dependent findings, disposition, and repair choice.

## Why intent replaces the role selector

The former entry point asked whether someone was a game developer, 3D artist, or technical artist.
Those routes changed labels but not behavior, and did not answer the important project questions:
what the person meant to create, what it should be used for, and how large it should be.

The primary entry point now gives one instruction: **Describe the model you’re working on.** It
accepts a 12–600 character plain-text description. Use and scale guidance appears only in the input
example. The entry surface does not repeat that instruction or expose privacy, implementation, or
alternate-workflow notes. A typed intake pass proposes supported intended use and a plausible
semantic vertical scale, even when the prompt contains no number. A clarification view asks one
natural question only when a required field remains below the confidence gate. It never shows a
field whose value is already supported by the proposal.

Asset Shepherd drafts one exact first-person target story. The user must review and agree to that
story before seeing validation rules or an upload control. The description is target metadata, not
instructions to run code, perform transforms, change materials, or authorize a repair.

Non-static target uses are permitted because they truthfully capture intent. The confirmation page
states that the current product can inspect and normalize the static GLB, while rigging, skinning,
and animation remain external work. This does not add those repair domains.

## Information architecture

| Route | Purpose | Mutation or inspection? |
|---|---|---|
| `/` | Describe the intended asset in one prompt | No |
| `/intents/{intent_id}` | Answer only missing target fields, then review the exact story | No |
| `/intents/{intent_id}/intake` | Review rules and choose the source GLB after agreement | No until submit |
| `/jobs/{job_id}?view=inspect` | Review measured facts, findings, and rule provenance | No |
| `/jobs/{job_id}?view=decide` | Approve or reject the grouped normalization | Only approval can authorize it |
| `/jobs/{job_id}?view=download` | Review verification and retrieve the result package | No |
| `/feedback` | Record bounded feedback with the originating workflow context | Local feedback record only |
| `/workspace` | Select a new slot or resume one of seven named assets | No |
| `/workspace/new/describe` | Describe one new or replacement asset | No |
| `/workspace/new/{draft_id}/upload` | Upload one GLB after semantic intake | Objective preflight only |
| `/workspace/{workspace_id}` | Resume the exact persisted conversation phase for one asset | Only through its typed workflow controls |

Former `/stories/{role}` bookmarks redirect to `/`. Audience modes are no longer a primary product
choice. Internally retained presentation labels do not affect policy or deterministic behavior.

The hosted left pane is a compact four-step orientation rail: **Assets → Describe → Upload →
Shepherd**. Assets selects a new slot or resumes one. Describe and Upload each contain exactly one
task. Shepherd owns the checklist, exact actions, approval, repair, verification, user feedback, and
every subsequent repair turn. The form-led reference route retains its own five-step rail.

The persistent question-mark action opens a task-oriented **How it works** page. It presents only
three steps: **Describe and upload**, **Review what we found**, and **Download the result**, plus one
start action. Release numbers, roadmap framing, internal tool or provenance terminology, and a
generic repair-scope inventory do not appear there. A limitation belongs in the active workflow
only when the particular asset or intended result makes it relevant.

## Hosted asset workspace

The conversation-led home is only a visual gallery of up to seven processed assets. Intake assigns each
asset a concise name from the user's description and cards show that name, current phase, and source
preview rather than a filename or hash. Opening a card reconstructs that asset's exact persisted
phase. The existing workspace ID remains the Strands session ID and each workspace owns a separate
`strands_state` directory. No conversation state is shared across assets.

Starting a new slot opens a description-only screen. A successful semantic intake advances to a
separate upload-only screen; the inferred target contract is carried forward and is not recomputed
after file selection. At seven assets, each gallery card offers an explicit replacement path before
description. The selected workspace is removed only after the replacement upload and objective
preflight persist successfully. The structured contract remains available through **Job details**, but it no longer
occupies a permanent right-hand reading area. Completion presents one compact workflow-agent
sentence, followed by the useful model comparison and Yes/No handoff. Yes changes the existing
panel to fixed-model and evidence downloads without a page reload.

## Target-story contract

Before a target story exists, the public version-3 `TargetIntakeContract` requires:

- the normalized description;
- a concise asset name for the gallery and workspace;
- one supported intended-use enum;
- a positive intended real-world height in centimeters;
- one evidence record, source, and confidence of at least 0.8 for every populated target field; and
- an exact list of fields that remain missing.

The interim OpenAI analyzer emits a strict `TargetIntakeInference`; server code validates it,
applies the 0.8 confidence gate, and constructs the contract. The proposal records provider/model
identity and inference evidence. The user can edit the natural-language description and ask the
analyzer to reinterpret both target fields, then must confirm once. Intended-use categories are not
exposed as a selector or repair mode. The inference must also return `PROCEED` or `REFUSE`. A
decline has no target fields, creates no job or uploaded-file copy, and renders only a concise
response such as: **Sorry, I can't engage with this type of content. Let's work on something
else.** Exact punctuation is not part of the contract.
Measured GLB bounds can inform evidence and questions but can never stand in for intended height.
The draft is stored as `target_intake.json`; it is not repair authorization. The offline extractor
and future Bedrock implementation emit the same schema.

Agreement creates an immutable `AssetIntentProvenance` record with:

- intent schema version;
- opaque intent ID;
- normalized original description;
- supported target-use enum;
- canonical target height in centimeters;
- the exact agreed story;
- confirmation timestamp;
- canonical SHA-256 over all preceding fields.

The job stores this record as `intent.json` and embeds the same record in `provenance.json`. The
server validates its canonical hash before accepting an upload. Changing the description, use, or
height requires a new intent and therefore a new inspection job. Reusing the same agreed intent
with different project rules also creates a new job; existing evidence is never reinterpreted.

The intended height already frozen in the target story controls the profile target state and is not
requested again. Asset Shepherd resolves a complete validated profile from one versioned Unreal
static-game-asset family. Target height comes directly from confirmed intent; height and grounding
tolerances are bounded proportions of intended height; explicit standing, hanging, or hovering
language may influence ground-contact policy; and genuinely unspecified values retain family
defaults. The user never enters a scale factor or transform matrix; the deterministic planner
no longer derives a semantic repair. The workflow agent decides whether any supported action is
warranted and calls a typed preview tool; deterministic code calculates its exact consequence.

## Rules and upload

After agreement, intake exposes two visible workflow steps, one at a time:

1. **Rules.** Review the complete intent-derived proposal or adjust supported advanced values.
2. **Upload.** Select the actual GLB to inspect.

New jobs use the immutable `unreal-static-game-asset-family-v1` parameter family. The historical
`unreal-indie-robot-v1` and `small-stylized-static-mesh-v1` profiles remain immutable CLI, fixture,
and evidence inputs, but are no longer product choices. All active parameters remain visible under
**Review all active rules**, and **Why these rules?** identifies confirmed intent, bounded intent
derivation, family defaults, and explicit user adjustments. **Adjust supported rules** exposes only
fields already enforced by `ProjectProfile`: height tolerance, Y-up and ground-contact requirements
and tolerance, naming pattern, and report-only triangle/material/texture budgets. The confirmed
height is displayed but is not requested again or replaceable by a raw operation.

Authorization behavior, uniqueness guarantees, verification invariants, unsupported repair domains,
engine/type, and mutation boundaries are fixed. Dominant-extent vertical inference is deprecated and
cannot create an assessment or action. Repository
profiles and the family remain byte-for-byte immutable. Each job receives a validated
`profile.json` snapshot plus frozen/family identifiers, explicit differences, per-rule sources,
version, and canonical hash in provenance. The legacy `base_preset_id` field mirrors the family ID.

Upload accepts one GLB 2.0 binary up to 50 MB. The same control accepts a click-to-choose action or
a Windows Explorer drop and visibly updates to the selected filename. A drop must contain exactly
one `.glb`. The server validates the filename extension, GLB magic, size, intent hash, and trusted
policy family before creating an isolated job.

## Inspect, decide, verify, and package

### Inspect

The hosted Shepherd view streams one six-row checklist and resolves each call to evidence available
or attention required. Each row appears once. A checkmark means pass; a colored exclamation row
means attention, and hovering or focusing its icon exposes the reason. There is no completed-count
label and no second table repeating the same statuses. **Summary** is the agent's compact
assessment, grounded in the confirmed target, measurements, and renders; it compresses normal
domains and groups every attention finding into no more than three readable areas. The next question
reflects the agent's chosen disposition rather than mechanically assuming every finding is fixable.
The conversation-led route uses the same shared checklist rather than bypassing this progress view.

In the form-led reference route, one closed **More details** disclosure retains the preview plus the full check log, target
expectations, universal invariants, measurements, findings, finding authority, exact rule
provenance, agent-proposed actions, execution stages, and frozen policy in a scrollable table. The
default view does not repeat the target story, a second workflow rail, or per-check explanatory
paragraphs. User free text cannot authorize an action; agent assessments and action previews remain
typed durable state rather than unstructured chat claims.

Intended use is context and a support-boundary check, not a preset. Static-asset intent receives the
complete supported workflow. Character intent is retained, but the current product offers only
static inspection/normalization and an external rigging or animation handoff. Semantic piece count
is currently **unspecified**: inspection reports roots, nodes, meshes, and primitives, but does not
pretend those structural counts identify artistic pieces and does not merge or split geometry.

### Decide

If the agent previews a consequential supported action, Decide presents that exact action. Approve
or Reject is bound to the action hash and exact Strands interrupt ID. Preauthorized display-name
repairs still require an initiating agent tool call. Rejection is recorded in decisions and
provenance, the proposed operation is not executed, and unresolved assessments remain explicit.
The hosted approval surface shows the selected plan in at most three groups—physical normalization,
mesh names, and node names—so it never says changes exist without displaying them. Exact single-name
mappings remain visible. Job details retains the complete structured evidence on demand.

### Verify and download

The output is reloaded and independently checked. Only a verified candidate is called ready and
served through the repaired-asset route. A structurally unsupported input receives an
inspection-only package without `repaired.glb`. A clean input is packaged without unnecessary GLB
reserialization or mutation.

If at least one repair executed, Download presents source and verified candidate in one shared 3D
scene at their actual relative scales. The user can orbit, pan, zoom, or fit both, before, or after.
Projected world-bounds corners drive persistent **Before** and **After** targeting brackets and
leader lines; a model less than 18% of the other's longest dimension receives an explicit
**model here** label. Optional X/Y/Z rulers retarget to the selected fit bounds with five
human-readable meter ticks, and an optional approximately 20-centimeter banana provides a playful
physical reference. The HUD and banana remain display-only. Standardized source/candidate render
artifacts must also be recorded for the workflow model's visual assessment; they do not alter the
source, candidate, approved action, invariant verification, or package bytes.

The Apache-licensed Google `<model-viewer>` 4.3.1 browser distribution is served from the package,
so previews do not rely on a public CDN at runtime.

After comparison, **Did we get it right?** remains the only result decision. **Yes** records durable
acceptance without navigating away and changes that panel in place to **Ready to download**. A ready
candidate offers the fixed GLB first and the complete evidence package second. The standard
POST/redirect response remains as a no-JavaScript fallback. **No** retains the bounded feedback loop.

The successful ZIP still contains exactly:

```text
repaired.glb
inspection.json
repair_plan.json
decisions.json
verification.json
provenance.json
report.md
```

`intent.json` and `profile.json` are job-input snapshots beside the output directory. The confirmed
intent is already included in packaged `provenance.json`, so the seven-file package contract does
not change.

## Attention and visual system

- One server-rendered focus area is visible in every state; the hard maximum remains three.
- The two-column shell retains the placeholder `LOGO` cell, persistent left navigation, current-step
  title, and full workspace.
- Primary questions and actions use large type and available whitespace.
- Target confirmation uses a wider canvas, human-readable metric units, and exactly three collapsed
  groups: purpose, scale and pose, and structure. Each group exposes at most three
  supporting facts only after the user opens it.
- The only target decision is **Did I get it right?** The user either continues or edits the same
  description and asks for another interpretation; resubmitting unchanged text is also a retake.
- **It’s not working for me** opens one reusable feedback page with the originating workflow
  context, four bounded reasons, and an optional note of at most 1,000 characters.
- Policy parameters, finding evidence, upload notes, and verification details stay available
  through disclosures instead of competing with the next action.
- The dark workshop palette, responsive left rail, keyboard-visible controls, and reduced-motion
  behavior remain.
- Interactive previews use pinned `<model-viewer>` 4.3.1. The browser viewer is not repair or
  verification authority, but standardized renders derived from the same asset states are sensing
  evidence available to the agent and user.

## Runtime boundaries and limitations

- Intake uses the OpenAI Responses API unless `--offline-intake` selects explicit-text extraction.
  Only the description leaves the process; the uploaded GLB remains local.
- The current repair flow uses the real Strands loop with a scripted zero-network provider. Under
  D036 this is a test harness, not accepted product behavior.
- Draft intents and active approval sessions are in memory. Refresh works while the process is
  running; restart requires a new target story and ends active sessions.
- Job artifacts live below `build/web/jobs/{job_id}` and use opaque server-generated IDs.
- The current semantic intake proposes only supported use and intended size. The corrected workflow
  model performs later assessment and may create typed requests for supported action tools; it still
  cannot add unsupported repair domains or authorize itself.
- Assembly intent remains visibly unspecified until a typed, measurable contract exists; current
  structural counts are objective observations only.
- Bedrock must use the same durable Job Contract and typed tool schemas and may not bypass parsing,
  invariant enforcement, explicit approval, or independent verification. It must choose sensing and
  disposition rather than replay the scripted harness.
- The current product remains static-GLB repair only. It does not add rigging, skinning, animation,
  topology, UV, material, texture, transparency, emissive, or speculative artistic repair.

## Current automated evidence

- Intent construction is reproducible and canonical; tampering invalidates its hash.
- Invalid descriptions, target uses, heights, and inconsistent target-intake records fail before a
  job exists.
- Explicit description values are preserved with evidence; clarification asks only for missing or
  conflicting required fields and survives hosted restart.
- Upload is unavailable before explicit agreement.
- Confirmed intent and its hash are frozen in the job and copied into package provenance.
- Confirmed height and bounded grounding language resolve one family without baseline selection or
  duplicate target entry, and without exposing a scale operation.
- Changing intent or rules creates distinct jobs and inspections.
- Family resolution, validated advanced-policy, broken/approved, clean-control, invalid-upload, and
  unsupported inspection-only paths remain covered; historical profiles stay byte-identical.
- The approved flow still packages the exact seven artifacts, preserves source bytes, cites rule
  provenance, and requires the exact interrupt-bound decision.
- Former role routes redirect to the intent entry point.
- Confirmation and clarification contain no target-use dropdown. Inspection presents one compact
  check log, one summary with at most three attention groups, and one confirmation question; the
  complete evidence remains closed by default. Blocked inputs direct the user back to the
  creation/export tool with recorded reasons.

## Next hosted step

When the AWS milestone is authorized, Bedrock should replace the interim provider while preserving
the same typed dialogue:

```text
user description
  -> validated minimum target-intake contract
  -> follow-up questions only for missing required fields
  -> proposed AssetIntentProvenance fields
  -> user confirms exact target story
  -> deterministic workflow begins
```

That integration requires configured user-owned AWS credentials, selected model/region access, and
cost controls. It must remain optional in tests and must not broaden repair authority.
