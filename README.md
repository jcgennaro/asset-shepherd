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
- [Contest compliance plan](docs/CONTEST_COMPLIANCE_PLAN.md)
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

Open `http://127.0.0.1:8010`. **Gallery** starts a new asset or resumes one of seven isolated,
persisted workspaces. The numbered workflow is **1 Upload → 2 Describe → 3 Shepherd → 4 Refine**.
Upload performs objective GLB preflight before the user describes the intended endpoint and
approximate dimensions. Shepherd lets the Strands agent choose sensing tools, assess evidence, and
propose typed repairs. The user reviews consequential changes; the selected input or candidate can
then enter as many numbered Refine iterations as needed before download.

The interim local live provider uses OpenAI `gpt-5.6-luna` with `xhigh` reasoning through the
Responses API for semantic intake and workflow decisions. The GLB stays local; the provider receives
the description, structured measurements, and standardized rendered evidence needed for the turn.
Each workspace owns its own durable Strands session and frozen job state, so refresh and restart
resume the same asset without sharing conversation state or repeating mutation. Use
`uv run asset-shepherd web --offline-intake` for the explicit-text intake fallback. Deterministic
providers remain available for zero-network tests.

The Windows launch scripts keep the encrypted development key under the current user's local app
data, outside the repository. The launcher exposes it only to the running server process and removes
it when that command ends. D071 moves production to the same Luna/xhigh behavior through Amazon
Bedrock Responses; the direct OpenAI API remains an interim local provider until that parity gate
passes.

The agent decides which checks and bounded actions are appropriate. Deterministic tools remain
authoritative for measurements, exact action consequences, authorization, source immutability,
mutation scope, independent verification, and packaging. The 3D preview uses the pinned local
`<model-viewer>` distribution, while standardized model-visible evidence is rendered separately.
Production persistence, judge access, and renderer portability remain explicit AWS deployment
gates rather than being implied by the local product.

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

The staged provider, persistence, rendering, AgentCore, web-hosting, observability, and acceptance
procedure is documented in
[`docs/BEDROCK_DEPLOYMENT_RUNBOOK.md`](docs/BEDROCK_DEPLOYMENT_RUNBOOK.md). Follow its gates in order;
do not combine the first Bedrock behavior test with cloud-storage and hosting changes.
