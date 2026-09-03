# Asset Shepherd Project Contract

**Repository:** `jcgennaro/asset-shepherd`  
**Track:** Professional Agents  
**Hackathon:** Agents for Humans  
**Submission deadline:** September 14, 2026 at 5:00 p.m. Pacific  
**Internal submission target:** September 13, 2026  
**Document version:** 2.4
**Controlling status:** Approved project contract once committed by the user  
**Approved amendments:** D019 conversation-led hosted workspace, D021 parameterized policy family,
D022 minimum target-intake contract, D023 provider-neutral semantic intake, D036 agent-orchestrated
sensing and disposition, D042 upload-first two-text UX, D047 seam-aware duplicate-position
handling, D048 attribute-seam presentation, D049 subtitle-free task screens and tolerant provider
normalization, D050 proportional target-box fitting and weld disclosure, D053 bounded
agent-selected pivot placement, D064 source-bound measured pivot anchors, D065 agent-message
identity, D077 per-asset model-neutral Bedrock allowlist, and D092 use-case-driven controlled mesh
simplification, and D100 typed sequential repair continuation, through 2026-09-03

---

## 1. Purpose and authority

This document is the controlling product, engineering, execution, and submission contract for Asset Shepherd. It exists so Codex can carry the project from the current repository bootstrap through hackathon submission with minimal design supervision.

Codex must read this document and the current project status before beginning any work. It must evaluate every implementation step against the requirements and milestone gates here. It may make routine implementation decisions autonomously, but it may not silently change the product scope, repair safety model, public promise, hackathon track, or submission strategy.

This contract is intentionally more authoritative than chat history, speculative notes, old prompts, or code comments. When instructions conflict, use this priority order:

1. A direct, current instruction from the user.
2. This project contract.
3. `docs/PROJECT_STATUS.md` and approved decision records.
4. The current code and tests.
5. Earlier chat, temporary plans, and implementation guesses.

This contract should remain stable. Changes to it require an explicit user decision and a dated entry in `docs/DECISIONS.md`. Codex should update project status, not casually rewrite the contract to make completed work appear compliant. That maneuver is popular in bureaucracies and will not be imported into this repository.

---

## 2. Mission

Asset Shepherd is an autonomous 3D-asset intake and normalization agent for indie game developers and technical artists.

A user provides a static 3D asset and describes the result they are trying to achieve. Asset
Shepherd's workflow agent:

1. Determines what it needs to learn and calls deterministic sensing tools.
2. Interprets measured and rendered evidence against the confirmed user goal.
3. Decides whether to accept, inspect further, ask, report, repair, or stop.
4. Chooses supported repair tools and typed parameters when a repair is warranted.
5. Requests human approval before any consequential physical or artistic change.
6. Re-observes every candidate, independently verifies invariants, and iterates when useful.
7. Returns a validated asset package or honest diagnostics with a clear before-and-after report.

The product does real work. It must produce an actual repaired asset and verification evidence, not merely discuss what a technical artist could do manually.

---

## 3. Winning product thesis

Game developers repeatedly acquire assets from marketplaces, contractors, procedural tools, and generative systems. Those assets often import at the wrong scale, lie on the wrong axis, float above or below the ground, use invalid or duplicate names, exceed project budgets, or contain structural surprises. The repetitive work is not creative modeling. It is inspection, diagnosis, cautious normalization, re-import, and verification.

Asset Shepherd turns that workflow into exception supervision:

- Deterministic sensors measure facts and produce standardized visual evidence.
- The agent interprets those facts against project intent.
- The agent chooses which supported actions to request and with which typed parameters.
- Consequential transformations wait for human approval.
- Deterministic enforcement constrains every action, and verification is independent of the agent's
  verbal confidence.

The demo must make this visible within seconds: a broken robot enters, one meaningful approval is requested, and a correctly scaled, upright, grounded, valid asset exits with evidence.

---

## 4. Hackathon compliance and judging strategy

The project is entered in the **Professional Agents** track.

The official hackathon requirements, checked when this contract was written, include:

- Build a new agent with the Strands Agents SDK during the submission period.
- Handle a real task end to end rather than acting as a chat-only assistant.
- Submit a public code repository with the required source, assets, setup instructions, README, and an MIT or Apache license visible on the repository page.
- Include an architecture diagram.
- Include a public YouTube or Vimeo video no longer than five minutes.
- The video must demonstrate the working product and explain the problem, audience, and importance.
- Include an AWS Builder ID.
- Provide free testing access through the judging period.
- A live demo and Amazon Bedrock AgentCore deployment are optional but strengthen Technical Implementation.
- Up to three public `builder.aws.com` posts can add 0.2 points each, up to 0.6 points. The current
  rules remove the literal `#AgentsforHumans` requirement; the safest title still includes the plain
  words **Agents for Humans** because lower rule text retains that wording.

Codex must recheck the current official rules before release because hackathon pages can change. The final submission checklist must use the rules as they exist at submission time.

### 4.1 Judging priorities

The five judging dimensions are equally weighted. Product decisions must serve all five:

**Technical Implementation**

- Genuine Strands agent loop.
- Custom deterministic tools.
- Structured outputs.
- Human-in-the-loop interruption and resume.
- Verification loop.
- Observable traces and tool metrics.
- Prefer AgentCore deployment if it is stable and does not endanger the deadline.

**Design**

- A coherent upload-to-download experience.
- Clear findings and consequences.
- No raw model monologue as the primary UI.
- A visibly useful repaired artifact.

**Potential Impact**

- Specific audience: indie developers and technical artists.
- Concrete repetitive workflow.
- Actual time and error reduction measured on fixtures or trials.

**Creativity and Originality**

- 3D technical-art workflow rather than another email or calendar agent.
- Agent judgment is paired with geometry tools and safety policy.

**Presentation**

- Broken asset versus corrected asset is instantly legible.
- The video shows the complete workflow, not architecture slides pretending to be a product.

### 4.2 Prize-oriented priorities

When time is constrained, use this order:

1. Reliable end-to-end demo.
2. Clear product experience.
3. Genuine Strands use and human approval.
4. Verifiable repair quality.
5. Stable AWS deployment.
6. Broader format support or additional repair types.

A narrow system that works is superior to a universal importer whose only stable feature is an exception trace.

---

## 5. Current repository baseline

The repository was created during the hackathon period and initialized as a Python 3.12 project using `uv` and a `src` layout.

Baseline setup commit:

```text
112b649d52009ffa544f7787fb4c0d59efc39272
chore: initialize Python project
```

The baseline includes:

- MIT license.
- `strands-agents` runtime dependency.
- `pytest`, Ruff, and Pyright development dependencies.
- Strict type checking.
- An import-only smoke test.
- No product implementation, AWS architecture, generic Strands tools package, or 3D libraries yet.

All future work occurs directly on `main`. Do not create feature branches or pull requests unless the user explicitly reverses that rule.

---

## 6. Product contract

### 6.1 Primary user

An indie game developer or technical artist who needs to evaluate and normalize a newly acquired static 3D asset before importing it into a game project.

### 6.2 Core user job

> Tell me what is wrong with this asset, fix what is mechanically safe, ask me only about consequential changes, and prove that the final asset satisfies my project conventions.

### 6.3 MVP input

The hackathon MVP accepts:

- Exactly one `.glb` file using glTF 2.0.
- Maximum hosted file size: 50 MB.
- Static mesh content.
- Embedded materials and images are allowed.
- One resolved project profile supplied as JSON for deterministic tooling or derived for a new web
  job from the trusted versioned policy family and explicitly confirmed in the hosted UI.

A file containing skins, animations, or morph targets may be inspected, but the MVP must refuse structural repair and explain why.

The MVP does not accept FBX, OBJ, loose `.gltf` packages, ZIP archives, or multiple assets in one job.

### 6.4 Coordinate and unit semantics

Asset Shepherd must respect glTF semantics rather than redefining them around Unreal Engine:

- glTF uses meters for linear distance.
- glTF is right-handed.
- glTF uses positive Y as up.

The project profile may display centimeters because game developers commonly think in centimeters, but all internal calculations must use meters with explicit conversion.

A 180-unit-tall glTF asset represents a 180-meter object, not a 180-centimeter object. A scale repair should make the represented object physically correct while preserving standards-compliant glTF semantics.

### 6.5 Project profile

The profile describes the target project's expectations. The initial schema must support:

```yaml
profile_version: 1
name: Unreal Indie Robot
engine: unreal
asset_type: static_mesh

expected_height_cm:
  target: 180
  tolerance: 10

orientation:
  require_y_up_geometry: true
  require_ground_contact: true
  ground_tolerance_cm: 1

naming:
  pattern: "^[A-Z][A-Za-z0-9_]*$"
  require_unique_node_names: true
  require_unique_mesh_names: true

budgets:
  max_triangles: 100000
  max_materials: 8
  max_textures: 16
  max_texture_dimension: 4096

repair_policy:
  auto_rename: true
  require_approval_for_normalization_transform: true
```

The production schema must be JSON and versioned. YAML above is explanatory only. Historical
profiles may retain `infer_vertical_from_dominant_extent` for artifact compatibility, but the
corrected product must not use dominant extent to infer semantic vertical, emit an orientation
finding, or create a rotation. Project-policy fields supply constraints and preferences to the agent;
they do not generate contextual conclusions without agent reasoning.

### 6.6 Required output package

A successful job produces a ZIP containing:

```text
repaired.glb
inspection.json
repair_plan.json
decisions.json
verification.json
provenance.json
report.md
```

`provenance.json` must include at least:

- Source SHA-256.
- Output SHA-256.
- Profile identifier and version.
- Application version or commit SHA.
- Relevant library versions.
- Repair actions executed.
- User approvals and rejections.
- Start and completion timestamps.

A blocked or failed job should still provide diagnostic files that were safely produced. It must not label an unverified file as project-ready.

### 6.7 Hosted conversational job definition

For the M9 hosted path, Asset Shepherd is conversation-led but contract-anchored. Conversation is
the primary navigation model; it is not the source of record for target state, policy, findings,
authorization, or readiness.

The hosted workspace must display an inspectable structured **Job Contract** containing source
status, intended target, rules, measured facts and renders, agent assessments, proposed actions,
decision state, verification, and package status.

After minimal user context, the hosted path may accept and hash the GLB before final target
agreement. Before confirmation it may perform only objective preflight: structural eligibility,
represented dimensions, transforms and ground-plane relationship, supported-feature counts, resource
counts, and deterministically available material or texture metadata. This state must be labeled as
measured source facts with no agreed target. It must not create a target-dependent assessment,
proposed action, approval interrupt, mutation, or readiness result.

Before offering target confirmation, the agent must satisfy the versioned minimum target-intake
contract. It requires a normalized asset description, one supported intended-use value, positive
intended real-world target dimensions, and one ordinary-language viewing-use choice. Every populated target field must retain concise source
evidence and confidence of at least 0.8; a missing, ambiguous, conflicting, or lower-confidence
required field remains explicitly missing. The agent should infer a useful target proposal from the
user's ordinary words, including semantic object scale when no number is supplied, and ask only
when materially different interpretations remain below the confidence gate. It must never
substitute measured source dimensions for intended dimensions. Grounding, naming, tolerances, and
resource budgets are resolved-policy parameters, not mandatory intake questions. The user may
adjust and must confirm the complete typed target once before any policy-relative inspection. Every
provider, including the interim OpenAI implementation and the intended Bedrock implementation,
must emit the same server-validated public schema; model prose alone is not target state. The model
may later choose typed parameters for supported action tools, but it cannot expose raw transforms as
user controls, expand repair domains, authorize an action, bypass tool validation, or declare
invariant readiness.

Ordinary users confirm a schema-valid job-scoped policy resolved from one trusted, immutable,
versioned parameterized family. They do not choose a named scale baseline or re-enter target state
already present in the confirmed intent. The resolver may use confirmed intent to choose supported
target-state parameters, uses family defaults when project-specific information is absent, and may
use objective preflight only to inform questions or evidence--never to loosen target rules until the
current asset passes. The full resolved rules remain visible and frozen with identifier, policy
family identifier, explicit differences from the family, per-rule source, version, and canonical
hash. Advanced users retain only the supported `ProjectProfile` fields already enforced by the
deterministic engine. Changing confirmed intent or rules creates a new inspection and job.

Original intent must be distinct from the supported job goal. Unsupported playable-character,
rigging, skinning, or animation intent may be preserved as context only when the user explicitly
accepts a narrowed static-mesh or inspection-only goal. The product must not claim unsupported
readiness.

### 6.8 Agent-orchestrated job definition

The workflow defined in `docs/AGENT_ORCHESTRATED_WORKFLOW.md` is controlling. The agent chooses its
sensors, forms target-dependent conclusions, chooses the disposition, and initiates every mutation.
Deterministic code supplies observations, action previews, invariant enforcement, exact mutation,
verification, and packaging. It must not manufacture a variable repair plan from a project profile
or shape heuristic.

This amendment preserves the narrow supported mutation domain and exact human authorization. It
changes who decides that a repair is warranted and how it is composed. A live workflow model, not
the scripted test double, must demonstrate that behavior before the hosted agent milestone passes.

---

## 7. MVP inspection contract

The deterministic inspector must report facts before the agent interprets them.

### 7.1 Package and structural facts

- File hash and byte size.
- glTF asset version and generator metadata.
- Parse success or failure.
- Scene count and active scene.
- Node, mesh, primitive, material, texture, image, skin, animation, and camera counts.
- Used extensions and required extensions.
- Presence of morph targets.

### 7.2 Geometry facts

- Vertex and triangle counts.
- World-space axis-aligned bounds.
- Dimensions in meters and centimeters.
- World-space minimum and maximum coordinates.
- File world origin, root world origins, bounds center, and footprint center-bottom.
- Dominant dimension axis.
- Whether the asset intersects, floats above, or extends below the Y=0 ground plane.

### 7.3 Transform facts

- Root nodes.
- Non-identity translation, rotation, and scale.
- Negative determinant transforms.
- Non-uniform scales.
- Parent-child transform hierarchy summary.

### 7.4 Naming facts

- Missing names.
- Duplicate node names.
- Duplicate mesh names.
- Exact node and mesh display-name inventory.

Whether a name violates the confirmed project expectation and whether it should be changed are
target-dependent agent conclusions. A deterministic naming tool may validate or preview a specific
replacement requested by the agent.

### 7.5 Materials and textures

- Material and texture counts.
- Texture dimensions and formats when readable.
- Budget violations.
- Missing or unreadable embedded image data.
- Apparent duplicate resources may be reported, but the MVP must not merge them.

### 7.6 Repair eligibility

The inspector must set a repair-eligibility result:

- `ELIGIBLE_STATIC_MESH`
- `INSPECTION_ONLY_UNSUPPORTED_FEATURES`
- `INVALID_OR_UNREADABLE`

A repair job must not proceed when eligibility is not `ELIGIBLE_STATIC_MESH`.

---

## 8. Assessment and evidence model

Universal-invariant tools may emit deterministic failures. Target-dependent findings are agent
assessments grounded in sensor observations and the confirmed goal. Every recorded assessment must
contain:

```text
id
code
domain
title
description
severity
action_class
confidence
affected_components
evidence
profile_rule
candidate_repairs
```

`candidate_repairs` is retained for schema migration only. In the corrected architecture it records
agent-proposed typed actions; the inspector does not populate it from a heuristic planner.

### 8.1 Severity

- `INFO`: useful fact or recommendation.
- `WARNING`: likely project issue, but asset can remain usable.
- `ERROR`: violates an explicit profile rule or materially harms import readiness.
- `BLOCKER`: prevents safe repair or verification.

### 8.2 Action class

- `REPORT_ONLY`
- `AUTO_SAFE`
- `APPROVAL_REQUIRED`
- `BLOCKED`

Severity and action class are separate. A serious budget concern can be report-only, while a minor
naming defect may be preauthorized. Preauthorization does not remove the requirement for an agent to
initiate the action.

### 8.3 Evidence discipline

The system must distinguish observation from inference.

Example:

```text
Observation: world-space height is 180.0 meters.
Profile: target height is 1.8 meters ± 0.1 meters.
Inference: a scale factor of 0.01 would place the asset at the target height.
Confidence: 0.99.
```

The agent may explain this inference. It may not invent dimensions or pretend a heuristic is a measurement.

---

## 9. Repair safety contract

### 9.1 General invariants

1. Never overwrite the source file.
2. Never execute data or code contained in the uploaded asset.
3. Every repair must cite a finding and an authorization source.
4. Deterministic tools perform all binary and geometry changes.
5. The agent cannot bypass repair policy.
6. The repaired output must be independently re-inspected.
7. Failed verification must prevent project-ready status.
8. Rejected repairs stay rejected for the job.
9. The source hash must remain unchanged.
10. Running the same approved repair pipeline twice must be semantically idempotent.

### 9.2 Preauthorized non-consequential repairs in the MVP

The agent may explicitly initiate the following typed actions when the confirmed project rules
preauthorize them:

- Assign deterministic valid names to unnamed nodes and meshes.
- Normalize invalid node and mesh names according to the project pattern.
- Make duplicate node and mesh names unique with deterministic suffixes.
- Re-serialize the GLB without changing geometry, materials, or textures when necessary for valid output packaging.
- Compact exact duplicate complete vertex tuples only when the agent explicitly requests it and
  deterministic inspection proves that POSITION and every accompanying attribute are byte-identical.
  Position-only matches across UV, normal, tangent, color, joint, or weight seams are never merged.

Attribute-separated duplicates are normal glTF representation, not user-facing defects. They must
not be presented as a choice whose approval could make an attribute-damaging weld safe. The
read-only position projection may expose residual boundary, non-manifold, and winding evidence for
agent interpretation, but it never authorizes topology mutation.

Name changes may be considered non-consequential because glTF references nodes and meshes by index,
not by display name. The implementation must still prove that indices and references remain intact.
No background pass applies them merely because an inspector found a name it dislikes.

The MVP should not automatically delete nodes, resources, materials, or textures. Such cleanup is deceptively easy to describe and annoyingly capable of amputating semantics.

### 9.3 Consequential repair primitives in the MVP

The first consequential action capability is a reversible root transform that the agent may compose from an
explicitly chosen subset of:

- Physical scale correction.
- A specific root rotation selected by the agent from target and sensor evidence.
- A specific root translation selected by the agent, including grounding when appropriate.
- A bounded pivot-placement translation selected by the agent: preserve the authored origin, place
  the world-bounds center or footprint center-bottom at the origin, or select one exact
  source-bound geometry landmark previously returned by the pivot-sensing tool.

The deterministic preview of the agent-requested transform must include:

- Before bounds and dimensions.
- Proposed 4×4 transform matrix.
- Expected after bounds and dimensions.
- Evidence and confidence for each component.
- A plain-language consequence summary.
- The option to approve or reject.

The implementation should prefer a reversible, standards-compliant root normalization transform over destructive vertex baking for the MVP. A top-level normalization node is acceptable if it round-trips correctly and verification proves the resulting world-space asset is correct.

Grounding and pivot placement are distinct target conditions. A grounded model may still have a
rear-edge or otherwise inconvenient pivot. The agent may choose a bounded pivot target only when
the confirmed use and measured evidence justify it. The sensor may enumerate exact bounds centers,
bounds corners, triangle-area centroid, long-axis end-region centers, and a uniform-density volume
centroid only when closed consistently wound topology proves that calculation valid. The agent
selects an opaque candidate ID after comparing coordinate-labeled views; it never supplies XYZ.
Hinged, hanging, rigged, articulated, or ambiguous assets retain their authored pivot or require
clarification when no measured candidate clearly represents the requested feature.

The agent should group compatible scale, rotation, pivot placement, and translation into one
coherent approval card
when its reasoning says they form one operation. The deterministic layer must neither insert a
component the agent did not request nor split the decision into scripted fragments.

Confirmed X/Y/Z target lengths are approximate evidence for one final-pose bounding box. After any
agent-requested orientation, the deterministic preview chooses one uniform proportional scale that
minimizes squared log-relative error across all three axes. It must preserve proportions and report
the residual on every axis. A single residual is not an exact acceptance requirement and cannot, by
itself, justify rejecting an otherwise correctly executed and visually preserved candidate.

The second consequential capability is one narrow degenerate-geometry cleanup. The agent may
request it only when deterministic inspection proves an indexed `TRIANGLES` primitive uses dense,
unextended, cardinality-matched attributes and contains either a repeated-index or scale-relative
zero-area triangle, or complete vertex tuples that no surviving triangle references. The exact
preview must list the affected mesh/primitive, before and after triangle and vertex counts, and the
number of proven removals. It requires explicit approval and must run separately from physical
normalization or vertex-tuple welding.

Execution removes only the proven zero-area index triples, compacts only complete vertex tuples no
surviving triangle references, remaps every aligned attribute together, and keeps the source binary
as an immutable prefix of append-only repaired accessors. It must fail closed for strips, fans,
non-indexed primitives, sparse or extended accessors, malformed cardinality, out-of-range indices,
morph targets, compressed primitives, unknown attributes, or a cleanup that would remove every
triangle. It never welds positions, crosses UV or normal seams, fills holes, recalculates normals,
remeshes, deletes a semantic component, or changes materials or textures.

The third consequential capability is bounded disconnected-component selection. Inspection may
enumerate exact position-projected, vertex-connected triangle bodies within one primitive and give
each one a stable source-bound ID. Small-gap AABB probes may group nearby bodies at several
scale-relative tolerances for interpretation, but those groups are diagnostic only: they never
weld geometry, change exact IDs, select a body, or authorize deletion. Disconnected bodies are
geometric facts rather than semantic errors.

Only the workflow agent may propose exact component IDs after comparing the confirmed expected
piece count with structured inventory and all four labeled source views. The user may keep, remove,
or comment on each body; any change to the proposed selection starts a fresh planning turn, and one
overall approval binds the exact keep/remove partition. There is no remove-small, keep-largest, or
automatic extra-body rule, and at least one body must remain in every affected primitive.

The first implementation is restricted to one-instance, unskinned, indexed `TRIANGLES` primitives
with no morph targets, compression, sparse accessors, accessor extensions, malformed indices,
cardinality mismatch, or pending degenerate cleanup. Execution filters only approved triangle
indices and appends a replacement index accessor while preserving retained expanded corner
attributes and the original binary prefix. Unreferenced vertex tuples left by this operation remain
visible to the existing diagnostic and may be compacted only in a separate approved cleanup turn.
Independent verification must reproduce the retained component count and exact authorized triangle
delta. Ambiguous or unsupported layouts remain report-only or return to the creation tool.

The fourth consequential capability is controlled mesh simplification. At target confirmation the
user chooses one nontechnical viewing use: close-up/showcase, normal gameplay, or
small/distant/repeated. The frozen policy maps those choices to soft caps of 50,000, 15,000, and
2,500 triangles respectively. The agent may propose one lossy simplification only when the asset is
over that cap and inspection proves a supported layout. The UI must explain the measured count,
use-case recommendation, original preservation, and the option to reject and keep full detail; it
must not ask ordinary users for a reduction percentage or polygon budget.

Simplification runs separately for each original exact component, preserves complete source vertex
tuples and their normals, UVs, material assignments, and named nodes, and copies every component
below 1,000 triangles unchanged. It is restricted to dense dedicated accessors on indexed
`TRIANGLES` primitives with no skin, morph target, compression, malformed indices, or pending
degenerate cleanup. It must preserve the bounded near-contact component grouping, keep bounds
within two percent, retain a nonempty mesh, and reload independently. It may stop above the soft cap
when those safeguards bind. Fresh visual comparison and measured post-export triangle and byte
counts are mandatory; predicted file-size savings are prohibited.

### 9.4 `REPORT_ONLY` findings

The MVP reports but does not repair:

- Triangle budget violations for layouts where controlled simplification is unavailable, declined,
  or unable to reach the soft cap safely.
- Material count violations.
- Texture count and dimension violations.
- Negative or non-uniform transforms that are not part of the approved normalization operation.
- Apparent duplicate materials or textures.
- Pivot preferences beyond the two bounded center targets.

### 9.5 `BLOCKED` operations

The MVP must refuse:

- Skin or skeletal changes.
- Animation changes.
- Morph-target changes.
- Topology repair or remeshing beyond the exact approved degenerate cleanup, component selection,
  and controlled simplification capabilities in 9.3.
- UV generation or modification.
- LOD generation.
- Collision generation.
- Material merging.
- Texture generation, compression, resizing, or artistic edits.
- Repairs involving unsupported required extensions.
- Any change whose references cannot be preserved and verified.

---

## 10. Deterministic verification contract

Verification is not a prose opinion from the same model that planned the repair.

The output must be reloaded from disk and independently inspected. Verification must check:

- The output parses successfully.
- The output passes the selected glTF validation mechanism.
- Source and output hashes are recorded.
- Triangle, vertex, material, and texture counts remain unchanged unless a future authorized repair explicitly permits a change.
- Names satisfy the profile and are unique.
- Each executed action satisfies the exact deterministic postconditions declared by its approved
  preview.
- Scale, rotation, and translation results match the exact agent-requested and user-approved action,
  without using dominant extent as a semantic proxy.
- Rejected repairs were not applied.
- All executed actions appear in provenance.
- No unrequested mutation occurred.

The agent must then reassess target satisfaction using fresh sensor evidence, including standardized
renders when appearance or pose matters. An empty deterministic plan is not evidence of semantic
correctness because deterministic code no longer owns contextual planning.

Verification states:

- `PASSED_PROJECT_READY`
- `PASSED_WITH_REMAINING_WARNINGS`
- `FAILED`
- `BLOCKED`

Only the first two may include `repaired.glb` as a ready candidate. The report must clearly list remaining warnings.

---

## 11. Synthetic fixture contract

The project must generate its own deterministic demo assets during the hackathon.

### 11.1 Clean robot fixture

Create a visually recognizable static robot from simple primitives. It should:

- Be approximately 1.8 meters tall.
- Be Y-up.
- Stand on Y=0.
- Use valid unique names.
- Remain within profile budgets.
- Use a small number of distinguishable materials.
- Contain no skin, animation, or morph targets.

### 11.2 Broken robot fixture

Derive a broken fixture deterministically with known defects:

- Approximately 100× too large.
- Rotated so its longest axis is not Y and it appears to lie on its side.
- Translated so it is not grounded.
- Duplicate and invalid node or mesh names.
- At least one texture or material budget warning if practical without destabilizing the fixture generator.

A machine-readable expected-defects manifest must accompany each generated fixture.

### 11.3 Fixture acceptance

- Fixture generation is reproducible from a clean checkout.
- Clean and broken files are visually distinguishable.
- Expected defects are known before inspection.
- No third-party copyrighted asset is required for automated tests.
- A prettier CC0 or original demo asset may be added later, but it cannot replace deterministic fixtures as the test foundation.

---

## 12. Technical architecture

### 12.1 Layering

```text
Web or CLI Interface
        ↓
Strands Agent Orchestrator
        ↓
Typed Tool Boundary
        ↓
Deterministic Asset Core
  ├─ Load and validate
  ├─ Measure and render observations
  ├─ Preview requested action consequences
  ├─ Apply authorized agent-requested actions
  ├─ Verify invariants and declared postconditions
  └─ Package artifacts
        ↓
Local filesystem or AWS object storage
```

### 12.2 Required separation

**Deterministic core owns:**

- Parsing.
- Geometry and transform calculations.
- Measured and rendered sensor evidence.
- Universal-invariant failures.
- Exact matrices and consequences for actions requested by the agent.
- File mutation.
- Validation.
- Hashing.
- Packaging.

**Strands agent owns:**

- Choosing when to call tools.
- Choosing which sensors are needed.
- Interpreting observations against the confirmed target.
- Creating and revising target-dependent findings.
- Choosing supported action tools and typed parameters.
- Choosing the disposition: accept, investigate, ask, report, repair, or stop.
- Explaining proposed consequences and uncertainty.
- Grouping approval decisions.
- Pausing and resuming for human input.
- Re-observing every candidate and iterating within explicit operational limits.
- Responding to deterministic verification failures without overriding them.
- Producing a concise final summary.

**The user owns:**

- Approval or rejection of consequential repairs.
- AWS account and credential actions.
- Public release and final submission.

### 12.3 Library-selection rule

Codex must perform a short capability spike before selecting the GLB implementation stack. Evaluate plausible Python libraries against:

- GLB load and save.
- Scene graph access.
- World-transform evaluation.
- Embedded materials and images.
- Preservation of unknown or unused fields where practical.
- Root normalization transform support.
- Linux and ARM64 compatibility.
- License compatibility.
- Deterministic testing.

The expected likely stack is some combination of NumPy, a glTF structure library, a geometry library, and Pillow. This is not mandatory. The selected approach must be recorded in an architecture decision record with actual round-trip evidence.

Do not introduce Blender as a hosted runtime dependency unless the lighter stack fails a written acceptance test and the user approves the deployment cost and complexity. Blender may be used locally to create or inspect demo media, but the product should not casually ship an entire DCC application to rename six nodes.

### 12.4 API and data modeling

Use strict typed models and versioned JSON. Pydantic v2 is preferred unless the capability spike finds a concrete conflict.

All tool inputs and outputs must be JSON-serializable and validated. The agent must receive structured data rather than scraping human-formatted reports.

### 12.5 Deterministic tool harness

The deterministic core must remain independently testable through a CLI. This is a repair-engine and
invariant harness, not the product decision maker. Variable actions require explicit typed parameters
that stand in for an agent tool call; the CLI must not infer a contextual repair plan.

Expected commands may include:

```text
asset-shepherd inspect
asset-shepherd preview-action
asset-shepherd repair
asset-shepherd verify
asset-shepherd fixtures generate
```

Exact command names may be adjusted for coherence. The CLI must support non-network testing with an
explicit action request and approvals JSON file.

### 12.6 Web interface

The hosted final experience should provide:

1. A persistent job-scoped conversation from bounded intake through evidence-grounded completion.
2. GLB upload with objective preflight before final target agreement.
3. An editable typed target card before confirmation and a frozen structured Job Contract after it.
4. A visible resolved policy summary, with supported advanced rule customization.
5. Agent assessments grouped around the current decision, with sensor evidence available on demand.
6. One exact approval card for the current agent-proposed consequential action; its structured
   control is the only authorization path.
7. Before and after 3D preview, verification summary, and downloadable result ZIP.
8. Durable refresh, application-restart, and agent-runtime-restart resume behavior.

The authoritative public flow is **Gallery → Upload → Describe → Shepherd → Refine**. Gallery is
workspace selection, not a numbered step. Upload performs only container validation and objective
preflight. Description then supplies the minimum target context. Shepherd produces the first
assessed candidate. The user selects either that candidate or its input as Iteration 1; Refine then
loops as 4.1, 4.2, and so on, with a fresh assessment and approval boundary every time. Download is
an outcome, not another workflow step.

Every Refine screen and source route must use the selected immutable iteration, never silently fall
back to the original upload. Bounds, component inventory, and origin relationships must be measured
from geometry referenced by that iteration's surviving primitives. Unreferenced tuples may remain
as a separately reviewable cleanup finding, but cannot inflate framing or bounds. A component
deletion does not authorize pivot movement: it invalidates earlier bounds/pivot evidence and any
later pivot change requires a fresh agent proposal and explicit approval.

Every default screen has one global workspace title. It may add at most one agent-authored
informative sentence for the current decision. Do not stack eyebrow labels, step counts, section
titles, card titles, subtitles, or duplicate state summaries. Control labels and factual row labels
must be concise and must not restate the title. Complete policy, evidence, and provenance remain
available through closed disclosures or the on-demand Job details dialog. Dialogs may carry the one
title needed for their own accessible context.

No default task screen may show a subtitle, field caption, or label that merely renames the only
input or repeats the instruction already given by the global title or agent sentence. Accessible
names remain required through semantic markup or ARIA and need not be visible when the control's
purpose is already unambiguous. New visible title-like copy requires task-specific information that
the user could not infer from the existing title, sentence, control, or workflow rail.

When endpoint clarification is necessary, the one agent sentence is `Select target engine.` The
selector may link canonical engine names to their official sites, but it must not modify or animate
third-party logos without applicable trademark permission. Product-owned abstract motion is
acceptable and must respect reduced-motion preferences.

The M8 form-led application remains the deterministic reference implementation, offline acceptance
harness, comparison baseline, and deployment fallback. M9 may change hosted navigation without
weakening its tests or binary-output contract.

The UI must not expose private chain-of-thought or treat streaming token text as proof of work.

A lightweight framework is acceptable. Codex may choose the implementation after the CLI is complete, prioritizing rapid deployment, file upload, and GLB preview. The choice must not force the deterministic core into UI-specific code.

---

## 13. Strands implementation contract

### 13.1 Required use

Asset Shepherd must use the Strands Agents SDK as the actual orchestration layer, not merely import it for eligibility theater.

The MVP should use one primary agent. Do not create a swarm or a collection of specialist agents unless a measured limitation of the single-agent design justifies it and the user approves the added complexity.

### 13.2 Agent components

The Strands design follows the model-tools-prompt structure:

- **Model:** configurable provider, with Amazon Bedrock preferred for the hackathon deployment.
- **Tools:** narrow typed wrappers around the deterministic asset core.
- **Prompt:** a versioned system prompt enforcing inspection, evidence, policy, approval, verification, and bounded retries.

### 13.3 Required agent capabilities

- Invoke inspection tools.
- Choose sensing tools and consume structured observations and renders.
- Produce evidence-cited target-dependent assessments.
- Choose supported repair tools and typed action parameters.
- Request human approval before consequential repair.
- Resume from the same interrupted job.
- Invoke repair, re-observation, verification, and packaging tools.
- Iterate through further sensing or a fresh proposed action when needed.
- Interpret invariant verification results without overriding them.
- Return a structured final result and user-facing explanation.
- Remain available through download for questions answerable from recorded job evidence.

### 13.4 Human-in-the-loop

Use Strands interrupts for approval. The interrupt reason must be JSON-serializable and contain the approval card data.

The user response must be explicitly associated with the interrupt ID. On resume:

- Approved actions may run.
- Rejected actions must be cancelled.
- The decision must be written to `decisions.json`.
- Side effects must be idempotent because interrupt hooks or tools may be re-entered during resume.

### 13.5 Agent safety

The agent cannot:

- Call arbitrary shell commands against uploaded content.
- Invoke an unsupported capability or submit an action that fails its typed schema and deterministic
  constraints.
- Modify paths outside the job workspace.
- Apply an approval-required action without a valid approval record.
- Claim verification success when the tool returned failure.
- continue after configured cost, time, repeated-failure, or user-decision limits.

### 13.6 Observability

Capture and expose at least:

- Invocation duration.
- Token usage when available.
- Tool call count, success, errors, and duration.
- Interrupt count.
- Final verification state.
- Model/provider identifier.

Use Strands `AgentResult` metrics and OpenTelemetry or AWS-native tracing where practical. The final demo should show a clean trace or metrics view, not a secret-laden raw log dump.

### 13.7 Model configuration

Do not hard-code an obsolete model ID from an old tutorial.

Model provider, model ID, AWS profile, and region must be explicit configuration. Local unit tests must not require a live model. Live integration tests must be opt-in and skip cleanly when credentials are absent.

### 13.8 Conversation and authorization boundary

The conversation may ask bounded follow-up questions, propose typed intent and policy state, choose
sensing and action tools, explain structured results, and cite assessment IDs, measured values,
standardized renders, and frozen rules. Appearance statements require recorded visual evidence
available to a vision-capable workflow model or explicit human adjudication; metadata alone supports
only metadata claims. Otherwise the property must be marked not evaluated.

Typing approval language in chat never authorizes a repair. The human grants or rejects
consequential authorization through the structured interrupt control. The deterministic core
validates that event against the exact registered action ID and hash and enforces it. The agent has
neither authorization role.

---

## 14. AWS and Bedrock contract

The Builder Center Strands walkthrough is useful for its operational lessons, but current official Strands and AWS documentation is the source of truth. The older article's exact model IDs and package versions may be stale.

### 14.1 Useful operational lessons incorporated here

- Use a dedicated AWS CLI profile for isolation.
- Verify identity with STS before debugging the agent.
- Explicitly configure region and model access.
- Confirm the selected model is available in that region.
- Ensure the runtime identity has the Bedrock permissions actually used by Strands, including model invocation and streaming conversation operations.
- Add useful logging before blaming the framework, the model, the region, the moon, or all four.

A GitHub access token is not a prerequisite for Asset Shepherd's Strands runtime. Do not create one unless a future product feature genuinely needs GitHub access.

### 14.2 Local AWS setup

When the AWS milestone begins, Codex must provide exact user-run commands for:

- Installing or confirming AWS CLI.
- Configuring a dedicated profile, preferably `asset-shepherd`.
- Verifying caller identity.
- Selecting a region with an available tool-capable Bedrock model.
- Confirming model access.

Credentials and secrets must never be committed.

### 14.3 Cost controls

Before invoking paid services:

- Create an AWS budget or billing alert.
- Set conservative job size and timeout limits.
- Record approximate cost per complete run.
- Avoid persistent resources until needed.
- Add cleanup or expiration for uploaded and generated artifacts.

Codex must stop and request approval before creating architecture expected to cost more than $10 total during development or more than $2 per day while idle.

### 14.4 AgentCore deployment

Amazon Bedrock AgentCore is preferred only after the local agent works.

AgentCore deployment is accepted when:

- The same tool contract runs remotely.
- Asset files are isolated by job.
- Interrupted jobs can be resumed or a documented, reliable approval handoff exists.
- Logs and traces are visible.
- Credentials are supplied through AWS mechanisms, not files in the repository.
- A fresh remote run returns the same contracted output artifacts.

If AgentCore threatens the submission deadline, Codex may propose a fallback deployment. It may not silently replace the architecture. The working product and video take priority over a prestigious service logo attached to a broken endpoint.

---

## 15. Security, privacy, and reliability

### 15.1 File handling

- Treat every upload as untrusted binary data.
- Validate extension, magic bytes, size, and parse results.
- Use per-job directories with generated IDs.
- Prevent path traversal.
- Never use user-supplied names as unrestricted paths.
- Do not execute scripts, extensions, URIs, or commands embedded in assets.
- Delete hosted uploads and outputs after a documented retention period.

### 15.2 Secrets

- No AWS keys, model keys, Devpost credentials, or personal data in Git.
- Provide `.env.example` without secrets.
- Redact credentials from logs and screenshots.
- Do not publish the AWS Builder ID screenshot or personal email in project media.

### 15.3 Failure behavior

- Fail closed on parse or verification errors.
- Preserve the original.
- Return useful diagnostics.
- Do not leave a job forever in `RUNNING`.
- Use bounded timeouts.
- Support retry of idempotent stages.

### 15.4 Determinism

Fixture generation, sensor measurements, action-preview calculation, repair application, and
invariant verification must be deterministic for the same source and typed tool calls.

The agent's assessment and chosen action may vary with evidence, target, and model reasoning. Once it
submits a typed action request, the exact preview, approval binding, matrix, mutation, and invariant
result must not depend on creative prose.

### 15.5 Hosted conversation data

Hosted provenance must record structured state transitions rather than the raw transcript. Include
confirmed structured intent and supported goal, profile and prompt versions and hashes, deterministic
tool-call inputs and output hashes, the registered action and decision event, verification and
package references, timestamps, and external-handoff status.

Do not package chain-of-thought, hidden prompts, routine agent prose, or the complete raw
conversation. For hosted jobs, package structured intent plus a canonical hash; retain raw
description text only in private short-lived job state or by explicit user choice. Existing M8
form-led artifacts remain the reference until the versioned hosted schema migration is implemented
and accepted.

---

## 16. Repository and autonomous execution protocol

### 16.1 Direct-main workflow

- Work directly on `main`.
- Do not create branches.
- Do not create pull requests.
- Pull only with `git pull --ff-only` when needed.
- Make small coherent commits after passing the relevant gate.
- Never force-push.
- Never use `git reset --hard` or destructive cleanup against unknown work.
- Preserve user changes and investigate mixed worktrees before editing.

### 16.2 Required project-control files

Codex must maintain:

```text
docs/PROJECT_CONTRACT.md   # this document; stable
docs/PROJECT_STATUS.md     # living milestone status
docs/DECISIONS.md          # meaningful autonomous decisions and user approvals
AGENTS.md                   # concise instructions to read the above files
```

### 16.3 Start-of-work procedure

At the start of every substantial Codex task:

1. Read `AGENTS.md`.
2. Read this contract.
3. Read `docs/AGENT_ORCHESTRATED_WORKFLOW.md`.
4. Read `docs/PROJECT_STATUS.md`.
5. Inspect Git status and recent commits.
6. Identify the earliest incomplete, unblocked milestone.
7. State internally what gate will prove the work complete.
8. Implement only work serving that milestone or a documented blocker.

### 16.4 End-of-work procedure

Before every milestone commit:

1. Run the common quality gate.
2. Run milestone-specific tests.
3. Inspect diffs for scope creep, secrets, and generated junk.
4. Update `PROJECT_STATUS.md` with evidence.
5. Add any material decision to `DECISIONS.md`.
6. Commit directly to `main`.
7. Push `main` when remote access is available.

### 16.5 Common quality gate

At minimum:

```text
uv lock --check
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

Codex may add faster targeted checks during iteration, but the full gate runs before a milestone commit.

### 16.6 Autonomous decision authority

Codex may decide without asking:

- Internal module layout.
- Routine library APIs after the capability spike.
- Test organization.
- Minor naming and formatting.
- Error types and log structure.
- Small UI layout details.
- Implementation details that do not alter product behavior.
- How to fix ordinary test, lint, or type failures.

Codex must log material decisions in `DECISIONS.md` when choosing among credible architectural alternatives.

### 16.7 Mandatory escalation

Stop and request user input when:

- A proposed change expands or contracts MVP scope.
- A repair could destroy or materially alter artistic content beyond this contract.
- A required behavior conflicts with glTF semantics.
- A third-party asset, dataset, or codebase has unclear licensing.
- AWS cost may exceed the thresholds above.
- Credentials, account permissions, or public-site actions require the user.
- A milestone gate remains unsatisfied after three focused approaches.
- The only apparent solution requires Blender in the hosted runtime.
- A security or privacy risk cannot be mitigated within the design.
- Public repository visibility, deployment, video publication, or final submission is required.

Do not escalate ordinary questions that can be answered by reading code, tests, or current official documentation.

### 16.8 Mandatory periodic check-ins

Codex must stop and provide a concise check-in after:

1. The deterministic CLI completes the full inspect → plan → approve → repair → verify → package workflow.
2. The Strands agent completes the same workflow with a real interrupt and resume.
3. The AWS-hosted workflow completes successfully.
4. The release candidate and submission package are ready, before anything is submitted.

The user may bring these reports to ChatGPT for review. Between checkpoints, Codex should continue according to this contract rather than asking for ritual approval after every file.

### 16.9 Check-in format

```text
Milestone:
Commit:
Gate result:
Working demo command or URL:
Artifacts produced:
Measured results:
Material decisions made:
Known limitations:
Decision required from user, if any:
Next milestone:
```

Avoid enormous command transcripts unless a failure requires them.

---

## 17. Milestone plan

Dates are targets, not excuses to skip gates. Codex should update actual completion dates in `PROJECT_STATUS.md`.

M0-M8 describe completed historical implementation gates. Their deterministic inspector/planner
requirements remain regression evidence for the repair-engine harness but do not override D036's
agent-orchestrated product authority. M9 must perform the migration and pass the D036 acceptance gate
before deployment or public product claims.

### M0 — Repository bootstrap

**Status:** Complete at baseline commit.

**Gate:** Python package, Strands import, tests, Ruff, formatting, Pyright, lockfile.

---

### M1 — Install controlling project documents

**Target:** August 21

**Work:**

- Commit this contract as `docs/PROJECT_CONTRACT.md`.
- Create `docs/PROJECT_STATUS.md` from the template in Appendix B.
- Create `docs/DECISIONS.md`.
- Create root `AGENTS.md` from Appendix A.
- Link design documents from README.

**Gate:**

- Common quality gate passes.
- Control files exist and agree that work occurs on `main`.
- Status identifies M2 as next.

**Commit:** `docs: add project contract and execution protocol`

---

### M2 — GLB capability spike and architecture decision

**Target:** August 22

**Goal:** Prove the selected lightweight stack can support the MVP before building abstractions around wishful thinking.

**Work:**

- Evaluate candidate libraries.
- Create or obtain a tiny synthetic GLB.
- Load it.
- Traverse scene nodes and compute world bounds.
- Rename a node.
- Add or modify a root normalization transform.
- Save a new GLB.
- Reload it.
- Verify geometry counts and transformed bounds.
- Run a glTF validation mechanism.
- Record an ADR with chosen libraries and rejected alternatives.

**Gate:**

- A checked-in automated spike test proves round-trip behavior.
- Unknown or unsupported data-loss risks are documented.
- Selected dependencies are compatible with Python 3.12, Linux, likely ARM64, and the MIT project.
- No Blender runtime dependency.

**Checkpoint:** No mandatory user checkpoint unless the spike fails or requires a scope decision.

---

### M3 — Typed schemas and fixture generator

**Target:** August 23–24

**Work:**

- Implement versioned typed models for profile, inspection, findings, candidate repairs, repair plan, decisions, verification, provenance, and job result.
- Export JSON schemas.
- Implement deterministic clean and broken robot fixture generation.
- Create expected-defects manifests.
- Add fixture profile.

**Gate:**

- Fixtures regenerate from a clean checkout.
- Generated JSON validates.
- Clean and broken GLBs load and pass basic structural validation.
- Automated tests prove expected dimensions and defect setup.

---

### M4 — Deterministic inspector

**Target:** August 25–27

**Work:**

- Implement inspection domains from Section 7.
- Emit findings with evidence.
- Implement repair eligibility.
- Add `inspect` CLI.
- Produce `inspection.json` and a basic human-readable report.

**Gate:**

- Inspector identifies every encoded broken-fixture defect required by the manifest.
- Clean fixture produces no false `ERROR`, `BLOCKER`, or `AUTO_SAFE` action.
- Repeated inspection is deterministic.
- No LLM or network is required.

---

### M5 — Candidate planning and repair engine

**Target:** August 28–30

**Work:**

- Deterministically generate rename candidates.
- Deterministically generate normalization-transform candidate.
- Validate approvals.
- Apply safe names.
- Apply approved root normalization transform.
- Preserve source and resource counts.
- Emit `repair_plan.json` and `decisions.json`.

**Gate:**

- Approved broken fixture becomes correctly sized, upright, and grounded within tolerance.
- Rejected normalization remains unapplied.
- Names become valid and unique.
- Source hash is unchanged.
- Geometry/material/texture counts are preserved.
- Repair is semantically idempotent.

---

### M6 — Verification, packaging, and deterministic CLI MVP

**Target:** August 31

**Work:**

- Implement independent output verification.
- Implement provenance.
- Implement result ZIP.
- Implement complete `run` CLI with approval file or interactive approval.
- Add failure-path tests.
- Add demo command.

**Gate:**

One command performs:

```text
broken.glb
→ inspection
→ plan
→ approval
→ repair
→ verification
→ result ZIP
```

And:

- Every contracted artifact exists.
- Verification passes.
- Second run proposes no additional v1 repair.
- Source remains untouched.
- Common quality gate passes.
- README contains a working local demo command.

**Mandatory checkpoint 1:** Stop and report before adding the agent layer.

---

### M7 — Local Strands agent

**Target:** September 1–3

**Work:**

- Implement narrow typed Strands tools over the deterministic core.
- Create versioned system prompt.
- Configure model provider through environment.
- Implement structured plan selection.
- Implement approval interrupt and resume.
- Implement one bounded correction attempt after failure.
- Capture metrics.
- Add fake-model or mocked tests without network.
- Add an opt-in live integration test.

**Gate:**

- A live Strands run inspects the broken fixture.
- The agent presents one coherent approval interrupt.
- Reject path works.
- Approve path resumes and completes.
- The exact deterministic output package is produced.
- No approval-required tool can run without an approval record.
- Unit tests require no credentials.

**Mandatory checkpoint 2:** Stop and report before web/AWS work.

---

### M8 — Coherent local web product

**Target:** September 4–6

**Work:**

- Build resolved-policy review and bounded advanced adjustment.
- Add GLB upload.
- Show stages and structured findings.
- Render before/after GLB previews.
- Display approval card.
- Resume interrupted agent.
- Show verification and download link.
- Handle invalid and unsupported files coherently.

**Gate:**

- A person can complete the full workflow without terminal access.
- The page never reveals credentials or private reasoning.
- Browser refresh or resume behavior is documented.
- The demo fixture works twice from a clean application start.

---

### M9 — Hosted Bedrock conversation, durability, and preferred AgentCore deployment

**Target:** September 6–9

**Work:**

- Replace the deterministic semantic planner with the D036 agent-led sensing, assessment,
  disposition, and action-preview loop while retaining deterministic enforcement.
- Make standardized rendered views available as recorded sensor evidence to a vision-capable
  workflow model.
- Recast the scripted provider as a test double only and require representative live-model behavior
  evaluation before product acceptance.
- Add the D019 conversation-led workspace over the existing typed intent, profile, finding, plan,
  decision, verification, and package schemas.
- Implement objective preflight before target confirmation, a visible Job Contract, and frozen
  policy-family resolution for ordinary users.
- Persist source identity, structured state, deterministic tool results, the exact pending
  interrupt, decisions, idempotency keys, output references, bounded conversation state, retention,
  and deletion status.
- Prove browser, application, and agent-runtime restart resume without duplicate mutation or
  packaging.
- Configure dedicated AWS development profile with user assistance.
- Verify identity, region, Bedrock model access, and permissions.
- Set budget alert.
- Run local agent through Bedrock.
- Deploy agent/backend to AgentCore if stable.
- Configure object storage and job isolation if required.
- Configure logs, traces, retention, and cleanup.
- Deploy or host frontend through the simplest stable route.

**Gate:**

- The D036 acceptance gate in `docs/AGENT_ORCHESTRATED_WORKFLOW.md` passes, including the
  long-bodied quadruped, ambiguous-orientation, action-provenance, and second-repair cases.
- One live Bedrock conversation completes bounded intake → preflight → target confirmation →
  agent-chosen sensing → assessment → action preview → approve or reject → repair → reassess → verify
  → package → evidence follow-up.
- Deterministic measurements and results are reproducible for the same typed calls; the workflow is
  not required to reproduce the obsolete M8 heuristic plan.
- A pending approval survives browser and runtime restart, and duplicate resume or callback attempts
  do not duplicate mutation or packaging.
- Every conversational factual statement in the acceptance trace maps to recorded evidence.
- Chat text cannot authorize an action, and hosted provenance contains structured conversation
  events without a raw transcript.
- A logged-out or documented test user can access the product.
- Remote upload, interrupt, resume, repair, verify, and download all work.
- Traces and metrics are visible.
- Idle cost is within threshold.
- Cleanup and retention are documented.
- The existing offline form-led acceptance suite remains passing.

**Mandatory checkpoint 3:** Stop and report before public release work.

---

### M10 — Evaluation and product hardening

**Target:** September 9–10

**Work:**

- Generate at least eight controlled fixture variants.
- Measure defect detection, false positives, repair success, idempotence, runtime, model usage, and approximate cost.
- Test invalid files and unsupported features.
- Time one manual-versus-assisted workflow honestly.
- Fix the highest-impact failures.

**Gate:**

- Reproducible evaluation command.
- Results table committed.
- Public claims trace to actual measurements.
- No silent asset corruption in the test corpus.

---

### M11 — Documentation, architecture, and Builder posts

**Target:** September 10–12

**Work:**

- Complete README and clean setup instructions.
- Add architecture diagram.
- Add security/privacy and testing notes.
- Add pre-existing-work disclosure.
- Add licenses and attribution for dependencies/assets.
- Draft and publish up to three `builder.aws.com` posts whose titles include **Agents for Humans**;
  do not treat a literal hashtag as required unless a later official-rules recheck restores it.
- Prepare Devpost text and testing instructions.

**Gate:**

- Clean clone instructions pass.
- Public repo contains required license and source.
- Architecture diagram clearly shows user, Strands loop, tools, AWS services, and output.
- No private information appears.

---

### M12 — Video, release candidate, and submission

**Target:** September 12–13

**Work:**

- Create release candidate.
- Run two clean end-to-end tests.
- Record a video under five minutes.
- Cover problem, audience, why it matters, live workflow, evidence, and architecture.
- Publish video publicly.
- Make repository public when user approves.
- Verify MIT license is visible in repository About area.
- Verify live demo and all links from a logged-out browser.
- Complete Devpost draft.

**Gate:**

- Submission checklist matches current official rules.
- Public video works.
- Public repository works.
- Testing access works.
- Release commit is recorded.
- No secrets or personal email screenshots are exposed.

**Mandatory checkpoint 4:** Stop for user review before final Devpost submission.

The user performs the final submission action.

---

## 18. Evaluation metrics

The evaluation system should report:

- Required defect recall on controlled fixtures.
- False severe finding count on clean fixtures.
- Automatic name-repair success.
- Normalization-transform success.
- Verification pass rate.
- Idempotence pass rate.
- Asset parse/validation pass rate.
- Median deterministic runtime.
- Median agent runtime.
- Model token usage and estimated cost.
- Number of user decisions per job.
- Manual versus assisted elapsed time on the demo workflow.

Do not claim broad production accuracy from eight synthetic fixtures. Describe the evaluation honestly as controlled MVP validation.

---

## 19. Demo contract

The final video target is approximately four minutes, leaving margin under the five-minute maximum.

Suggested flow:

```text
0:00–0:25  Show the broken robot and explain the import problem.
0:25–0:50  Identify indie developers and technical artists as users.
0:50–1:30  Upload asset and project profile.
1:30–2:10  Show agent-chosen sensing and an evidence-cited assessment.
2:10–2:40  Approve one exact agent-proposed action.
2:40–3:15  Show repair, agent reassessment, invariant verification, and before/after evidence.
3:15–3:40  Download the package and show measurable results.
3:40–4:05  Show Strands/AWS architecture and observability.
4:05–4:15  Close with the product promise.
```

The video must demonstrate a real run or a prevalidated run through the actual product. It must not depend on an unrehearsed model deciding to explore a philosophical tangent while the recording clock advances.

---

## 20. Submission deliverables

Before submission, ensure all of these exist:

- Public repository.
- MIT license visible in repository About section.
- Complete source and fixtures.
- README.
- Architecture diagram.
- Public video under five minutes.
- Text description.
- Problem, audience, and importance clearly stated.
- AWS Builder ID entered as required.
- Live demo or free testing access.
- Testing instructions.
- Pre-existing-work disclosure.
- Dependency and asset attribution.
- Optional Builder Center post links.
- Release commit SHA.
- Confirmation that deployment remains available through the judging period.

---

## 21. Hard non-goals before submission

Do not add before the hackathon deadline:

- FBX support.
- OBJ support.
- Loose glTF package support.
- Skeletal repair or retargeting.
- Animation editing.
- Morph-target editing.
- Mesh reconstruction or decimation beyond the bounded, use-case-driven simplification in 9.3.
- UV generation.
- Collision generation.
- LOD generation.
- Material merging.
- Texture modification.
- Unreal Editor plugin.
- Marketplace integration.
- Team administration.
- General-purpose technical-art chat.
- Multi-agent swarm.

After the core product passes all gates, a feature may be added only if it materially improves judging and does not threaten release stability. Record the decision first.

---

## 22. Risk register

### Risk: GLB round-trip corrupts content

**Mitigation:** Capability spike, count invariants, independent reload, glTF validation, clean and broken fixtures, preserve resource counts.

### Risk: Orientation inference is wrong

**Mitigation:** Orientation is a target-dependent agent conclusion, never a dominant-extent rule.
The agent may request additional measurements, standardized renders, or user clarification. Rotation
requires an agent-requested typed preview and consequential approval.

### Risk: Agent is ornamental

**Mitigation:** A live model must choose sensors, form evidence-cited assessments, choose disposition,
and design supported action requests. The scripted provider is only a test double and cannot satisfy
the agent-orchestrated acceptance gate.

### Risk: Agent hallucinates repairs

**Mitigation:** Capability registry, typed action schemas, deterministic dry-run consequences,
approval hashes, mutation-scope enforcement, and independent verification. No transform is accepted
from prose or applied without an explicit agent tool call.

### Risk: AWS region or model access blocks progress

**Mitigation:** Explicit profile/region/model, STS identity check, access check, local non-AWS model option for development, AgentCore only after local completion.

### Risk: AgentCore consumes schedule

**Mitigation:** Deployment milestone has fallback; working product and video outrank service choice.

### Risk: UI consumes schedule

**Mitigation:** Build after CLI and agent; choose lightweight framework; only eight required states.

### Risk: Scope expands into full technical-art suite

**Mitigation:** Hard non-goals and one approved repair class.

### Risk: Demo asset is visually weak

**Mitigation:** Improve fixture materials or add an original/CC0 demo asset after deterministic tests are stable.

### Risk: Costs exceed credits

**Mitigation:** budget alert, low-cost model during development, opt-in live tests, artifact expiration, cost thresholds.

### Risk: Public release exposes personal data

**Mitigation:** secret scans, logged-out testing, screenshot review, no Builder ID screenshot, no private email in media.

---

## Appendix A — Required root `AGENTS.md`

```markdown
# Asset Shepherd Agent Instructions

Before doing substantial work, read:

1. `docs/PROJECT_CONTRACT.md`
2. `docs/AGENT_ORCHESTRATED_WORKFLOW.md`
3. `docs/PROJECT_STATUS.md`
4. `docs/DECISIONS.md`
5. `docs/REAL_WORLD_VALIDATION_PLAN.md`

`docs/PROJECT_CONTRACT.md` is the controlling product and execution specification.
`docs/AGENT_ORCHESTRATED_WORKFLOW.md` controls the model/tool authority boundary and product path.
The real-world validation plan controls corpus, Tripo, Blender, Unreal, evaluation, and demo work.

Work directly on `main`. Do not create branches or pull requests. Do not force-push or use destructive Git cleanup. Preserve unrelated user changes.

Work on the earliest incomplete, unblocked milestone. Evaluate completion against its explicit gate. Run the common quality gate before milestone commits. Update `PROJECT_STATUS.md` with evidence and `DECISIONS.md` for material choices.

Continue autonomously between mandatory checkpoints. Escalate only for the conditions listed in the contract. Never commit credentials or expand scope silently.
```

---

## Appendix B — Initial `docs/PROJECT_STATUS.md`

```markdown
# Asset Shepherd Project Status

**Last updated:** YYYY-MM-DD
**Current commit:** <sha>
**Current milestone:** M1
**Overall state:** IN_PROGRESS

## Milestones

| Milestone | State | Evidence | Commit | Notes |
|---|---|---|---|---|
| M0 Repository bootstrap | COMPLETE | pytest, Ruff, format, Pyright, lock check | 112b649d52009ffa544f7787fb4c0d59efc39272 | Baseline |
| M1 Project control docs | IN_PROGRESS |  |  |  |
| M2 GLB capability spike | NOT_STARTED |  |  |  |
| M3 Schemas and fixtures | NOT_STARTED |  |  |  |
| M4 Inspector | NOT_STARTED |  |  |  |
| M5 Repair engine | NOT_STARTED |  |  |  |
| M6 Deterministic CLI MVP | NOT_STARTED |  |  | Mandatory checkpoint after completion |
| M7 Strands agent | NOT_STARTED |  |  | Mandatory checkpoint after completion |
| M8 Web product | NOT_STARTED |  |  |  |
| M9 AWS deployment | NOT_STARTED |  |  | Mandatory checkpoint after completion |
| M10 Evaluation | NOT_STARTED |  |  |  |
| M11 Docs and Builder posts | NOT_STARTED |  |  |  |
| M12 Release and submission | NOT_STARTED |  |  | Mandatory checkpoint before submission |

## Current gate

Describe the exact conditions being pursued.

## Latest evidence

- Tests:
- Lint:
- Type checking:
- Demo command or URL:
- Generated artifacts:

## Blockers

None.

## Next action

Complete M1 according to `docs/PROJECT_CONTRACT.md`.
```

---

## Appendix C — Initial `docs/DECISIONS.md`

```markdown
# Asset Shepherd Decision Log

Record decisions that materially affect architecture, product behavior, cost, security, or scope.

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
```

---

## Appendix D — Codex bootstrap prompt

Use this once to install the contract into the repository:

```text
Work directly on main in the Asset Shepherd repository. Do not create a branch or pull request.

The attached ASSET_SHEPHERD_PROJECT_CONTRACT.md is the approved controlling project contract.

1. Save it as docs/PROJECT_CONTRACT.md without changing its technical meaning.
2. Create root AGENTS.md exactly from Appendix A.
3. Create docs/PROJECT_STATUS.md from Appendix B, replacing the date and current commit where appropriate.
4. Create docs/DECISIONS.md from Appendix C.
5. Add a concise “Project control” section to README.md linking those three documents.
6. Run the full common quality gate defined in the contract.
7. Update PROJECT_STATUS.md with the M1 evidence and mark M1 complete only if its gate passes.
8. Commit directly to main with message: docs: add project contract and execution protocol
9. Push main.
10. Then continue autonomously with M2. Stop only if an escalation condition occurs or when a mandatory checkpoint is reached.

At the next report, use the contract's mandatory check-in format. Do not paste enormous command transcripts unless a failure requires them.
```

---

## Appendix E — Source note

This contract was prepared using the official Agents for Humans Devpost rules and FAQ, current Strands Python quickstart and interrupt documentation, current AWS guidance, and the Builder Center article “Getting Started with Strands Agents: A Step-by-Step Guide.” Codex must prefer current official documentation over old tutorial version numbers or model IDs and must recheck the official hackathon rules before submission.
