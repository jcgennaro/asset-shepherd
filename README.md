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

For the current Bedrock path, authenticate the `asset-shepherd` AWS profile and set the explicit
environment shown in `.env.example`. It uses AWS session credentials and does not require or send
an OpenAI API key:

```powershell
$env:AWS_PROFILE = 'asset-shepherd'
$env:ASSET_SHEPHERD_INTAKE_PROVIDER = 'bedrock-converse'
$env:ASSET_SHEPHERD_MODEL_PROVIDER = 'bedrock-converse'
$env:ASSET_SHEPHERD_MODEL_ID = 'moonshotai.kimi-k2.5'
$env:ASSET_SHEPHERD_AWS_REGION = 'us-east-1'
.\scripts\Start-AssetShepherd.ps1
```

The upload screen keeps model choice out of the numbered workflow. Its compact **Agent model**
disclosure offers only the reviewed Bedrock Converse allowlist and explains when to try each model:
Kimi K2.5 is recommended; Claude Haiku 4.5 is an experimental speed/cost comparison; Mistral Large
3 and Qwen3 VL are experimental long-context and visual alternatives; Nova 2 Lite is a lower-cost
diagnostic. The selected model is stored with that asset, so resume and Refine never silently
change it. Arbitrary posted model IDs fail closed.

The optional direct-OpenAI development adapter remains available. Save its key once, then start
without setting `ASSET_SHEPHERD_MODEL_PROVIDER=bedrock`:

```powershell
.\scripts\Save-OpenAIKey.ps1
.\scripts\Start-AssetShepherd.ps1
```

Muse Spark 1.3 is available as an opt-in Meta Model API comparator, not as an AWS production
fallback. Save its separate key with Windows user-scoped encryption. For evaluation assets whose
inputs and outputs the user has explicitly agreed Meta may use for model improvement, run the
lower-cost contributor model in a dedicated local workspace:

```powershell
.\scripts\Save-MetaModelKey.ps1
$env:ASSET_SHEPHERD_INTAKE_PROVIDER = 'meta'
$env:ASSET_SHEPHERD_MODEL_PROVIDER = 'meta'
$env:ASSET_SHEPHERD_INTAKE_MODEL = 'muse-spark-1.3-contributor'
$env:ASSET_SHEPHERD_MODEL_ID = 'muse-spark-1.3-contributor'
$env:ASSET_SHEPHERD_ALLOW_META_TRAINING = '1'
$env:ASSET_SHEPHERD_INTAKE_REASONING = 'high'
$env:ASSET_SHEPHERD_WORKFLOW_REASONING = 'high'
.\scripts\Start-AssetShepherd.ps1 -WorkDirectory 'build/web/jobs-muse'
```

The launcher exposes `MODEL_API_KEY` only to the running server process and restores the caller's
environment when it exits. Contributor mode fails closed unless both its exact model ID and
`ASSET_SHEPHERD_ALLOW_META_TRAINING=1` are present. A production evaluation must instead use
`muse-spark-1.3` and omit the training flag. Meta documents `high` as the effective maximum for
Muse Spark 1.3; `xhigh` is accepted by Asset Shepherd as an alias and is normalized to `high`.
See Meta's [release announcement](https://research.meta.ai/blog/introducing-muse-spark-1-3), the
[official API cookbook](https://github.com/meta-models/meta-model-cookbook/blob/main/README.md), and
Strands' [OpenAI-compatible provider documentation](https://strandsagents.com/docs/user-guide/concepts/model-providers/openai/)
for the external-provider boundary.

Nova 2 Lite can still be selected explicitly through the shared Converse adapter:

```powershell
$env:AWS_PROFILE = 'asset-shepherd'
$env:ASSET_SHEPHERD_INTAKE_PROVIDER = 'bedrock-converse'
$env:ASSET_SHEPHERD_MODEL_PROVIDER = 'bedrock-converse'
$env:ASSET_SHEPHERD_INTAKE_MODEL = 'us.amazon.nova-2-lite-v1:0'
$env:ASSET_SHEPHERD_MODEL_ID = 'us.amazon.nova-2-lite-v1:0'
$env:ASSET_SHEPHERD_AWS_REGION = 'us-east-1'
$env:ASSET_SHEPHERD_INTAKE_REASONING = 'medium'
$env:ASSET_SHEPHERD_WORKFLOW_REASONING = 'medium'
.\scripts\Start-AssetShepherd.ps1
```

Asset Shepherd rejects Nova `high`/`xhigh` in this bounded configuration because the live API does
not accept an output-token limit with high reasoning. The legacy `bedrock-nova` provider name
remains loadable for saved configuration, but new configuration should use `bedrock-converse`.

Open `http://127.0.0.1:8010`. **Gallery** starts a new asset or resumes one of seven isolated,
persisted workspaces. The numbered workflow is **1 Upload → 2 Describe → 3 Shepherd → 4 Refine**.
Upload performs objective GLB preflight before the user describes the intended endpoint and
approximate dimensions. At target confirmation the user also chooses whether the asset will normally
be seen close-up, at ordinary gameplay distance, or small/distant/repeated. Asset Shepherd converts
that use-case answer into a 50,000, 15,000, or 2,500-triangle soft cap without asking the user to
choose technical reduction settings. Shepherd lets the Strands agent choose sensing tools, assess evidence, and
propose typed repairs. The user reviews consequential changes; the selected input or candidate can
then enter as many numbered Refine iterations as needed before download.

When a supported mesh exceeds the confirmed cap, the agent may propose one controlled lossy
optimization. The original remains immutable and the user can reject the proposal to preserve full
detail. The deterministic reducer protects small components, original attribute tuples, UVs,
normals, materials, names, and bounds, then reports measured—not predicted—triangle and file-size
changes. Preservation limits may make the safe result larger than the soft cap.

The recommended provider uses Kimi K2.5 through Amazon Bedrock Converse for semantic intake and
workflow decisions. The GLB stays local; the provider receives
the description, structured measurements, and standardized rendered evidence needed for the turn.
Each workspace owns its own durable Strands session and frozen job state, so refresh and restart
resume the same asset without sharing conversation state or repeating mutation. Use
`uv run asset-shepherd web --offline-intake` for the explicit-text intake fallback. Deterministic
providers remain available for zero-network tests.

The Windows launch scripts keep an optional direct-OpenAI development key under the current user's
local app data, outside the repository. In OpenAI mode, the launcher exposes it only to the running
server process and removes it when that command ends. In Bedrock mode, the launcher removes any
inherited OpenAI key and uses only the active AWS session credentials. The direct OpenAI
API remains a development adapter, not a production fallback.

The agent decides which checks and bounded actions are appropriate. Deterministic tools remain
authoritative for measurements, exact action consequences, authorization, source immutability,
mutation scope, independent verification, and packaging. Both the interactive 3D preview and the
standardized model-visible evidence use the pinned local `<model-viewer>` distribution. Evidence
rendering launches an installed Chromium-family browser headlessly; set
`ASSET_SHEPHERD_CHROMIUM_PATH` when browser discovery is unavailable. Blender is only an explicit
local compatibility fallback selected with `ASSET_SHEPHERD_EVIDENCE_RENDERER=blender`, not a
production dependency. Production persistence, judge access, and clean-Linux renderer acceptance
remain explicit AWS deployment gates rather than being implied by the local product.

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

Live Bedrock use for the Strands repair workflow remains opt-in and all model/region values stay
explicit. Copy `.env.example` into your environment, confirm its inference profile is available in
your account, and use the standard `AWS_PROFILE`. The live integration test runs only when
`ASSET_SHEPHERD_RUN_LIVE=1`; ordinary tests never look up credentials or make network requests.

The staged provider, persistence, rendering, AgentCore, web-hosting, observability, and acceptance
procedure is documented in
[`docs/BEDROCK_DEPLOYMENT_RUNBOOK.md`](docs/BEDROCK_DEPLOYMENT_RUNBOOK.md). Follow its gates in order;
do not combine the first Bedrock behavior test with cloud-storage and hosting changes.
