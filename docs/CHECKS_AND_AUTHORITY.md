# Asset Shepherd checks and authority

The concise worker-facing overview is [`WHAT_IT_DOES.md`](WHAT_IT_DOES.md).

Asset Shepherd separates **what the asset should become** from **what must always remain safe**.
The workflow agent chooses sensing, interprets target-dependent evidence, and chooses supported
actions. Deterministic tools measure, render, calculate exact action consequences, enforce
invariants, mutate only after a valid agent call and applicable approval, and verify the result.

## Authority classes

Every observation, assessment, and verification check has one of five typed bases. The present schema
must be migrated to add `AGENT_ASSESSMENT`; until then, existing policy findings are legacy output,
not the target authority model.

| Basis | Who or what supplies it | Can user intent change it? |
| --- | --- | --- |
| `FROZEN_PROJECT_POLICY` | The confirmed target plus a versioned policy family | Only before upload, by creating a new job |
| `AGENT_ASSESSMENT` | The workflow agent, citing confirmed target plus recorded sensor evidence | The user may correct intent; new evidence may revise it |
| `UNIVERSAL_INVARIANT` | Deterministic safety and preservation code | No |
| `OBJECTIVE_SOURCE_DIAGNOSTIC` | A measurement of the uploaded bytes | No; it may be informative rather than blocking |
| `EXTERNAL_CONSUMER_EVIDENCE` | Khronos, Blender, Unreal, or another independent consumer | No; evidence informs verification and human review |

### Where the workflow model participates

The semantic-intake provider currently receives only the user's description and proposes supported
use and plausible scale. That is an interim implementation, not the completed agent product.

The workflow model must receive the confirmed target, durable structured state, available tool
capabilities, measurements, and requested standardized renders. It then:

- chooses additional sensors;
- determines which observations matter to the target;
- creates and revises target-dependent assessments;
- chooses whether to accept, inspect, ask, report, repair, or stop; and
- chooses supported action tools and typed parameters.

`target_intake.json` records, per field, whether the value came from `MODEL_INFERENCE`,
`EXPLICIT_USER_TEXT`, or `USER_CLARIFICATION`, with confidence and concise evidence. Values below
the 0.8 confidence gate remain missing and cause a question. The user must confirm or adjust the
proposal once. Only then does the resolver freeze the job policy.

The resulting policy records the source of each active parameter:

- `CONFIRMED_INTENT`: the user-confirmed target, even when the initial proposal came from the LLM;
- `DERIVED_INTENT`: a deterministic value derived from confirmed intent, such as bounded
  tolerances or explicit standing/hanging language;
- `FAMILY_DEFAULT`: a versioned project convention not supplied by the model;
- `USER_OVERRIDE`: an advanced supported value explicitly changed by the user.

Assessments cite exact target values, policy sources, and sensor evidence. A malformed index remains
a universal blocker even if the user or model says the asset is acceptable.

## Inspection checks

| Area | Checks | Basis | Implementation |
| --- | --- | --- | --- |
| Target dimensions | Axis-aligned bounds and exact extents are observations; the agent determines which dimension should match which target concept | Objective diagnostic plus agent assessment | NumPy world-space bounds, target, and any needed renders |
| Orientation | Transforms, bounds, ground relationship, and coordinate-labeled views are observations; the agent decides whether upright pose or front/yaw is wrong | Objective diagnostic plus agent assessment | Deterministic traversal and four standardized renders; glTF +Y is up and +Z is forward; never dominant extent alone |
| Grounding | Minimum Y and support-plane relationship are observations; the agent decides whether the intended object should be grounded | Objective diagnostic plus agent assessment | Deterministic bounds plus target context and renders when needed |
| Naming | Presence, duplicates, and pattern results are observations; the agent chooses disposition and replacement | Frozen policy plus agent assessment | Versioned regex and index-stable name scan |
| Budgets | Counts and limits are observations; the agent explains their importance and normally reports them | Frozen policy plus agent assessment | Accessor/resource counts and Pillow image metadata |
| Container and structure | GLB 2.0 header, scenes, references, supported repair domain | Universal invariant | `pygltflib` load plus local structural validation |
| Geometry validity | Attribute cardinality; finite positions, normals, tangents, and UVs; unit normals; tangent handedness; index range | Universal invariant | Direct accessor decoding with NumPy; violations block repair |
| Topology diagnostics | Repeated-index and scale-aware zero-area triangles; boundary, non-manifold, and inconsistently wound edges; index-topology components; unused and coincident positions | Objective diagnostic, report-only | Direct index, triangle, edge, and position analysis |
| Performance diagnostics | Vertex reuse and estimated FIFO-16 vertex-cache locality | Objective diagnostic, report-only | Deterministic index-stream simulation; target-engine profiling remains authoritative |
| Attribute coverage | Presence of normals, tangents, and primary UVs per primitive | Objective diagnostic | Direct accessor inventory; absence alone is not universally invalid |
| Hierarchy and resources | Empty leaves, unreachable nodes, unused resources, apparent duplicate materials/textures | Objective diagnostic | Active-scene reachability and canonical resource comparison |
| Transform diagnostics | Root origins, ground-center reference, negative determinant, non-uniform scale | Objective diagnostic | Explicit world-matrix traversal |
| Images/materials | Readability, declared alpha mode/cutoff, double-sided state, base color, metallic, roughness, emissive factors | Objective diagnostic | Pillow plus glTF material metadata; not a visual claim |
| Unsupported semantics | Skins, animations, morph targets, unsupported required extensions | Universal invariant | Structural feature inventory; inspection continues but repair blocks |

Asset Shepherd does not infer that missing tangents, one material, UVs outside 0–1, or a large
triangle count are universally wrong. Those can be valid artistic or engine choices. Version 1
does not repair topology, normals, UVs, materials, textures, transparency, or emissive behavior.

## Repair and verification checks

The agent chooses typed sensor tools, forms the assessment, and chooses supported action-preview tools
and their typed parameters. Deterministic code calculates the exact matrix or edit, validates the
capability boundary, and enforces authorization. Users never manipulate raw matrices in the UI.
Deterministic code must not add a scale, rotation, translation, grounding, or rename that the agent
did not request.

Universal verification asserts:

- source and output hashes match the plan, outcome, and provenance;
- the output reloads as GLB 2.0;
- accessors, buffer views, buffers, materials, textures, images, samplers, animations, skins,
  cameras, mesh primitives, original node references, extension metadata, and the complete binary
  payload are semantically unchanged;
- only the approved normalization root may change node count or scene roots;
- vertex, triangle, material, and texture counts remain stable;
- Trimesh independently reloads the output and agrees on world bounds;
- executed and rejected actions exactly match decisions and provenance;
- when the official Khronos validator is configured, repair introduces no new validator errors.

Action verification checks the exact declared postconditions of every approved action and proves
that no unrequested mutation occurred. Rejection requires the corresponding action to remain
unapplied and its record to be preserved. The agent then reassesses target satisfaction using fresh
sensor evidence. An empty second deterministic plan is not a semantic verification condition.

The official Khronos result is layered deliberately. Zero output errors is objective conformance.
If the untouched source already contains an official error in data outside the authorized repair,
the error remains an explicit warning; any new error or validator execution failure makes
verification fail. Asset Shepherd does not claim that it repaired source metadata it did not touch.

## Independent consumer evidence

- `asset-shepherd validate` runs the official Khronos glTF Validator and retains its full JSON
  report plus typed counts and codes.
- `validation/blender/inspect_glb.py` imports in Blender, inventories scene/resources, and can
  re-export a control GLB.
- `validation/blender/render_turntable.py` produces equally framed, coordinate-labeled views. The
  render contract maps front/right/back/left to source glTF +Z/-X/-Z/+X camera positions so the
  agent can perform a semantic yaw check without guessing from extents.
- `asset_shepherd.validation.visual_compare` verifies paired render sets and reports per-view MAE,
  RMSE, maximum channel delta, alpha MAE, and changed-pixel fraction. These metrics are external
  evidence, not an automated semantic judgment that appearance is correct.
- `validation/unreal/import_compare.py` imports isolated raw, Shepherd, and reference arms and
  records Unreal-owned metrics and warnings.

A vision-capable workflow model may use recorded standardized views for evidence-cited semantic
assessment. Appearance, transparency, emissive behavior, normals, material coverage, and texture
fidelity still require human adjudication when model and mechanical evidence are inconclusive.

## Local commands

All examples are single-line PowerShell commands.

Install the pinned official Windows validator for the current user:

```powershell
.\scripts\Install-KhronosValidator.ps1
```

Validate one GLB and write the full report:

```powershell
uv run asset-shepherd validate fixtures/clean_robot.glb --output build/validation/clean_robot.khronos.json
```

Compare two identically named Blender render directories:

```powershell
uv run python -m asset_shepherd.validation.visual_compare --reference validation/corpus/shader_lantern_01/observed_real_world/screenshots/raw --candidate validation/corpus/shader_lantern_01/observed_real_world/screenshots/shepherd --maximum-mae 0.1 --output build/validation/lantern-render-comparison.json
```

The Khronos executable is optional for the portable Python runtime. Once installed, the script
saves `ASSET_SHEPHERD_GLTF_VALIDATOR` as a current-user path; new Asset Shepherd processes then add
the official before/after comparison automatically.
