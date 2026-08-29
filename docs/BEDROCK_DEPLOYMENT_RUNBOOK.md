# Bedrock and Strands Deployment Runbook

**Status:** Approved procedure; execution starts at Step 1

**Last verified against official documentation:** 2026-08-29

**Milestone:** M9 hosted Bedrock conversation and deployment

Asset Shepherd already uses Strands as its orchestration layer. This runbook moves the two live
model boundaries from OpenAI to Amazon Bedrock, then moves filesystem-backed application state and
the agent runtime from one Windows workstation to AWS without changing the user/agent/tool authority
contract.

The migration has three independent proof gates:

1. **Bedrock provider gate:** the unchanged local product completes representative workflows using
   Bedrock and makes no OpenAI request.
2. **Cloud-portability gate:** every required job artifact, session, approval, and render can be
   recovered without relying on process memory or a workstation path.
3. **Remote-product gate:** the browser product completes upload through download against the
   remotely hosted agent with observable, bounded, restart-safe behavior.

Do not combine these gates into one debugging exercise. Keep the current local product runnable
until the remote-product gate passes.

## Execution status

- [x] Step 1.1 workstation inspection: AWS CLI v2.36.34 is installed per-user. The Codex process
  inherited an older PATH, so the current shell cannot resolve `aws`; a new terminal should.
- [ ] Step 1.2 dedicated `asset-shepherd` profile and verified caller identity.
- [ ] Step 1.3 account-available Bedrock model and region.
- [ ] Step 1.4 budget alert.
- [ ] Step 2 local all-Bedrock provider gate.
- [ ] Step 3 cloud-portable state and artifacts.
- [ ] Step 4 deployable visual sensing.
- [ ] Step 5 AgentCore runtime.
- [ ] Step 6 remote web product.
- [ ] Step 7 operations and cleanup.
- [ ] Step 8 remote M9 acceptance.

## Controlling constraints

- Keep `workspace_id` as the per-asset conversation and session authority.
- Keep the Strands agent as the semantic orchestrator and the deterministic GLB tools as the
  measurement, bounded-mutation, authorization, and verification authority.
- Do not let chat text authorize a mutation. Consequential changes retain the exact structured
  Strands interrupt, action hash, and explicit user approval.
- Keep source files immutable. Every mutation creates a separately hashed candidate.
- Do not introduce a second conversational authority. AgentCore Memory is optional and is not part
  of the first deployment; Strands session snapshots remain authoritative.
- Do not put the interactive FastAPI/Jinja website inside the AgentCore invocation contract.
- Do not send GLB bytes through every model or AgentCore turn. Upload assets to private object
  storage and pass only a workspace-scoped reference plus its hash.
- Do not hard-code a Bedrock model ID or assume an old tutorial's region availability.
- Do not create paid resources or invoke a paid model before caller identity, region/model access,
  and a budget alert are confirmed.
- Stop for approval before architecture expected to cost more than $10 during development or more
  than $2 per idle day.
- Never commit credentials, account IDs, tokens, presigned URLs, or secret-bearing command output.

## Target deployment shape

```mermaid
flowchart TD
    B[Browser] --> W[FastAPI web service]
    B -->|presigned upload/download| S3[Private S3 asset storage]
    W -->|workspace_id and structured turn| A[AgentCore Runtime]
    A --> ST[Strands agent]
    ST --> BR[Amazon Bedrock model]
    ST --> T[Deterministic GLB tools]
    T --> S3
    ST --> SS[Strands S3 session snapshots]
    W --> D[DynamoDB workspace and command state]
    A --> D
    A --> CW[CloudWatch logs, metrics, and traces]
    W --> CW
    T --> R[Portable renderer or isolated render worker]
    R --> S3
```

The web service authenticates users and invokes AgentCore service-to-service. The browser does not
receive AWS credentials and does not invoke the private agent runtime directly.

## Current implementation map

| Concern | Current implementation | Required migration |
|---|---|---|
| Workflow model | Strands `OpenAIResponsesModel` or `BedrockModel` selected by environment | Configure and evaluate the existing Bedrock path |
| Intake model | Provider-neutral interface with OpenAI and deterministic implementations | Add a Bedrock implementation emitting the same validated schema |
| Agent session | `SnapshotSessionManager` with `LocalFileStorage` under one workspace | Replace storage with Strands S3 session storage while retaining `workspace_id` |
| Workspace record | Atomic JSON files plus process-local locking | DynamoDB record with optimistic/conditional writes |
| Binary artifacts | Per-workspace local directories | Private S3 prefixes with hashes, lifecycle, and presigned transfer |
| Visual sensing | Four standardized Blender renders plus masks | Replace with a portable renderer or isolate rendering outside AgentCore |
| Interactive preview | Browser-local `<model-viewer>` | Retain; serve GLB URLs from authenticated/presigned object storage |
| Web application | FastAPI/Jinja/Uvicorn on localhost | Deploy independently from AgentCore through the simplest stable AWS web route |

## Step 1 — Workstation and AWS account preflight

**Purpose:** establish identity and availability without creating application infrastructure or
making model calls.

### 1.1 Workstation inspection

Run:

```powershell
Get-Command aws -ErrorAction SilentlyContinue
aws --version
```

If AWS CLI v2 is absent, install it from the official AWS distribution and open a new terminal.
Do not put access keys in the repository or a checked-in `.env` file.

If WinGet reports AWS CLI installed but `Get-Command aws` does not find it, open a fresh terminal
before reinstalling. A per-user WinGet installation updates the user PATH, but already-running
processes retain their older environment.

### 1.2 Dedicated profile

Prefer IAM Identity Center when the account provides it:

```powershell
aws configure sso --profile asset-shepherd
```

Otherwise configure a dedicated least-privilege development identity using the account's approved
credential method. Then verify exactly which account and principal will be used:

```powershell
aws sts get-caller-identity --profile asset-shepherd
aws configure get region --profile asset-shepherd
```

Do not paste the returned account number or credentials into project files.

### 1.3 Region and model capability

Choose a region in which the account can invoke a current multimodal, tool-capable Bedrock model.
Record the chosen region and model ID only in local environment configuration. Confirm model access
with the Bedrock model catalog and a bounded provider smoke test only after Step 1.4.

Required model behavior:

- image input for standardized source/candidate renders;
- sequential tool calling with parallel calls disabled or behaviorally constrained;
- the existing typed tool schemas;
- sufficiently large context for the system contract, Job Contract, and bounded tool evidence;
- predictable structured intake output; and
- guardrail compatibility.

### 1.4 Cost checkpoint

Create or confirm an AWS Budget/billing alert before the first paid call. Set conservative
development thresholds and retain evidence that the alert exists without committing account data.

**Step 1 gate:** AWS CLI v2 works, the `asset-shepherd` identity is known, one region/model candidate
is recorded locally, and a budget alert exists. No application resource is required yet.

## Step 2 — Remove OpenAI from the production execution path

### 2.1 Bedrock semantic intake

Implement `BedrockTargetIntakeAnalyzer` behind the existing `TargetIntakeAnalyzer` protocol. It must
produce `TargetIntakeInference`, pass the same Pydantic validation and confidence gates, and retain
provider/model provenance. Normalize the generated schema to the subset supported by the selected
Bedrock model rather than weakening server-side validation.

The deterministic intake implementation remains the zero-network test fallback. The OpenAI adapter
may remain an optional development adapter, but production startup must not require an OpenAI key.

### 2.2 Bedrock workflow configuration

Use explicit local environment values:

```powershell
$env:ASSET_SHEPHERD_INTAKE_PROVIDER = 'bedrock'
$env:ASSET_SHEPHERD_MODEL_PROVIDER = 'bedrock'
$env:ASSET_SHEPHERD_MODEL_ID = '<account-available-model-id>'
$env:ASSET_SHEPHERD_AWS_REGION = '<selected-region>'
$env:AWS_PROFILE = 'asset-shepherd'
```

Update the launcher so Bedrock configuration does not pass through the saved-OpenAI-key path. Keep
model ID, region, retry, timeout, token, and reasoning controls explicit and secret-free.

### 2.3 Behavioral parity evaluation

Run the current local browser product through Bedrock before changing storage or hosting. Cover:

1. clean accept-as-is;
2. ordinary scale/naming repair with approval;
3. ambiguous orientation where the model asks or preserves orientation;
4. disconnected-component selection with user revision;
5. a Refine turn requiring a new consequential action and approval;
6. rejection and subsequent feedback;
7. inappropriate-content refusal; and
8. visual reassessment using source, isolated candidate, and shared-scale comparison renders.

Capture tool calls, typed assessments, provider/model identity, latency, token metrics when reported,
and approximate cost per completed run. Do not publish private reasoning tokens.

**Step 2 gate:** intake and workflow use Bedrock, `OPENAI_API_KEY` is absent, representative D036
cases pass, and the normal offline suite remains green.

## Step 3 — Make state and artifacts cloud-portable

### 3.1 S3 layout

Create one private bucket only after reviewing its region, encryption, public-access block, CORS,
and lifecycle configuration. Use non-guessable workspace IDs and bounded prefixes such as:

```text
workspaces/<workspace_id>/source/source.glb
workspaces/<workspace_id>/iterations/<iteration_id>/candidate.glb
workspaces/<workspace_id>/evidence/<assessment_id>/...
workspaces/<workspace_id>/packages/<package_id>/result.zip
sessions/<workspace_id>/...
```

Store hashes and object version/ETag metadata in the workspace record. Presigned URLs must be
short-lived and scoped to one exact object operation.

### 3.2 Strands session storage

Replace `LocalFileStorage` with Strands S3 session storage. Preserve the same `workspace_id`, stable
agent ID, and exact interrupt-resume behavior. Define deletion and retention for session messages;
do not add AgentCore Memory in this phase.

### 3.3 DynamoDB workspace state

Move the durable workspace record, current phase, iteration lineage, pending interrupt metadata,
processed command IDs, gallery slot, retention marker, and object references to DynamoDB. Use a
monotonic record version and conditional writes so duplicate or racing callbacks cannot execute or
package twice.

**Step 3 gate:** a process can be killed and replaced at intake, approval, repair, refinement, and
completion; the exact workspace resumes from S3/DynamoDB without duplicate mutation or packaging.

## Step 4 — Make standardized visual sensing deployable

The current agent-required renderer invokes locally installed Blender. Resolve this before moving
the GLB tools into AgentCore.

### Preferred route

Package a lightweight Linux/ARM64-capable GLB renderer that produces the existing four
coordinate-labeled 512 px views, masks, camera contract, shared-scale comparison views, and framing
quality metrics. It must preserve material/texture appearance well enough for the D036 visual gate.

### Bounded fallback

If the lightweight renderer misses its written acceptance test, propose—do not silently create—an
x86 ECS/Fargate render worker containing headless Blender. Keep it private, job-scoped, time-limited,
and accessible only through exact S3 inputs/outputs. Measure image size, cold-start time, and cost
before acceptance.

**Step 4 gate:** a clean Linux environment generates nonblank, unclipped, reproducible source,
candidate, and shared-scale views with no workstation path or interactive desktop dependency.

## Step 5 — Deploy the Strands agent to AgentCore Runtime

Create an AgentCore entry point accepting a structured invocation with `workspace_id`, authenticated
actor identity, command ID, and the new user turn. It returns structured workflow state rather than
HTML. Use the same session ID for every turn in one asset workspace.

Choose direct code deployment only if all native dependencies and the renderer pass its runtime
compatibility spike. Otherwise build an ARM64 Linux container exposing AgentCore's required port
8080, `GET /ping`, and `POST /invocations` contract.

The runtime execution role receives least-privilege access to:

- the selected Bedrock model;
- only the required S3 bucket prefixes;
- only the workspace DynamoDB table/indexes;
- CloudWatch logs/traces; and
- any explicitly approved render worker invocation.

Do not make the AgentCore endpoint public. The web service invokes it using service identity and
derives the asset workspace from the authenticated user/session, not arbitrary browser input.

**Step 5 gate:** a direct AgentCore invocation completes a multi-turn inspect → approval interrupt
→ resume → repair → reassess → package flow, with visible logs/traces and exactly-once semantics.

## Step 6 — Deploy the interactive web product

Deploy the existing FastAPI/Jinja application separately through the simplest stable route after a
small compatibility spike. ECS/Fargate or App Runner are candidates; select one from measured
startup, filesystem, request-duration, and cost behavior rather than branding.

The web service owns browser routes, user authentication, gallery authorization, presigned transfer,
and AgentCore invocation. It does not own model reasoning or bypass the structured workflow state.
Keep gallery capacity and workspace isolation exactly as in the local product.

For the competition deployment, provide either logged-out access or one documented test user.
Prefer web authentication plus service-to-service SigV4 invocation; do not distribute AWS
credentials to the browser.

**Step 6 gate:** a fresh user can upload, leave, return through the gallery, approve/refine, and
download from the remote URL.

## Step 7 — Guardrails, observability, retention, and cost

- Apply the existing on-topic/content contract at the model boundary and configure a Bedrock
  Guardrail after verifying that it yields the product's concise refusal behavior.
- Instrument the agent and web request with a shared workspace/turn correlation ID, excluding raw
  GLB contents, secrets, and private reasoning.
- Enable AgentCore/CloudWatch metrics and the traces needed to see model calls and public tool-use
  events.
- Alarm on error rate, invocation duration, throttling, S3 growth, and estimated spend.
- Apply S3 lifecycle and DynamoDB retention cleanup consistent with the documented seven-day private
  workspace policy.
- Test deletion of workspace assets, session state, metadata, and generated URLs.

**Step 7 gate:** the team can diagnose one failed run, prove cleanup, and bound idle and per-run
cost without inspecting secret-laden raw logs.

## Step 8 — Remote M9 acceptance

Run at least these remote cases from a clean browser:

1. valid accept-as-is asset;
2. malformed upload stopped before model invocation;
3. consequential repair approved;
4. consequential repair rejected and refined;
5. disconnected-component review and surviving-iteration promotion;
6. application/runtime restart while approval is pending;
7. duplicate approval callback;
8. model or renderer transient failure with understandable recovery; and
9. completed download whose GLB and evidence package independently reload and match recorded hashes.

Verify that each factual agent claim maps to recorded evidence, no chat text authorizes mutation,
the source object remains unchanged, all user-visible files are intelligibly named, and the current
offline suite still passes.

**Step 8 gate:** every M9 gate in `PROJECT_CONTRACT.md` passes. Stop for mandatory checkpoint 3
before public release or submission work.

## Rollback and fallback

- A failed Bedrock evaluation returns development to the working OpenAI adapter without changing
  deterministic tools or persisted contracts.
- A failed AgentCore spike may be replaced only by an explicitly approved Strands/Bedrock deployment
  on a conventional AWS compute service; the architecture change must be recorded.
- A failed remote web deployment must not remove the working local path.
- AWS resources created for a rejected route must be inventoried and deleted before trying another
  route.

## Official references

- [Strands Amazon Bedrock provider](https://strandsagents.com/docs/user-guide/concepts/model-providers/amazon-bedrock/)
- [Strands session management and S3 storage](https://strandsagents.com/docs/user-guide/concepts/agents/session-management/)
- [AgentCore Runtime operation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-how-it-works.html)
- [AgentCore direct code deployment](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-code-deploy.html)
- [AgentCore Runtime permissions](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html)
- [AgentCore quotas](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/bedrock-agentcore-limits.html)
- [AgentCore authentication](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-oauth.html)
- [AgentCore observability](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-configure.html)
