# Asset Shepherd at the Inflection Point

**Status:** Direction accepted in D019; M9 implementation pending

**Date:** 2026-08-22

**Current implementation:** `main` at `adda928feea80b2db5c9c4196ef4b5cc171e7d6f`

**Controlling specifications:** `PROJECT_CONTRACT.md` and `REAL_WORLD_VALIDATION_PLAN.md`

This document is the single handoff for a product-direction review. It separates the product that
exists now from the conversational product we are considering next. It does not authorize AWS
work, paid model calls, new repair domains, or changes to the controlling contract.

## The decision in one sentence

Should Asset Shepherd remain a guided form that happens to use an agent, or become a persistent,
job-scoped conversation in which a Bedrock/Strands agent works on one asset with the user while a
deterministic core remains the sole authority for facts, repairs, approvals, and verification?

## Short answer and recommended direction

The stronger product hypothesis is the second model, with a strict qualification:

> The conversation owns collaboration and explanation. The deterministic core owns truth and
> execution.

The intended experience is analogous to working with Codex on a repository, but applied to one 3D
asset and hosted with Strands plus an Amazon Bedrock model. The user should be able to explain what
they meant to create, add the GLB, answer focused questions, inspect evidence, approve or reject a
bounded plan, and receive a verified package without learning the internal seven-stage pipeline.

This is an interaction-model change, not permission to turn the model into a geometry engine or to
broaden the current repair scope.

## What exists today

The current product is a local, server-rendered static-GLB workflow with a real Strands loop and a
scripted zero-network provider.

### Current user flow

```text
Describe intended asset, use, and real-world height
  -> Review and agree to an exact target story
  -> Select a versioned policy baseline
  -> Review rules or customize supported fields
  -> Upload one GLB
  -> Inspect deterministic findings
  -> Approve or reject grouped physical normalization, when proposed
  -> Independently verify
  -> Download the evidence package
```

The persistent rail presents **Describe → Agree → Inspect → Decide → Download**. Only one workflow
step is visible at a time. The former game-developer, artist, and technical-artist selector has been
retired from the primary UI; legacy routes redirect to the intent entry point.

### Current deterministic capabilities

For one static GLB up to 50 MB, the product can:

- validate the GLB container, references, buffers, embedded images, and supported structure;
- measure world-space bounds, represented height, dominant orientation, grounding, and transform
  hazards;
- count vertices, triangles, nodes, meshes, materials, textures, skins, animations, and morphs;
- apply project-policy checks for dimensions, naming, orientation, grounding, and budgets;
- derive deterministic safe display-name repairs;
- derive one reversible root normalization for scale, orientation, and grounding;
- require one explicit interrupt-bound approval for that physical normalization;
- preserve a rejection and leave unresolved findings explicit;
- reload and independently verify the candidate, including preservation invariants and a second
  planning pass;
- package the repaired GLB and structured evidence.

The contracted successful ZIP remains:

```text
repaired.glb
inspection.json
repair_plan.json
decisions.json
verification.json
provenance.json
report.md
```

### Current policy and intent records

Repository profiles are immutable versioned presets. A supported custom copy is schema-validated
and frozen per job with its base preset ID, explicit overrides, version, and canonical hash.
Findings cite the exact policy rule that caused them. Changing rules creates a new inspection/job.

The newly added `AssetIntentProvenance` record freezes:

- the original user description;
- static asset, rig-ready character, or playable-character intent;
- intended real-world height;
- the exact user-confirmed target story;
- version, opaque ID, confirmation time, and canonical hash.

The agreed height becomes the profile target state. Users do not enter matrices, rotations,
translations, or scale factors. The planner derives a minimal repair from measured facts and the
frozen target.

### Current trust boundary

The current system already enforces the boundary the envisioned product needs:

| Concern | Current authority |
|---|---|
| GLB facts and measurements | Deterministic inspector |
| Readiness rules | Frozen `ProjectProfile` |
| Finding generation | Deterministic inspector |
| Repair candidates | Registered deterministic planner |
| Consequential authorization | Human decision bound to the exact interrupt |
| File mutation | Deterministic repair engine |
| Success or failure | Independent verifier |
| Explanation and stage ordering | Strands agent and web presentation |

The model cannot invent a candidate action, accept an arbitrary transform from prose, bypass
approval, or declare an output ready.

### Current evidence

- 60 offline tests pass; one opt-in live-provider test is skipped.
- Ruff, formatting, Pyright, uv lock validation, and wheel build pass.
- Approved, rejected, clean-control, invalid-upload, and unsupported inspection-only paths are
  covered.
- The approved workflow produces the exact seven-file package and preserves the source.
- Patchling and Shader Lantern provide real GLB evidence; Shader Lantern completed deterministic,
  Blender, and isolated Unreal validation with its report-only triangle warning preserved.
- Desktop and compact web review show one focus area, no horizontal overflow, and no browser
  diagnostics.

### Current limitations

- The interaction is form-led, not a genuine adaptive conversation.
- Draft intent and approval state are in memory and disappear on server restart.
- The description is stored but not semantically compared with the source asset.
- The system cannot yet ask follow-ups based on inspection results.
- Only the current static-GLB safe-name and root-normalization repairs are supported.
- Rigging, skinning, animation, topology, UV, material, texture, transparency, emissive, and
  speculative artistic repairs are out of scope.
- The hosted AWS/Bedrock architecture, identity, model access, durable state, retention, and cost
  controls are not configured.
- Blender and Unreal are independent validation consumers, not hosted tools available to the agent.

## The envisioned product

The envisioned Asset Shepherd is a persistent conversation about one asset, not a chat box pasted
onto the existing form.

### Envisioned user experience

```text
User opens an asset workspace
  -> describes what they intended to make
  -> agent asks only the missing questions needed to define “ready”
  -> user confirms a structured target and source-preservation promise
  -> user uploads the GLB
  -> agent runs deterministic inspection tools
  -> agent explains the most important evidence in the user's language
  -> user and agent resolve ambiguity without changing facts
  -> deterministic planner produces the smallest supported plan
  -> user approves or rejects the consequential action
  -> deterministic repair and verification run
  -> agent explains the verified outcome, remaining warnings, and external handoffs
  -> user downloads the package and can continue the same job conversation
```

The conversation should feel collaborative: “Here is what I was trying to make; help me understand
what is wrong and get it ready.” It should not feel like a generic assistant improvising edits.

### What the Bedrock/Strands layer may do

- ask bounded follow-up questions about target use, dimensions, engine expectations, and appearance
  constraints;
- convert conversation into a proposed typed intent and policy override set;
- ask the user to confirm the exact structured target before inspection;
- call narrow, path-free deterministic tools in the correct order;
- summarize measured findings and cite their evidence and rule provenance;
- distinguish safe automatic work, approval-required work, report-only warnings, unsupported work,
  and external handoffs;
- present the exact registered plan and human-approval interrupt;
- explain verification results and package contents;
- retain job context so a user can ask follow-up questions about the same evidence.

### What the Bedrock/Strands layer may not do

- infer a fact when a deterministic tool can measure it;
- create, alter, or execute a repair candidate outside the registry;
- convert free text into an authorization record;
- silently modify a frozen target or project policy after upload;
- weaken approval classes, preservation invariants, verification gates, or readiness semantics;
- claim visual equivalence, material preservation, or engine compatibility without evidence;
- receive general shell access to Blender, Unreal, or the hosted runtime;
- expand unsupported repair domains because the user asks conversationally.

### Envisioned control flow

```text
Conversation
    |
    v
Proposed typed intent and policy
    |
    v
Explicit user confirmation
    |
    v
Frozen job state and source copy
    |
    v
Deterministic inspect -> plan
    |
    v
Human approval interrupt, if required
    |
    v
Deterministic repair -> independent verify -> package
    |
    v
Conversation explains only recorded evidence
```

### Envisioned hosted separation

The product direction does not imply putting Blender or Unreal inside Bedrock or AgentCore.

| Component | Proposed responsibility |
|---|---|
| Browser workspace | Conversation, preview, evidence, approval, download |
| Application API | Authentication, jobs, uploads, policy/intent persistence, retention |
| Strands agent with Bedrock model | Dialogue, typed intent proposal, tool orchestration, explanation |
| Deterministic Python core | Inspection, planning, registered repair, verification, packaging |
| Durable job store | Source, frozen policy/intent, interrupt state, evidence, output lifecycle |
| Blender validation worker | Optional independent offline or asynchronous acceptance evidence |
| Unreal validation worker | Optional separate Windows-based downstream integration evidence |

For the hackathon path, Blender and Unreal should remain local evaluation consumers. A later worker
integration, if justified, should expose only narrow typed validation operations and return
structured evidence; it should not expose an arbitrary terminal to the model.

## What changes and what does not

| Area | Current product | Envisioned model | Invariant? |
|---|---|---|---|
| Entry | Three-field intent form | Adaptive but bounded dialogue | Changes |
| Intent | User confirms generated story | User confirms agent-proposed typed target | Same boundary |
| Policy | User selects preset baseline and optional copy | Agent recommends or derives policy; advanced review remains | Needs decision |
| Upload | After intent agreement | During the same job conversation, after enough target context | Changes presentation |
| Inspection | Deterministic and immediate | Deterministic tool call explained conversationally | Invariant |
| Findings | Structured cards and disclosures | Structured evidence plus conversational explanation | Invariant facts |
| Repair plan | Deterministic registry | Deterministic registry | Invariant |
| Approval | Exact grouped interrupt | Exact grouped interrupt in conversation/workspace | Invariant |
| Repair | Safe names and approved root normalization | Same initial repair set | Invariant for first hosted release |
| Verification | Independent reload, invariants, second plan | Same, with conversational summary | Invariant |
| State | In-memory session | Durable resumable job conversation | Changes |
| Blender/Unreal | External validation evidence | External or later narrow workers | Invariant for initial hosted release |

## The product questions at this inflection point

These questions should be answered before M9 implementation begins.

1. **Conversation depth:** Should the first Bedrock release conduct only intent intake and
   explanation, or own the entire job conversation through download while deterministic tools keep
   execution authority?
2. **Policy selection:** Once the user supplies an intended height, the two current presets differ
   mostly in their default height band. Should the agent automatically select/derive the nearest
   policy and leave full rule choice under Advanced, rather than asking ordinary users to make a
   second scale-like choice?
3. **Target agreement timing:** Must intent be frozen before upload, or should the agent accept the
   source earlier and use deterministic inspection to ask better target questions before the user
   confirms the job definition?
4. **Unsupported intent:** Is it useful to accept “playable animated character” while clearly
   returning rigging/animation as external work, or does that create a product promise the static
   MVP cannot fulfill?
5. **Description semantics:** May the model use the description to flag a question such as “the
   requested glass/emissive appearance is not represented in the GLB,” provided it labels that as an
   unverified conversational observation rather than a deterministic finding?
6. **Conversation evidence:** Which agent utterances, user confirmations, tool calls, and summaries
   belong in durable provenance without bloating or exposing private conversation content?
7. **Durability:** What is the minimum session, interrupt, upload, and output persistence required
   for a credible hosted demo and safe resume behavior?
8. **Default interface:** Should the conversation replace the current forms, or should structured
   controls remain visible beside it as an inspectable source of truth?
9. **Evaluation:** What test corpus and human rubric prove that the conversation improves task
   completion and understanding without increasing unsafe authorizations or false claims?
10. **Scope gate:** Which exact conversational capabilities belong in M9, and which must wait until
    after the hackathon evidence and AWS mandatory checkpoint?

## Recommended staged transition

### Stage 1 — Preserve the current executable product

Keep the current form-led, zero-network workflow as the deterministic reference and offline
acceptance harness. Do not regress the existing package, approval, verification, or evidence gates.

### Stage 2 — Add a narrow Bedrock conversation over the same schemas

Use Bedrock/Strands to collect missing intent fields, propose `AssetIntentProvenance`, explain
deterministic findings, and present the existing approval interrupt. Require explicit confirmation
of typed state and continue to use the same deterministic tools. Keep the structured evidence views
available beside the conversation.

### Stage 3 — Make the job durable and resumable

Persist the conversation's structured state, source, frozen policy/intent, exact interrupt, and
artifacts with a documented retention and deletion policy. Prove refresh/restart/resume before
claiming a production-like hosted workflow.

### Stage 4 — Evaluate collaboration, not personality

Compare form-led and conversational completion on registered assets. Measure target-definition
accuracy, time to a correct approval decision, rejected unsafe suggestions, comprehension of
remaining warnings, and verified output rate. Do not use subjective “felt helpful” evidence alone.

### Stage 5 — Consider external validation workers only if evidence demands them

Keep Blender and Unreal outside the initial hosted runtime. Add narrow asynchronous validation
workers only when the deterministic product and evaluation show a concrete gap worth their cost,
security, licensing, and operational complexity.

## Proposed review standard

Approve the envisioned model only if it:

- makes the product materially easier to understand than the current form;
- preserves the deterministic core as the sole factual and execution authority;
- keeps consequential approval explicit and exact;
- does not imply repair capabilities the product lacks;
- produces durable, auditable state without storing unnecessary private dialogue;
- fits the M9 AWS, security, cost, and mandatory-checkpoint constraints;
- can be evaluated against the existing form-led baseline and real-world corpus.

## Requested reviewer output

Please return:

1. the strongest argument for and against this inflection;
2. a recommended product model for the hackathon release;
3. answers to the ten open questions above;
4. a smallest coherent M9 scope with explicit deferrals;
5. any contradiction with the current contract, safety model, or evaluation plan;
6. a proposed user journey in no more than eight steps;
7. the three highest-risk assumptions to validate before implementation.

## ChatGPT Pro review outcome

**Review date:** 2026-08-22

**Review source:**
<https://chatgpt.com/c/6a879ddd-f8e8-83ea-b153-e5ebf18c8615>

**Decision status:** Accepted by the user and recorded as D019. The decision authorizes the bounded
hosted interaction and durability direction described here. It does not authorize AWS activity,
paid model calls, new repair domains, or weaker safety boundaries.

### Reviewer recommendation

Adopt a **conversation-led, contract-anchored asset workspace**, while explicitly rejecting a
chat-only product.

The conversation should replace wizard sequencing as the primary interaction. A persistent,
visible **Job Contract** should remain beside it and expose the source, target, rules, measured
facts, findings, plan, decision, verification, and package status. The agent may collaborate,
explain, and call narrow typed tools. Deterministic code remains authoritative for measurements,
findings, candidate repairs, authorization validation, mutation, verification, and readiness. The
human remains the authority who grants or rejects consequential authorization.

The current form-led application should remain intact as the deterministic reference, offline
acceptance harness, comparison baseline, and deployment fallback.

### Answers to the ten product questions

| Question | Reviewed direction |
|---|---|
| Conversation depth | Keep the agent present from intake through download and evidence-grounded follow-up, without expanding its authority. |
| Policy selection | Ordinary users confirm a derived target and read-only rules summary; the system selects the nearest trusted baseline and freezes a schema-valid job copy. Advanced users retain supported rule customization. |
| Target timing | Accept the GLB before final target agreement and run objective, measurement-only preflight. Do not create policy-relative findings, a registered plan, approval interrupt, readiness result, or mutation until typed target confirmation. |
| Unsupported intent | Preserve the original request, but require acceptance of a narrower supported goal such as `static_mesh_for_external_rigging`. Otherwise return inspection-only diagnostics. Never claim that the result is playable. |
| Description semantics | Use description text to choose questions. Compare it with appearance-related facts only when deterministic material or texture metadata supports the statement. Classify each property as supported, contradicted, or not evaluated. |
| Conversation evidence | Package structured state transitions, confirmed intent, versions and hashes, a deterministic tool ledger, registered action and decision records, and artifact references. Exclude chain-of-thought, routine prose, hidden prompts, and the raw transcript. |
| Durability | Survive browser refresh, application restart, and agent-runtime restart. Persist the frozen source, state, interrupt, decisions, idempotency keys, artifacts, retention deadline, and bounded conversation state. |
| Default interface | Replace form-led navigation, not structured state. Keep the Job Contract inspectable and use a structured approval control; chat text cannot authorize repair. |
| Evaluation | Compare form-led and conversation-led paths on the same registered assets and controlled cases. Gate release on target accuracy, comprehension, safe decisions, verified outputs, and reliable resume rather than perceived friendliness. |
| Scope gate | Limit the first hosted conversation to bounded intake, typed confirmation, existing deterministic tools, exact approval, durable resume, evidence explanation, and the existing package. Defer all new repair domains and open-ended editing. |

### Smallest coherent hosted slice

Include:

- one durable workspace for one conversation, one source GLB, one frozen target, one policy, one
  deterministic plan, and one result package;
- early source hashing, structural eligibility checks, and objective measurements;
- at most three initial focused questions, with extra questions only for material contradictions or
  unsupported goals;
- an editable typed target card before confirmation and immutable state afterward;
- narrow, path-free Strands tools over the current inspector, planner, repair engine, verifier, and
  packager;
- explanations that cite finding IDs, measurements, and frozen policy rules;
- the existing exact grouped normalization interrupt, with approval or rejection bound to the
  registered action ID and hash;
- restart-safe, exactly-once resume and package behavior;
- post-verification questions limited to recorded evidence and external handoffs;
- the contract's existing AWS identity, model-access, budget, least-privilege, retention, and paid
  invocation checkpoints.

Explicitly defer:

- every new repair operation or editable safety rule;
- visual-model judgment and model-generated transforms;
- authorization through conversational prose;
- material, texture, transparency, emissive, topology, UV, rigging, animation, LOD, or collision
  edits;
- Blender or Unreal in AgentCore or as hosted workers;
- multi-asset conversations, cross-job memory, accounts, teams, shared profile libraries, arbitrary
  JSON policy upload, and open-ended post-completion editing;
- general shell or filesystem access and long-term transcript retention.

### Contract and decision conflicts requiring explicit resolution

1. **D012 and D018 ordering.** They require rule and target agreement before upload. The reviewed
   hosted flow permits upload and measurement-only preflight first. This is safe only if no
   policy-relative finding, plan, approval, repair, or readiness state exists before confirmation.
2. **Profile-selection language.** The project contract currently says the user selects a profile
   in the UI or supplies JSON. The reviewed ordinary-user flow confirms a frozen derived policy
   rather than choosing a named baseline. The resolved profile still must be schema-valid,
   versioned, hashed, and inspectable.
3. **D018 packaged description.** The current package freezes the exact original description and
   story. The review recommends packaged structured intent plus a canonical hash, with raw text
   retained privately for a short period or included only by explicit choice.
4. **Authority wording.** The human grants or rejects consequential authorization. Deterministic
   code validates its binding and enforces it. The agent owns neither authority.
5. **M9 gate.** Conversation and durability can be a bounded M9 product slice, but they do not
   replace the controlling M9 AWS deployment, logged-out-access, observability, retention, cleanup,
   and cost gates.
6. **Evidence standard.** The conversation-led model is the stronger hypothesis, not yet a proven
   stronger product. A controlled comparison must decide that claim.

No reviewed recommendation changes the GLB-only input boundary, source-preservation rules,
registered repair set, exact approval requirement, independent verification, seven-artifact
package, or real-world validation plan.

### Reviewed eight-step user journey

1. Describe the intended object and use in one sentence, then upload one GLB.
2. Asset Shepherd hashes, validates, and measures the untouched source without planning repairs.
3. The agent asks only questions required by missing context, measured contradictions, or unsupported
   intent.
4. The user edits and explicitly confirms the typed target, supported job goal, derived rules, and
   external handoffs.
5. Deterministic tools inspect and register the smallest supported plan; the agent explains cited
   evidence.
6. The user approves or rejects the exact grouped normalization through a structured interrupt.
7. Deterministic tools repair a copy, independently verify it, and package the seven artifacts.
8. The user downloads the result and may ask evidence-only questions until the job is deleted or
   expires.

### Highest-risk assumptions

1. Conversation improves target accuracy, completion time, or comprehension without increasing
   unsafe authorization or false-readiness claims.
2. Users understand the difference between measured source facts and a provisional target that has
   not yet been confirmed.
3. Durable Bedrock/Strands interruption and exactly-once resume remain reliable and affordable
   across browser, application, and runtime restarts.

### Codex assessment and proposed disposition

The recommendation is coherent and preserves Asset Shepherd's safety thesis. The Job Contract is
the essential qualification: the product should feel conversational without making policy,
evidence, or approval disappear into prose.

D019 records the approved direction and requires implementation to:

- makes conversation the primary hosted navigation but keeps visible structured state and the
  current form-led reference path;
- permits only objective preflight before typed target confirmation;
- derives and freezes the ordinary user's policy while retaining Advanced review and supported
  customization;
- separates original intent from a narrower supported job goal;
- makes structured controls the only authorization mechanism;
- minimizes packaged conversation data; and
- treats conversation/durability as bounded additions to M9 without weakening its existing AWS,
  deployment, cost, and access gate.

D019 supersedes D012 and the ordering portion of D018 for the hosted M9 path. The M8 form-led
behavior remains the executable reference until the versioned M9 implementation passes its gate.
No AWS activity or paid model invocation is authorized yet.
