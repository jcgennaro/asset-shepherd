# Asset Shepherd

Asset Shepherd is an autonomous 3D-asset intake, inspection, repair-planning, and
verification agent for game developers.

> [!NOTE]
> This repository is an early hackathon work in progress.

## Project control

- [Project contract](docs/PROJECT_CONTRACT.md)
- [Agent-orchestrated workflow](docs/AGENT_ORCHESTRATED_WORKFLOW.md)
- [Agent operating contract](docs/AGENT_OPERATING_CONTRACT.md)
- [Real-world validation plan](docs/REAL_WORLD_VALIDATION_PLAN.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Decision log](docs/DECISIONS.md)
- [Web design and flow](docs/WEB_DESIGN_AND_FLOW.md)
- [Checks and authority](docs/CHECKS_AND_AUTHORITY.md)
- [Future component labeling and removal](docs/FUTURE_COMPONENT_HANDLING.md) — deferred, not MVP

The agent-orchestrated workflow defines the product authority boundary: deterministic tools provide
measurements, rendered evidence, bounded actions, enforcement, and proof; the workflow agent decides
what to inspect, what the evidence means, and which supported action to request. Model conclusions
cannot waive file validity, authorization, mutation scope, or invariant verification.

## Real-world validation

The [validation workspace](validation/README.md) preserves immutable raw provenance, controlled
mutation ground truth, Blender evidence, and an isolated Unreal comparison harness. Patchling
Courier is the current hero and preservation case. Shader Lantern is the second rights-confirmed
real-world corpus member. Its approved workflow normalized the 12.8 MB
[raw GLB](validation/corpus/shader_lantern_01/raw/asset.glb) to the intended 1.2-meter height, made
two safe display-name repairs, independently preserved its exported geometry and PBR resources in
Blender and Unreal, and left its triangle-budget warning unresolved. Exact evidence and limitations
are in the
[Shader Lantern checkpoint](validation/corpus/shader_lantern_01/checkpoint.md).
The rights-confirmed 4.86 MB
[Patchling raw GLB](validation/corpus/patchling_01/raw/asset.glb) is the repository's first
distributable real-world demo input. Generated GLBs and ZIPs remain reproducible and untracked.

## Local web product

```powershell
uv sync
```

Save the OpenAI key once. This is one command; the prompt hides the pasted value:

```powershell
.\scripts\Save-OpenAIKey.ps1
```

Start Asset Shepherd later with one command:

```powershell
.\scripts\Start-AssetShepherd.ps1
```

Open `http://127.0.0.1:8010`. The flow starts by asking the user to describe the model they are
already working on.
The interim OpenAI intake provider uses `gpt-5.6-luna` with `xhigh` reasoning to propose a supported
use and plausible semantic scale from ordinary language. Only the description is sent; the GLB
stays local. The user adjusts or confirms that typed proposal before rules or upload are available.
The frozen intake records provider/model provenance, and changing intent starts a new inspection.
Use `uv run asset-shepherd web --offline-intake` for the explicit-text, zero-network fallback.
The Windows launch scripts keep the encrypted development key under the current user's local app
data, outside the repository. The launcher exposes it only to the running server process and removes
it when that command ends.

The versioned D019 reference is at `http://127.0.0.1:8010/workspace`. It starts with a short asset
description plus the untouched GLB, performs profile-free objective preflight, uses the same
semantic proposal, and asks only for fields that remain genuinely ambiguous. A
persistent Job Contract shows measured source facts, the derived
frozen policy, current assessments and action state, exact decision, verification, and package state
beside the conversation. Ordinary users never choose a named scale preset. Advanced customization is limited
to fields already enforced by `ProjectProfile`; safety and repair boundaries remain fixed.

The persistent left pane shows the shared **Describe -> Agree -> Inspect -> Decide -> Download**
workflow. Intake presents **Rules -> Upload** one step at a time, and each job presents only its
current Inspect, Decide, or Download view. Intake currently calls OpenAI through a provider-neutral
boundary; the repair workflow still uses a zero-network scripted provider over the real Strands
loop. That repair path is a deterministic test harness, not the completed product agent. D036
requires a real workflow model to choose sensors, assess evidence, choose disposition, and initiate
typed supported actions. Deterministic tools remain authoritative for measurements, exact action
consequences, authorization enforcement, mutation scope, and invariant verification.

New conversational jobs use one immutable, versioned **Unreal Static Game Asset Policy Family**.
Asset Shepherd proposes the complete job policy from the already-confirmed target story, including
its height, bounded tolerances, and explicit standing/hanging/hovering intent; unspecified project
rules retain conservative family defaults. Users no longer select a named scale preset or re-enter
height. **Review all active rules** and **Why these rules?** keep the proposal inspectable, while
advanced adjustment remains limited to supported target-state and report-only budget fields.
Upload freezes the resolved policy, and provenance records its family and resolved identifiers,
explicit differences, per-rule sources, version, and canonical SHA-256. Historical repository
profiles remain immutable for CLI reproduction and existing evidence. Changing rules starts a new
inspection and job.

The M8 form routes preserve jobs only while the process runs. The D019 `/workspace` path persists
structured state and the native Strands interrupt so refresh, application restart, and agent-runtime
restart resume the exact job without duplicate mutation or packaging. Local private workspace state
has a seven-day retention marker; production cleanup remains part of the AWS gate. The 3D preview
uses the pinned official `<model-viewer>` browser component; GLB files remain served from the local
Asset Shepherd origin.

## Deterministic repair-engine harness

```powershell
uv sync
uv run asset-shepherd run fixtures/broken_robot.glb `
  --profile profiles/unreal_indie_robot.json `
  --approvals examples/approve_normalization.json `
  --output demo-output
```

The legacy command inspects, plans, applies policy-safe renames, consumes the explicit normalization
approval, repairs, independently verifies, and writes `demo-output/result.zip`. It does not invoke a
model or make a network request. It tests repair mechanics and artifacts; its heuristic plan is not
the target D036 product behavior.

## Local Strands orchestration harness

The offline harness drives the real Strands event loop and native interrupt/resume mechanism with a
scripted zero-network model:

```powershell
uv run asset-shepherd agent-run fixtures/broken_robot.glb `
  --profile profiles/unreal_indie_robot.json `
  --output agent-demo-output `
  --decision approve `
  --offline-scripted
```

The CLI prints the combined normalization approval card and its Strands interrupt ID before it
resumes. The deterministic seven-file ZIP remains unchanged; `agent_result.json` sits beside it and
contains the prompt version, user-facing summary, provider/model identity, token usage, tool
success/error/duration metrics, interrupt count, correction count, and final verification state.
This proves tool plumbing, not model judgment or agent-orchestrated repair choice.

Live Bedrock use for the Strands repair workflow remains opt-in and has no hard-coded model ID. Copy
`.env.example` into your environment, set `ASSET_SHEPHERD_MODEL_ID` and region to values available
in your account, and use the standard `AWS_PROFILE`. The live integration test runs only when
`ASSET_SHEPHERD_RUN_LIVE=1`; ordinary tests never look up credentials or make network requests.
