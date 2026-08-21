# Asset Shepherd Decision Log

Record decisions that materially affect architecture, product behavior, cost, security, or scope.

## Decisions

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
