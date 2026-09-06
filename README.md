# Asset Shepherd

Asset Shepherd is an autonomous 3D-asset intake, inspection, repair-planning, and
verification agent for game developers.

> [!NOTE]
> Built for the **Agents for Humans** hackathon, Professional Agents track.
> The authenticated AWS demo is deployed; release validation and submission work remain in progress.

## Current deployment

As recorded on September 6, 2026, the hosted app runs on Amazon ECS Express Mode behind an
Application Load Balancer, with invite-only Amazon Cognito sign-in. Workflow commands pass through
SQS and a Lambda dispatcher to the Strands agent in Amazon Bedrock AgentCore Runtime. S3 stores
artifacts and sessions; DynamoDB stores workspace state and spending reservations. CloudWatch and
SNS provide operational alerts. Local development uses the same application source with local
workspace storage.

Kimi K2.5 through **Amazon Bedrock Converse** is the default. **Luna xhigh through the OpenAI API**
is also available as an explicit hosted selection, using a backend-only AWS Secrets Manager key
and separate OpenAI billing. This is not Luna through Bedrock: that account-access path remains
blocked. There is no silent provider fallback. Meta remains an opt-in local comparator, not a
deployed hosted option; Google is not a hosted option.

The shared demo has a $10/UTC-day **estimated model-spending** emergency ceiling, with $5/$8
warnings; this does not cap hosting costs or impose a 24-runs/day judge quota. Judge credentials
are supplied privately, never in this repository. The demo uses a shared gallery, not private
per-user asset tenancy: use only nonconfidential test assets.

See [current status](docs/PROJECT_STATUS.md), [deployment procedure](docs/BEDROCK_DEPLOYMENT_RUNBOOK.md),
[sign-in operations](docs/HOSTED_LOGIN_RUNBOOK.md), [hosted OpenAI](docs/HOSTED_OPENAI_RUNBOOK.md),
and [spending safety](docs/MODEL_SPENDING_RUNBOOK.md) for acceptance evidence and remaining gates.

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
- [Original component-handling design](docs/FUTURE_COMPONENT_HANDLING.md) — historical proposal;
  current capabilities and authority are recorded in project status and the workflow contract

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

### Fresh laptop setup

Install Git and `uv`, plus Chrome, Edge, or Chromium for evidence rendering. The repository pins
Python 3.12 in `.python-version`; `uv` can provision it during setup. Blender, Unreal, Node.js,
Docker, and an AWS deployment are not required for the normal local app. The browser viewer is
vendored in the repository. AWS CLI and a configured AWS identity are needed only for AWS-backed
work, not direct-API development or the offline harnesses below.

The repository is currently private, so authenticate Git with an authorized GitHub account first.

```powershell
git clone https://github.com/jcgennaro/asset-shepherd.git
cd asset-shepherd
uv sync --locked
```

The clone includes ordinary Git blobs, with no Git LFS step:

| Sample | Path | Approximate size |
|---|---|---:|
| Patchling | `validation/corpus/patchling_01/raw/asset.glb` | 4.9 MB |
| Shader Lantern | `validation/corpus/shader_lantern_01/raw/asset.glb` | 12.8 MB |
| Clean and broken robots | `fixtures/clean_robot.glb`, `fixtures/broken_robot.glb` | 24 KB each |

The shattered-heart collar's [runbook](validation/benchmarks/shattered-heart-collar/README.md)
and run records are included, but its 30 MB raw GLB and screenshots remain ignored pending
redistribution-rights confirmation. Generated outputs, local gallery history, `.venv`, credentials,
and `.env` files are not included. Hosted workspaces remain in AWS; cloning does not copy them into
your local gallery.

API keys must be saved again on the new computer using the helpers below. Do not copy the encrypted
Windows key files between machines: they are protected for the original Windows user/environment.
The PowerShell key helpers require Windows; on other systems, supply the selected provider's key
through a secure process environment and launch `uv run asset-shepherd web` directly. Set
`ASSET_SHEPHERD_CHROMIUM_PATH` if automatic browser discovery fails.

### Bedrock locally

For the current Bedrock path, authenticate the `asset-shepherd` AWS profile and set the explicit
environment shown in `.env.example`. It uses AWS session credentials and does not require or send
an OpenAI API key. The named profile must be configured on the laptop; a clone does not create it.
`.env.example` is a configuration reference, not an automatically loaded dotenv file.

```powershell
$env:AWS_PROFILE = 'asset-shepherd'
$env:ASSET_SHEPHERD_INTAKE_PROVIDER = 'bedrock-converse'
$env:ASSET_SHEPHERD_INTAKE_MODEL = 'moonshotai.kimi-k2.5'
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

### OpenAI locally

Save the key with Windows user-scoped encryption, then explicitly select Luna for both model
boundaries. Model calls incur charges on the configured OpenAI account:

```powershell
.\scripts\Save-OpenAIKey.ps1
$env:ASSET_SHEPHERD_INTAKE_PROVIDER = 'openai'
$env:ASSET_SHEPHERD_MODEL_PROVIDER = 'openai'
$env:ASSET_SHEPHERD_INTAKE_MODEL = 'gpt-5.6-luna'
$env:ASSET_SHEPHERD_MODEL_ID = 'gpt-5.6-luna'
$env:ASSET_SHEPHERD_INTAKE_REASONING = 'xhigh'
$env:ASSET_SHEPHERD_WORKFLOW_REASONING = 'xhigh'
.\scripts\Start-AssetShepherd.ps1
```

### Optional local comparators

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

Gemini 3.8 Flash is also available as an opt-in local comparator through Strands' native Gemini
provider. It is not an Amazon Bedrock model and is not part of the AWS production architecture.
Save its separate key with Windows user-scoped encryption, then isolate test workspaces from the
OpenAI, Bedrock, and Meta runs:

```powershell
.\scripts\Save-GeminiKey.ps1
$env:ASSET_SHEPHERD_INTAKE_PROVIDER = 'gemini'
$env:ASSET_SHEPHERD_MODEL_PROVIDER = 'gemini'
$env:ASSET_SHEPHERD_INTAKE_MODEL = 'gemini-3.8-flash'
$env:ASSET_SHEPHERD_MODEL_ID = 'gemini-3.8-flash'
$env:ASSET_SHEPHERD_INTAKE_REASONING = 'high'
$env:ASSET_SHEPHERD_WORKFLOW_REASONING = 'high'
.\scripts\Start-AssetShepherd.ps1 -WorkDirectory 'build/web/jobs-gemini'
```

The launcher exposes `GEMINI_API_KEY` only to the running server process and restores the caller's
environment when it exits. Asset Shepherd accepts only the exact evaluated model ID and maps its
usual `xhigh` setting to Gemini's supported `high` level. The structured intake uses native Gemini
JSON-schema output, and the Strands workflow sends standardized renders as native image parts.
Create and manage the key in [Google AI Studio](https://aistudio.google.com/apikey). The web app and
geometry tools still run locally in this mode; only model requests leave the workstation.

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

The in-product **FAQ** covers supported formats, source preservation, viewing-use mesh targets,
sequential repair verification, pivot choices, and Windows download troubleshooting. If Chrome
claims a GLB is “blocked by your organization” on an unmanaged personal PC, the FAQ records the
`inetcpl.cpl` Internet Options check that resolved the local test without suggesting that users
disable unrelated security protections.

When a supported mesh exceeds the confirmed cap, the agent may propose one controlled lossy
optimization. If another consequential repair must run first, the agent records optimization as a
typed deferred stage and the verified candidate offers a one-click continuation into its separate
proposal. The original remains immutable and the user can reject the proposal to preserve full
detail. The deterministic reducer protects small components, original attribute tuples, UVs,
normals, materials, names, and bounds, then reports measured—not predicted—triangle and file-size
changes. Preservation limits may make the safe result larger than the soft cap.

The recommended provider uses Kimi K2.5 through Amazon Bedrock Converse for semantic intake and
workflow decisions. In local mode, the GLB stays local; the provider receives
the description, structured measurements, and standardized rendered evidence needed for the turn.
Each workspace owns its own durable Strands session and frozen job state, so refresh and restart
resume the same asset without sharing conversation state or repeating mutation. Use
`uv run asset-shepherd web --offline-intake` for the explicit-text intake fallback. Deterministic
providers remain available for zero-network tests.

The Windows launch scripts keep optional direct-OpenAI, Meta, and Gemini development keys under the
current user's local app data, outside the repository. A launcher exposes only the selected key to
the running server process and removes it when that command ends. In Bedrock mode, the launcher
removes any inherited OpenAI key and uses only the active AWS session credentials. External APIs
remain explicit selections rather than automatic fallbacks. Direct OpenAI is also supported in the
hosted deployment through Secrets Manager; Meta and Gemini remain local comparators.

The agent decides which checks and bounded actions are appropriate. Deterministic tools remain
authoritative for measurements, exact action consequences, authorization, source immutability,
mutation scope, independent verification, and packaging. Both the interactive 3D preview and the
standardized model-visible evidence use the pinned local `<model-viewer>` distribution. Evidence
rendering launches an installed Chromium-family browser headlessly; set
`ASSET_SHEPHERD_CHROMIUM_PATH` when browser discovery is unavailable. Blender is only an explicit
local compatibility fallback selected with `ASSET_SHEPHERD_EVIDENCE_RENDERER=blender`, not a
production dependency. Cloud persistence, invite-only access, and Linux rendering are deployed and
have recorded acceptance evidence; the remaining identity-isolation and full remote validation
matrix are tracked in `docs/PROJECT_STATUS.md`. Task-local pre-intake upload drafts do not yet
survive web-task replacement.

### Local checks (no paid model tests)

In a development shell with live-test opt-in disabled:

```powershell
$env:ASSET_SHEPHERD_RUN_LIVE = '0'
uv run pytest -q
uv run ruff check .
uv run ruff format --check
uv run pyright
uv lock --check
```

The last recorded full gate passed 363 tests with three skips. This is recorded project evidence,
not a claim that every laptop environment has been tested. The offline CLI harnesses below are
useful first smoke tests before configuring a paid provider.

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
