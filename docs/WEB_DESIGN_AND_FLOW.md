# Asset Shepherd Web Design and Flow

This is the current local web-product handoff. It documents the implemented intent-first flow and
its safety boundary; it is not a proposal to expand repair scope.

## Product mental model

Asset Shepherd works with a user on one asset, but the conversation is not the repair authority:

```text
Describe the intended asset and target state
  -> Review and agree on one target story
  -> Review agent-resolved project rules and upload the source GLB
  -> Inspect deterministic findings
  -> Approve or reject one grouped physical normalization, if proposed
  -> Independently verify and download the evidence package
```

The future hosted form of the first two steps is a bounded Strands conversation using Amazon
Bedrock. It may ask follow-up questions, structure intent, and explain results. Measurements,
candidate repairs, authorization, mutation, verification, and ready/not-ready status remain owned
by the deterministic engine. The current local implementation uses ordinary validated form input
and makes no model or network request.

## Why intent replaces the role selector

The former entry point asked whether someone was a game developer, 3D artist, or technical artist.
Those routes changed labels but not behavior, and did not answer the important project questions:
what the person meant to create, what it should be used for, and how large it should be.

The primary entry point now asks:

- **What were you trying to make?** A 12–600 character plain-text description.
- **What should it become?** Static game asset, rig-ready character, or playable animated
  character.
- **How tall should it be in-game?** A positive real-world height in meters.

Asset Shepherd drafts one exact first-person target story. The user must review and agree to that
story before seeing validation rules or an upload control. The description is target metadata, not
instructions to run code, perform transforms, change materials, or authorize a repair.

Non-static target uses are permitted because they truthfully capture intent. The confirmation page
states that the current product can inspect and normalize the static GLB, while rigging, skinning,
and animation remain external work. This does not add those repair domains.

## Information architecture

| Route | Purpose | Mutation or inspection? |
|---|---|---|
| `/` | Describe the intended asset, use, and real-world height | No |
| `/intents/{intent_id}` | Review the exact drafted target story | No |
| `/intents/{intent_id}/intake` | Review rules and choose the source GLB after agreement | No until submit |
| `/jobs/{job_id}?view=inspect` | Review measured facts, findings, and rule provenance | No |
| `/jobs/{job_id}?view=decide` | Approve or reject the grouped normalization | Only approval can authorize it |
| `/jobs/{job_id}?view=download` | Review verification and retrieve the result package | No |

Former `/stories/{role}` bookmarks redirect to `/`. Audience modes are no longer a primary product
choice. Internally retained presentation labels do not affect policy or deterministic behavior.

The persistent left pane is now a compact workflow orientation rail: **Describe → Agree → Inspect
→ Decide → Download**. The workspace still shows only one step at a time. The title reflects the
current step, for example `Asset Shepherd -- Describe` or `Asset Shepherd -- Decide`.

## Target-story contract

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
derives the minimal physical normalization, if one is warranted.

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

Safety classes, grouped approval behavior, vertical inference, uniqueness guarantees, verification
invariants, unsupported repair domains, engine/type, and source preservation are fixed. Repository
profiles and the family remain byte-for-byte immutable. Each job receives a validated
`profile.json` snapshot plus frozen/family identifiers, explicit differences, per-rule sources,
version, and canonical hash in provenance. The legacy `base_preset_id` field mirrors the family ID.

Upload accepts one GLB 2.0 binary up to 50 MB. The server validates the filename extension, GLB
magic, size, intent hash, and trusted policy family before creating an isolated job. The copied source
is never mutated.

## Inspect, decide, verify, and package

### Inspect

Inspect shows the untouched source preview, measured bounds, core counts, findings, and collapsed
details. Every profile-caused finding cites the frozen rule parameter and profile identifier that
caused it. Free text cannot create a finding or candidate action.

### Decide

If the deterministic plan proposes scale/orientation/grounding normalization, Decide presents one
grouped consequential action. Approve or Reject is bound to the exact Strands interrupt ID.
Policy-safe display-name repairs remain separate. Rejection is preserved in decisions and
provenance, the physical operation is not executed, and unresolved findings remain explicit.

### Verify and download

The output is reloaded and independently checked. Only a verified candidate is called ready and
served through the repaired-asset route. A structurally unsupported input receives an
inspection-only package without `repaired.glb`. A clean input is packaged without unnecessary GLB
reserialization or mutation.

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
- Policy parameters, finding evidence, the confirmed story on job pages, upload notes, and
  verification details stay available through disclosures instead of competing with the next
  action.
- The dark workshop palette, responsive left rail, keyboard-visible controls, and reduced-motion
  behavior remain.
- Interactive previews use pinned `<model-viewer>` 4.3.1. The viewer is a browser dependency, not
  repair or verification authority.

## Runtime boundaries and limitations

- The local flow uses the real Strands loop with a scripted zero-network provider.
- Draft intents and active approval sessions are in memory. Refresh works while the process is
  running; restart requires a new target story and ends active sessions.
- Job artifacts live below `build/web/jobs/{job_id}` and use opaque server-generated IDs.
- The local resolver semantically recognizes only a bounded set of explicit support-state language
  such as standing, hanging, or hovering. It does not infer appearance, project budgets, artistic
  intent, likely dimensions, or unsupported repair goals from prose.
- A later Bedrock integration may improve that collaboration, but must emit this same bounded schema
  and may not bypass deterministic inspection, explicit approval, or independent verification.
- The current product remains static-GLB repair only. It does not add rigging, skinning, animation,
  topology, UV, material, texture, transparency, emissive, or speculative artistic repair.

## Current automated evidence

- Intent construction is reproducible and canonical; tampering invalidates its hash.
- Invalid descriptions, target uses, and heights fail before a job exists.
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

## Next hosted step

When the AWS milestone is authorized, the Bedrock/Strands conversational layer should conduct the
same intake as a typed dialogue:

```text
user description
  -> bounded follow-up questions
  -> proposed AssetIntentProvenance fields
  -> user confirms exact target story
  -> deterministic workflow begins
```

That integration requires configured user-owned AWS credentials, selected model/region access, and
cost controls. It must remain optional in tests and must not broaden repair authority.
