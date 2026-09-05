# Asset Shepherd Decision Log

Record decisions that materially affect architecture, product behavior, cost, security, or scope.

## Decisions

### D113 — Preserve same-origin native forms behind the login gate

**Date:** 2026-09-05

**Status:** ACCEPTED; local browser regression passes; web deployment pending

The hosted Redo form failed before its handler because D111 applied `no-referrer` to every page.
For native non-CORS POST navigation, that policy produces `Origin: null`; the exact-origin CSRF
gate then rejects a legitimate same-site action. Use `Referrer-Policy: same-origin` for application
responses and retain `no-referrer` on `/auth/` routes, including callback redirects. Keep exact
configured-origin enforcement, signed sessions, and rejection of missing/null origins unchanged.
No Referer fallback, cross-origin exception, new secret, or model run is needed. A fresh headless
Chromium profile verifies native loopback form submission using the actual application policy,
without attaching to the owner's browser. See `HOSTED_LOGIN_RUNBOOK.md`.

### D112 — Explicit hosted OpenAI Luna after the renewed Bedrock denial

**Date:** 2026-09-05

**Status:** ACCEPTED; AgentCore proposal-stage acceptance and authenticated web deployment pass

The user requested one more Bedrock Luna attempt and, if still blocked, secure AWS storage of the
OpenAI key and a Luna xhigh trial. The authenticated Bedrock Responses request still returns account
unavailability. Publish the existing DPAPI-protected key to a separate Secrets Manager secret and
give only ECS intake and AgentCore workflow roles exact-secret read permission. Use one shared,
explicit model/provider resolver with a deployment allowlist; preserve every existing workspace's
model. No automatic fallback, Meta enablement, or Google enablement is authorized here. OpenAI
billing remains external to AWS credits, and D107's external-provider content-boundary distinction
still applies. Both intake and workflow use Luna xhigh. See `HOSTED_OPENAI_RUNBOOK.md`.

The first key/access check passes from the developer computer with 16 tokens. Do not call this an
AWS runtime or completed-asset acceptance until its separate checks pass. Protect secrets and
OAuth codes from logs; no prompt-injection tests are performed.
The subsequent AgentCore v8 test reaches native approval with the unchanged saved tablet source:
75.83 seconds wall time, 47,230 input/4,360 output tokens, and no consequential mutation. Keep Kimi
as the deployment/legacy default; Luna is an explicit new-workspace choice, not a global migration.
Web task revision 12 is deployed successfully with zero old tasks. The signed-in browser shows
both model choices and the probe's proposal/3D preview; anonymous data/actions remain denied.
Full browser intake-through-repaired-download acceptance remains for an explicitly approved run.

### D111 — Invite-only Cognito gate for the shared contest demo

**Date:** 2026-09-04

**Status:** ACCEPTED; deployed anonymous-denial checks pass; human first-login acceptance pending

The user confirmed the public endpoint must require login. Use Cognito with administrator-only
invitations, no public signup, and an application-wide session gate for data and actions. Keep the
existing shared demo owner: invited users share the gallery. This explicitly does not claim
per-user private workspaces. Use standard Authlib OIDC/PKCE validation and a Secrets Manager-generated
server-only signer for Secure/HttpOnly host-only cookies. Keep provider keys out of this change.
AWS console authentication remains separate from website authentication. No prompt-injection tests
are authorized or required. Details and remaining limitations: `HOSTED_LOGIN_RUNBOOK.md`.
The owner rejected Cognito's generic invitation as unrecognizable (it also landed in spam). Use
an Asset Shepherd-branded subject and responsive HTML invitation, a fixed application link, and
clear first-login/shared-gallery guidance. Keep AWS's default sender until an SES identity is
explicitly verified. A branded replacement invitation invalidates the old temporary password.

### D110 — Fixed-resolution evidence and bounded repeated sensing failures

**Date:** 2026-09-04

**Status:** ACCEPTED; local regression and proposal-stage provider comparisons pass

The Smartpad Tablet's hosted failure was real screenshot cropping caused by adaptive rendering,
not a content-policy block. Fix the dedicated capture page at render scale 1, validate capture
dimensions, and invalidate cached views through contract 7. Preserve the 512px evidence capture,
existing compact model-facing contact sheet, and all occupancy/clipping checks.

After two identical visual-sensing failures in an invocation, stop the Strands loop after tool
results are recorded and before another model call. Count the prerequisite across tool names;
reset only on an explicitly new invocation. Preserve usage and a recognizable error so the UI can
explain the rendering failure. Do not silently skip visual evidence or authorize a repair.

Luna xhigh and Muse Contributor/high each formed a valid proposal and stopped at approval on the
same unchanged source and target using the fixed local renderer. This comparison neither changes
the public model default nor establishes end-to-end repaired-output acceptance. Details, usage,
timing qualifications, and the replay command are in `TABLET_RENDER_REGRESSION.md`. No injection
attempts were tested.

### D109 — Reduce prompt-attack sensitivity after an ordinary-asset false positive

**Date:** 2026-09-04

**Status:** ACCEPTED; deployed to both consumers, benign-request acceptance passes

**Decision owner:** User and Codex

**Milestone:** M9 hosted conversation and deployment

The reconstructed Smartpad Tablet start request was blocked by version 1's `PROMPT_ATTACK` filter:
confidence `LOW`, configured strength `HIGH`. Every other category and denied topic was undetected.
The user requested substantially lower sensitivity and explicitly prohibited injection-attempt
tests. No such tests were run for this change.

Change only prompt-attack input strength to `LOW`, publish a new immutable version, and pin both
the web intake and AgentCore deployment to it after benign-request acceptance. Preserve version 1
as a separate CloudFormation resource while consumers roll forward. Keep the existing content
categories, denied topics, exact refusal, and deterministic approval/tool boundaries unchanged.
Acceptance uses ordinary asset descriptions and the reconstructed saved tablet job request only;
it makes no claim about attack-detection performance at the lower sensitivity.

The guardrail stack reached `UPDATE_COMPLETE` and published immutable version `2`. Its input
checks allow 4/4 benign cases: the complete reconstructed saved tablet start message, the tablet
description, a tabletop radio, and a city-bus-sized robot dog. The previously blocked full tablet
message still receives LOW classifier confidence but is allowed at LOW filter strength. No Kimi
invocation or injection-attempt test was used for these checks. Common quality gate: 268 passed,
3 skipped, lock/Ruff/format/Pyright clean. AgentCore runtime version 6 is READY and the web stack
reached UPDATE_COMPLETE with ECS task definition 9; both explicitly pin Guardrail version 2. The
content-policy comparison shows only PROMPT_ATTACK changed; all denied topics remain identical.

### D108 — Route all contest alarms through one confirmed private email topic

**Date:** 2026-09-04

**Status:** ACCEPTED; deployed and verified through recipient inbox delivery

**Decision owner:** User and Codex

**Milestone:** M9 hosted conversation and deployment

**Context**

The eight bounded project alarms were live and healthy but deliberately had no notification action.
Step 7 requires one actionable route. The user supplied a private notification address, which must
not be committed, logged by the application, or duplicated across alarm resources.

**Decision**

Create one standard SNS topic in the operations stack and subscribe the deployment-supplied email
through a `NoEcho` CloudFormation parameter. Attach all eight alarms to that topic only for entry
into `ALARM`; do not emit recovery or initial-state email noise. Require the recipient to confirm
the AWS subscription before treating the route as operational. Keep the address out of repository
content, outputs, application configuration, and application logs.

**Evidence and consequences**

Source acceptance requires exactly eight alarm actions, one shared topic, a `NoEcho` address
parameter, and no committed Gmail address. The live `asset-shepherd-operations` stack reached
`UPDATE_COMPLETE`; all eight alarms have exactly one enabled action on the shared topic and remain
`OK`. The subscription is confirmed. A bounded test placed only the dispatcher-throttles alarm in
`ALARM`; CloudWatch recorded successful execution of the SNS action, and the alarm was restored to
`OK` without invoking an application workflow or model. The recipient supplied the delivered email
for the test at 2026-09-04 15:36:18 UTC (11:36 a.m. Eastern), completing the end-to-end notification
gate. The email body and unsubscribe link are not retained in the repository.

### D107 — Bind deployed Bedrock inference to one immutable narrow content boundary

**Date:** 2026-09-04

**Status:** ACCEPTED; deployed application acceptance passes

**Decision owner:** Codex

**Milestone:** M9 hosted conversation and deployment

**Context**

Asset Shepherd already shared one exact application-level refusal across target intake and workflow
prompts. The public AWS path also needs a model-boundary control without blocking legitimate game
art such as fictional weapons, monsters, horror, or destructive machines. Bedrock providers can use
a native Guardrail; external OpenAI and Meta APIs cannot.

**Decision**

Deploy a separately versioned `asset-shepherd-guardrail` stack. Deny sexual exploitation,
extremist recruitment, and material enablement of real-world wrongdoing, use high content filters
for sexual, hate, misconduct, and prompt-attack inputs, and deliberately omit the general violence
filter so normal fictional game assets stay in scope. Use the exact existing refusal for input and
output intervention. Pin deployments to an immutable numeric version, never `DRAFT`.

Apply the Guardrail to the latest user text/image message in Strands Bedrock Converse turns so the
trusted system policy is not itself classified. Apply the same version to direct Converse target
intake. Fail closed when only an ID or version is configured, and grant each service role
`bedrock:ApplyGuardrail` only for the generated Guardrail ARN. Keep the shared prompt/application
boundary for all providers; OpenAI and Meta remain supported but are not represented as protected by
a Bedrock control.

**Evidence and consequences**

The stack reached `CREATE_COMPLETE` with ID `xadkxnj292qu` and version `1`. Direct `ApplyGuardrail`
tests allow railgun, horror-monster, medieval-sword, FPS-rifle, and pet-collar requests and block
explicit sexual content, sexualized-minor content, extremist recruitment, and concealment of a real
explosive, passing the eight-case boundary matrix. Direct Kimi Converse accepts the fictional sword
case and returns `guardrail_intervened` with the exact refusal for extremist recruitment. Focused
adapter tests prove immutable environment validation, exact redaction wording, latest-message
configuration, intake request wiring, and safe intervention mapping. Rebuilt AgentCore/web images
passed their architecture-specific CodeBuild gates. AgentCore runtime v5 and ECS task definition 7
carry Guardrail version 1. The public intake emits the exact refusal without echoing a blocked
request and preserves an ordinary 30 cm Unreal robot request through target proposal. The temporary
allowed workspace was then purged with five object versions removed and `VerifiedEmpty=True`. A
bounded status call started runtime v5 and recovered the accepted workspace at `COMPLETE`; ten
health checks, the accepted notebook, its exact GLB download, and all eight alarms pass.

### D106 — Keep contest operations bounded, correlated, and explicitly erasable

**Date:** 2026-09-04

**Status:** ACCEPTED; low-cost operations foundation deployed, Step 7 remains in progress

**Decision owner:** Codex

**Milestone:** M9 hosted conversation and deployment

**Context**

The live product already had service logs, Bedrock metrics, S3 lifecycle expiry, DynamoDB TTL, a
dead-letter queue, Lambda X-Ray passthrough, and the managed ECS deployment alarm. It did not have a
single operational view, project-owned alarms, bounded log retention, command IDs in both sides of
the AgentCore bridge, or an independently verifiable way to erase every version of one failed test
workspace. Enabling detailed Bedrock request/response logging would expose prompts and rendered
evidence without being necessary to diagnose the deployment.

**Decision**

Deploy one `asset-shepherd-operations` CloudFormation stack containing a CloudWatch dashboard and
eight no-notification alarms: Lambda errors, throttles, and near-timeout duration; SQS backlog and
DLQ depth; Bedrock client and server errors for the selected model; and a 5 GiB private-workspace
storage soft limit. Retain every project CodeBuild, ECS, Lambda, and AgentCore log group for seven
days. Emit only workspace ID, command ID, operation, phase/state, and duration as cross-service
correlation fields; never log prompts, GLB bytes, screenshots, provider responses, credentials, or
private reasoning.

Keep the existing concise application-layer content refusal while Bedrock Guardrail compatibility
and public wording are tested separately; do not claim an unverified Guardrail integration. Keep
the existing user-created AWS Budget as the spend alert rather than duplicating account billing
configuration in the application stack.

Keep the contest web tier in two public subnets in different Availability Zones, not every subnet
in the default VPC. Size its single task from measured utilization at 0.5 vCPU and 1 GiB. This keeps
managed HTTPS and multi-AZ ingress while bounding public IPv4 and Fargate idle spend. Treat a
continuously available endpoint as an explicit test/review-window choice rather than a free default.
Because an existing Express shared ALB can retain its old zone set when service networking changes,
reconcile it with a separate fail-closed script that discovers only the tagged project ALB, validates
the two public subnets and VPC, applies the exact set, waits for availability, and verifies the result.

Provide an administrator-only, `ShouldProcess`-protected cleanup script. It accepts exactly one
32-hex workspace ID, verifies the application owner when a pointer exists, and deletes only that
workspace's current and noncurrent S3 object/session versions plus its DynamoDB pointer and command
receipts. An explicit orphan flag is required when the pointer is already gone. It then re-queries
all four locations and fails closed unless they are empty.

**Evidence and consequences**

The operations stack reached `CREATE_COMPLETE`; the dashboard is `asset-shepherd-contest`. All five
discovered project log groups report seven-day retention. A dry run named only the known corrupted
deployment-test workspace `b082803b950b441c92b53c366d714927`; the real cleanup removed its
remaining workspace versions, Strands session versions, and four command receipts. Independent AWS
queries then returned zero versions/markers, no workspace pointer, and zero command receipts. The
successful public demo workspace was not touched. The cleanup verifier initially miscounted an
empty PowerShell value; that presentation bug was fixed and the now-empty target reports
`VerifiedEmpty=True`.

All eight alarms settled to `OK`. AgentCore runtime version 4 uses immutable image
`e0356a6-ops-agentcore`; the Lambda dispatcher uses content-addressed package
`dispatch-247c24908e3cdf07345f8ee59ba8fd0093c9696a135e672feaf3c1f809b9892e.zip`. One no-model status
command traversed the production SQS/Lambda bridge and reached `SUCCEEDED`; its exact command ID
appeared in both services' bounded start/success events, and AgentCore also recorded `COMPLETE` plus
duration. The accepted workspace remained version 6 and download-ready.

The accepted public workflow's recorded Kimi planning and approval turns cost about $0.114 at the
documented $0.60/M input and $3.00/M output rates (175,184 input and 2,934 output tokens), excluding
the separate intake call and AWS compute. The first ECS Express default used a 1-vCPU/2-GiB task and
all six default-VPC subnets, which allocated seven public IPv4 addresses and implied an approximately
$76.95/month fixed floor. The accepted configuration uses 0.5 vCPU/1 GiB and two subnets. Published
us-east-1 Fargate, Application Load Balancer, and three-public-IPv4 rates bound its fixed floor at
about $0.0622/hour, $1.49/day, or $44.77 per 30-day month before variable traffic and service usage.
Live metrics peaked at 43.1% of the old vCPU and 11.5% of its 2 GiB, leaving measured headroom in the
smaller task. AgentCore has no preallocated idle compute charge while its session is stopped. This
is an observed provider subtotal and infrastructure floor, not an estimate of the complete bill.
The live subnet script first named only the tagged Express ALB in `us-east-1a` and `us-east-1b`, then
applied and verified those exact zones. The ALB API and managed endpoint DNS now expose only the two
selected addresses. Ten consecutive health requests, the accepted notebook, and the 24,580-byte GLB
download passed after the resize; all eight project alarms remained `OK`.
Alarm notification routing, multi-user authentication, Guardrail acceptance, and the full Step 8
failure matrix remain open.

### D105 — Dispatch long AgentCore turns through durable SQS receipts and Lambda

**Date:** 2026-09-04

**Status:** ACCEPTED; live Step 6 gate passed

**Decision owner:** Codex

**Milestone:** M9 hosted conversation and deployment

**Context**

The existing FastAPI routes synchronously ran Strands and the deterministic tools inside the web
process. Representative AgentCore turns take roughly two minutes and can run longer, so forwarding
the same blocking request through an Application Load Balancer would couple browser availability to
model latency and lose in-flight work when an ECS task is replaced. The D093 contract already
requires `202 Accepted` and typed status polling.

**Decision**

The ECS web task validates and records a schema-versioned command receipt in the existing DynamoDB
table, then sends only that bounded command to an encrypted SQS queue. A one-message Lambda consumer
invokes the private AgentCore Runtime with the workspace-bound runtime session. It updates the
receipt to `RUNNING`, `SUCCEEDED`, or `FAILED`; the browser polls that receipt and reloads the durable
notebook only after completion. A caught transport failure is terminal for that receipt and requires
a fresh command ID rather than an automatic replay, because an AgentCore invocation can outlive the
client transport that started it. SQS is at-least-once, while the stable command ID and AgentCore's
persisted `processed_commands` boundary make the mutation exactly-once. GLB bytes, provider secrets,
free-form paths, and AWS credentials never enter the message or browser.

Keep local Uvicorn behavior synchronous when the queue is not configured. Build the AgentCore image
for ARM64 and the ECS Express web image for x86_64, matching each managed service's runtime contract.
Use one ECS task for the contest gate to keep cost and pre-workspace upload staging predictable; S3
and DynamoDB remain authoritative after workspace creation.

**Evidence and consequences**

Focused acceptance proves typed enqueue, actor binding, conflicting command rejection, safe resend
before dispatch, suppression while running, HTTP 202 receipts, and pollable status without starting
the local agent. The CloudFormation template creates encrypted command/DLQ queues, a least-privilege
Lambda dispatcher, separate ECS execution/infrastructure/task roles, and the ECS Express service.
The dispatcher disables SDK retries and allows an 850-second response read so one slow AgentCore
turn cannot become overlapping invocations. Its IAM policy grants only the selected runtime and its
`DEFAULT` runtime endpoint, both of which AgentCore requires. The web container trusts the managed
ingress forwarding headers so redirects remain HTTPS.

The live `asset-shepherd-web` stack passed its alarm bake on 2026-09-04 with image `2e206e3-web` at
`https://as-73038a3f3e8d40819c72ccb90d068ec4.ecs.us-east-1.on.aws`. A clean Kimi workflow returned
HTTP 202 in about 0.5 seconds, persisted the exact approval interrupt, completed the approved repair,
and reached accepted record version 6. Its two recorded agent invocations used 175,184 input and
2,934 output tokens over 84.0 seconds. The 24,580-byte candidate downloads as
`upright-robot-prop_shepherded_090426.glb` with `model/gltf-binary`. After forcibly replacing the ECS
task, the gallery, accepted notebook, and download all rehydrated from S3/DynamoDB without rerunning
the model or mutation. This adds two small request-driven services but avoids load-balancer timeouts
and replaceable-task coupling. Step 6 is complete; Step 7 operational hardening and the full Step 8
remote matrix remain.

### D104 — Build one gated ARM64 image and expose only typed AgentCore commands

**Date:** 2026-09-03

**Status:** ACCEPTED; runtime deployed and full acceptance gate passed

**Decision owner:** Codex

**Milestone:** M9 hosted conversation and deployment

**Context**

AgentCore Runtime requires a Linux ARM64 container with `/ping` and `/invocations`; the Windows
workstation has no Docker engine. The hosted workflow also cannot safely expose its interactive
website, arbitrary prompts, GLB bytes, filesystem paths, or provider keys as a generic runtime
payload. The renderer must be proven in the exact deployment architecture before the runtime can be
trusted.

**Decision**

Build remotely in a small ARM64 CodeBuild environment from a committed-only S3 source archive.
Publish to a private immutable-tag ECR repository only after an explicit acceptance marker proves
the architecture, packaged Chromium source/shared-scale render paths, masks, AgentCore import, and
`/ping`. Keep the FastAPI web and AgentCore commands as separate container targets over one shared
base.

Expose a discriminated, schema-versioned AgentCore command union for read-only status, confirmed
target execution, exact interrupt approval/rejection, typed plan revision, result acceptance or
refinement, and bounded retry. Bind every command to the configured actor, workspace identifier,
`workspace-<id>` AgentCore session, and idempotent command identifier. Return only bounded workflow
state. The runtime hydrates disposable cache state from the D103 S3/Dynamo repository and never
accepts asset bytes or arbitrary paths.

Create a separate AgentCore-only execution role instead of broadening the local test role. Its
trust policy is source-account/source-ARN constrained; data, ECR, Bedrock, logs, metrics, and trace
permissions are scoped to the deployed resources and accepted models. Bedrock uses IAM. Future
OpenAI and Meta keys must use distinct AgentCore Identity API-key credential providers (or
referenced Secrets Manager secrets) and exact retrieval grants; keys never enter images,
CloudFormation parameters, browser code, or ordinary environment variables. Google remains outside
the deployed allowlist.

**Evidence and consequences**

The initial CodeBuild run surfaced a Chromium sandbox startup failure and also proved that CodeBuild
post-build phases run after a failed build. The rejected ECR image was deleted, the pipeline now
requires a success marker before push, and Chromium retains bounded stderr for future diagnosis.
The accepted rerun proved `arm64/linux`, eight rendered views plus masks, and application import in
59 build seconds before publishing a 387,633,373-byte compressed image. Chromium's inner sandbox is
disabled only for the AgentCore container target, which runs inside AgentCore's managed isolation
and processes loopback-served bounded assets with vendored viewer code. This remains a deliberate
defense-in-depth tradeoff; the public ECS web target does not inherit that setting. Four boundary
tests prove actor/session confusion and undeclared prompt fields fail closed. The common gate passes
with 253 tests and three intentional live skips.

CloudFormation then deployed the accepted immutable AgentCore image and separate service-only role.
A direct typed status call returned HTTP 200 from a cloud-hydrated workspace. A paid Kimi turn
produced an exact approval interrupt, and approval resumed deterministic mutation, Chromium
rendering, invariant verification, evidence packaging, and versioned S3/DynamoDB persistence in the
managed runtime. Every deterministic check passed, but Kimi rejected the synthetic robot candidate
as visually inverted, so the workflow correctly persisted `BLOCKED`. The run took 168.65 seconds
and recorded 208,234 input plus 11,444 output tokens. A second turn fixed orientation but left the
height at 3.4 m: this smoke seed bypassed semantic intake, and its height-only description had been
expanded to a synthetic 1.8 m cube whose deterministic log-space best fit selected scale 1.0. Kimi
again rejected the candidate after 434,254 input and 4,958 output tokens. Replaying the exact second
approval returned the same state without advancing durable record version 8, proving persisted
command idempotency. This establishes the deployed invocation, interrupt/resume, tool, renderer,
verification, persistence, and duplicate-command boundaries; a representative fully specified
successful candidate and replaced-runtime replay remained open at that checkpoint.

The final gate used the frozen `broken-normalization` case with a fully specified 122 × 182 × 40 cm
target. Approval completed normalization, name repair, Chromium evidence, deterministic verification,
visual reassessment, and packaging. The durable result was `COMPLETE` and download-ready with no
failed checks and only the expected material-budget warning. Kimi confirmed the intended dimensions,
orientation, grounding, retained parts, and names at 0.95 confidence. The turn took 114.76 seconds
and recorded 169,391 input plus 1,909 output tokens. An identical approval replay preserved durable
record version 5. After `StopRuntimeSession` terminated the managed microVM, the same runtime session
and command rehydrated the identical complete version 5. The private runtime therefore passes the
multi-turn success, exact interruption, idempotency, and replaceable-compute requirements.

### D103 — Back replaceable processes with immutable S3 manifests and conditional DynamoDB state

**Date:** 2026-09-03

**Status:** ACCEPTED

**Decision owner:** Codex

**Milestone:** M9 hosted conversation and deployment

**Context**

The local hosted product already survives a process restart because its files remain on one
workstation. ECS and AgentCore processes are replaceable, so an absolute Windows path, a mutable
container directory, or a last-writer-wins remote JSON object cannot be the production authority.
Approval commands also need one atomic version boundary so two callbacks cannot both advance and
package the same workspace.

**Decision**

Deploy one retained private state stack: an encrypted/versioned S3 bucket with a seven-day
lifecycle, an encrypted on-demand DynamoDB table with owner/update index and TTL, and an
exact-resource policy on the restricted runtime role. Preserve local storage as the default.
Complete cloud configuration selects Strands `S3SessionManager` plus an S3/Dynamo workspace
repository; partial configuration fails startup instead of silently losing durability.

Persist workspace files as workspace-scoped content-addressed S3 objects. Write one immutable
manifest per monotonically increasing record version, then conditionally advance DynamoDB from the
expected version to that manifest. Hydration materializes a disposable local cache, rejects
absolute or escaping paths, and verifies every SHA-256. Persist iteration references relative to
the workspace root so the same state can move from Windows to a Linux container; continue to read
legacy absolute-path schema version 1 locally.

**Evidence and consequences**

Unit acceptance proves clean-process restoration, conditional stale-write rejection, unchanged-GLB
deduplication, manifest path confinement, and fail-closed cloud configuration. A live proof through
the restricted `asset-shepherd` role replaced the process cache after intake, after the approval
interrupt, and after verified packaging; restored exact GLBs and the interrupt; executed one
authorized repair; preserved an exact duplicate package; queried the owner index; and deleted the
active smoke pointer. The cloud-configured FastAPI app also returned its gallery.

S3 retains immutable orphan/content history until lifecycle expiration; deleting the active
DynamoDB pointer does not immediately erase those objects. The full intake/approval/repair/refine/
agent-orchestrated refinement replacement is still required before Step 3 closes. Browser presigned transfer,
multi-user authentication, Linux rendering, AgentCore, and ECS remain later gates.

### D102 — Name direct verified-model downloads as dated Shepherd outputs

**Date:** 2026-09-03

**Status:** ACCEPTED

**Decision owner:** User

**Milestone:** M9 hosted conversation

**Context**

The browser previously saved a verified model under only the agent-assigned asset slug. That made
the repaired output difficult to distinguish from its source in an ordinary Downloads folder and
did not communicate when the output was produced.

**Decision**

Name every direct verified-model download
`<asset-slug>_shepherded_MMDDYY.glb`, for example
`tabletop-radio_shepherded_090326.glb`. Use the same name in the HTML download hint and the HTTP
`Content-Disposition` header. Keep internal immutable candidates and the evidence package's
contracted `repaired.glb` member unchanged so deterministic consumers and existing provenance do
not depend on a presentation filename.

**Evidence and consequences**

Local and hosted endpoints now share one filename helper. Focused web tests prove the exact example,
the dated HTML hint, the response-header suffix, and the unchanged seven-file evidence package.
The common quality gate passes with 240 tests, two intentional live-provider skips, lock validation,
Ruff lint/format, and zero Pyright findings.

### D101 — Render completed simplification from durable verification facts

**Date:** 2026-09-03

**Status:** ACCEPTED

**Decision owner:** Codex

**Milestone:** M9 hosted conversation / M10 evaluation

**Context**

Muse workspace `ac4d03a975844b8cb8b3d6b721767517` successfully completed the new
candidate-based simplification turn for the 65-part broken-heart collar. Packaging atomically
renamed `output/candidate.glb` to `output/repaired.glb`, as designed. The result renderer then
attempted to `stat()` the obsolete candidate path while building the Topology row and raised an
uncaught `FileNotFoundError`, replacing the otherwise successful result with a raw 500 page.

Inspection also showed that hosted approval events used the literal `normalize-root-v1` candidate
ID even when the selected approval action was `simplify-mesh-v1`. Decisions, repair provenance, and
the output package contained the correct action; the minimized workspace event label did not.

**Decision**

Build the completed simplification summary from the durable verification record. Use the source
inspection's recorded byte count and `MESH_SIMPLIFICATION_FILE_SIZE_REDUCED.actual` for the measured
output byte count instead of depending on a transient pre-packaging filename. If an older
verification lacks the optional size check, show the verified triangle reduction without inventing
a file size.

Record the selected plan's actual approval action ID in both interrupt-created and decision events.
Do not encode a repair-kind-specific constant at the provider-neutral workspace boundary.

**Evidence and consequences**

A regression test completes and packages an agent-orchestrated simplification, proves
`candidate.glb` has been renamed away, then renders an addressed Topology summary with measured
triangle and file-size changes. The saved collar package remains valid and needs no repair rerun;
refreshing its page after the server update recovers the completed result.

### D100 — Make deferred mesh optimization a typed, sequential repair

**Date:** 2026-09-03

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 hosted conversation

**Context**

An over-budget Gemini run correctly chose physical normalization before lossy mesh simplification,
but the only available assessment representation described that choice as though the agent had
ignored optimization. The user then had to infer that a freeform refinement was required. Scale,
grounding, and pivot changes are technically compatible with simplification, but combining them in
one candidate would make a failed bounds, topology, or visual check harder to attribute and would
let one approval authorize two materially different changes.

The same review found that Chrome's generic “blocked by your organization” download message can
appear on a personal, unmanaged Windows computer with no Chrome policies. Reviewing the relevant
Internet Options setting through `inetcpl.cpl` restored the local GLB download.

**Decision**

Keep physical normalization and lossy simplification in separate candidate and verification lanes,
but make their sequence explicit and easy. The agent may attach the typed
`deferred_repair_kinds=["SIMPLIFY_MESH"]` marker only when it proposes a different repair first and
the measured source exceeds the confirmed use-case cap through a safely simplifiable primitive.
The topology row then says optimization is queued instead of saying it was not proposed.

After the first candidate passes, offer **Continue to mesh optimization** as a one-click,
candidate-based refinement and **Finish with this version** as the non-lossy exit. Continuing
re-inspects the verified candidate and requires a fresh simplification proposal and approval; the
first repair's approval never authorizes the second. Preserve the general freeform refinement path.

Add a persistent FAQ entry to the utility navigation. It explains formats, source preservation,
use-case triangle caps, sequential repair rationale, pivots, and cautious Windows download
troubleshooting without claiming that the user's unmanaged machine has an organization policy.

**Evidence and consequences**

Typed-model tests prove current and deferred simplification cannot coexist. Agent-job validation
rejects deferral for an asset that is already within its cap or has no safe simplification path.
Prompt and hosted-page coverage protect the agent instruction, the FAQ, and navigation. A deferred
second stage costs another bounded model turn only when the user explicitly continues; it is never
silently purchased or applied.

### D099 — Canonicalize target forms and ask viewing use once

**Date:** 2026-09-03

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 hosted conversation

**Context**

After a local server restart, saved Gemini workspace `d53910f6f898440b8b447a9801ad9b5e`
reached endpoint clarification with an otherwise valid Dog Helmet target draft. Submitting a
canonical engine also submitted a stale value from the always-enabled `Other destination` field.
The target contract correctly rejects endpoint detail for Unity, Unreal, and Godot, but the form
boundary passed the irrelevant string through and exposed the resulting raw Pydantic validation
diagnostic in the conversation.

The same endpoint card also collected the ordinary-language viewing-use choice, but the following
target review rendered the full question again. Its permanent explanation introduced polygon
terminology even when the user did not need it.

**Decision**

Treat canonical endpoint enums as complete values. Both clarification and revision discard any
submitted endpoint detail unless the selected endpoint is Other. As progressive enhancement, hide
and disable the Other text field until Other is selected, but retain the server-side invariant as
the authority because browser state and direct requests cannot be trusted. Convert any unexpected
typed-contract construction failure at this boundary to a concise target retry message.

Record whether viewing use already has explicit user evidence. If the user chose it beside a
missing endpoint, do not ask again on the review card; if no explicit choice has yet been made, ask
once there. Move the explanatory sentence behind a question-mark dialog. The dialog describes the
50,000-triangle hero/close-up, 15,000-triangle normal-gameplay, and 2,500-triangle
background/repeated guidelines, explains that below-guideline geometry is preserved, and states
that a proposed optimization can be declined.

**Evidence and consequences**

Regression acceptance submits a canonical endpoint with a deliberately stale Other value and
proves the persisted endpoint detail is null. Unit coverage applies the same invariant to target
revision. Hosted rendering coverage proves the viewing-use question appears before clarification,
does not appear again after an explicit selection, remains available on first-time review paths,
and exposes the detailed complexity policy only through a native dialog. Static acceptance covers
the dialog and endpoint-state handlers. The common gate passes with 235 tests, two intentional
live-provider skips, lock validation, Ruff, formatting, and zero Pyright findings.

### D098 — Bound Gemini thinking and explain recoverable response-limit failures

**Date:** 2026-09-03

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 hosted conversation / M10 evaluation

**Context**

Gemini workspace `c839d09e26b6450fa092615f0055302e` completed deterministic inspection
and rendered evidence, then stopped before submitting its assessment. The failure happened while
the user happened to rotate the browser viewport, but the camera handler performs only local HUD
projection and sent no workflow request. Durable state records the actual provider failure:
Gemini reached the configured 16,384 generated-token limit.

This was not an oversized-image recurrence. The model received one 768 x 256 JPEG contact sheet
containing three 256-pixel views; its stored binary payload was about 13 KB. The truncated model
turn contained only 236 visible words. The remainder of the allowance was consumed by high-level
thinking while reconciling an oversized asset, display-name cleanup, and a separate lossy
simplification decision. The provider terminated before a typed `propose_agent_repair_plan` call.

**Decision**

Use Gemini `medium` reasoning by default for both intake and workflow evaluation. Continue to
accept explicit `high`, and map an explicit project `xhigh` request to Gemini `high`, so controlled
comparisons remain possible. Keep the 16,384 generated-token bound instead of paying for unbounded
reasoning.

Do not retry automatically. Preserve the completed measurements and rendered evidence, explain in
the Asset Shepherd conversation that the model reached its response limit and that no repair was
applied, then offer the existing explicit **Retry Shepherd** action. Hide raw provider diagnostics
and documentation URLs from the product surface. This retains the established bounded-recovery
contract and avoids an unrequested second billable model call.

**Evidence and consequences**

The exact workspace contains successful inspection and render tool results, no assessment, no
repair plan, no interrupt, and no candidate. Its browser camera-change path performs only local
overlay scheduling. Targeted tests cover the medium Gemini default, the explicit xhigh-to-high
path, the actionable sanitized response-limit message, and the hosted conversation surface.

The provider did not return a completed result object after `MAX_TOKENS`, so this run has no exact
usage ledger. The configured cap and short visible fragment nevertheless localize the failure to
generated thinking rather than request size. A manual retry is a fresh bounded planning pass from
the saved deterministic inspection.

### D097 — Keep target choices and the active 3D scene usable at narrow widths

**Date:** 2026-09-03

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 hosted conversation

**Context**

The destination cards were sized from the full browser viewport even when the persistent scene
column left only a narrow conversation lane. Four compressed engine cards became difficult to read,
and the use-case choice that controls mesh-complexity policy appeared only on the following target
review. Below the two-column breakpoint, the shared 3D scene was also placed outside the active
notebook turn, so the user could lose the visual context needed to answer the current question.
Finally, the selected viewing use froze a triangle cap but a below-budget no-op was visible only in
agent evidence, leaving users unable to tell whether simplification had been considered.

**Decision**

Collect the target engine and the single ordinary-language viewing-use choice together whenever the
endpoint needs clarification. Name the choices `Hero / close-up`, `Normal gameplay`, and
`Background / repeated`; retain the frozen caps of 50,000, 15,000, and 2,500 triangles. Let both
choice grids reflow from their own available width instead of relying on a full-window breakpoint.

Keep one shared interactive 3D scene. At desktop widths it remains in the resizable sticky evidence
column. At widths of 1,150 pixels or less, move that same scene into the currently active notebook
cell; scrolling changes both the active historical state and the scene's location. Do not create a
second viewer or duplicate WebGL state.

Always state the deterministic mesh-complexity outcome in the Topology action once viewing use is
confirmed: optimization proposed/applied/rejected, detail preserved because the source is under the
cap, optimization unavailable for an unsafe layout, or an over-budget case where the agent did not
propose it. This is presentation of frozen policy and measured facts, not new deterministic planning.

**Evidence and consequences**

Hosted acceptance covers the combined destination/use-case form, an explicit non-default choice,
the inline current-scene slot, and the visible normal-gameplay budget outcome. The saved radio run
now reports that its 4,327 triangles were preserved because they are within the confirmed
15,000-triangle soft cap. Static acceptance proves that the shared scene moves between the evidence
host and active notebook slot across the breakpoint. The responsive implementation preserves one
scene instance and all existing scroll-driven historical selection behavior.

The fixed-model endpoint returns HTTP 206/200 with `Content-Disposition: attachment` and the
expected filename. The Codex embedded browser requests that file but resets the connection instead
of presenting a save surface; that is a host-browser limitation, not a failed Asset Shepherd
package. Full Chrome, Edge, and the future deployed browser path remain the supported download
surfaces.

### D096 — Add Gemini 3.8 Flash as a native opt-in comparator

**Date:** 2026-09-03

**Status:** ACCEPTED for opt-in local evaluation; one live representative case passes

**Decision owner:** User and Codex

**Milestone:** M9 hosted conversation / M10 evaluation

**Context**

The user wants to compare Gemini 3.8 Flash against Asset Shepherd's proven Luna, Kimi, and Muse
runs. Gemini accepts standardized image evidence and tool use, and Strands has a native provider,
but Gemini is not hosted by Amazon Bedrock. This is therefore a development comparator rather than
a change to the AWS contest deployment.

**Decision**

Add `gemini` behind the existing provider-neutral intake and workflow boundaries. Permit only the
exact `gemini-3.8-flash` model ID. Use native Gemini JSON-schema output for semantic intake and the
native Strands Gemini model for the tool loop. Hoist rendered tool-result images into first-class
Gemini image parts so visual evidence is not serialized as opaque function-response JSON. Map the
project's `xhigh` convention to Gemini's supported `high` reasoning level.

Store the local API key with Windows current-user DPAPI, outside the repository. Expose
`GEMINI_API_KEY` only while the selected local server child process runs. Keep Gemini workspaces
separate from other provider runs. A production use would require a separate privacy, secret-store,
egress, billing, and architecture decision; it does not replace Kimi's accepted Bedrock path.

**Evidence and consequences**

The implementation includes native structured intake, native multimodal Strands tool transport,
fail-closed model and reasoning validation, provider-acceptance runner support, bounded provider
timeouts, and zero-network tests for configuration, screenshot transport, schema use, and DPAPI
launcher behavior. A live native structured-intake smoke identified a single Unreal riding-crop
prop and proposed plausible `4 x 65 x 4 cm` bounds.

The fixed `broken-normalization` case then passed safety, semantic, visual, approval, and packaging
checks. Gemini selected the required 100-fold scale reduction, +90-degree Z rotation,
footprint-center-bottom pivot, and safe display-name cleanup; deterministic verification confirmed
`1.22 x 1.82 x 0.40 m` final bounds and preserved the immutable source. The two-turn workflow used
307,454 input and 20,274 output tokens over 89.91 provider seconds. This is a promising one-case
sample, not the eight-case release gate, and it does not replace Kimi on Bedrock as the AWS
production candidate.

### D095 — Add Muse Spark 1.3 as an explicit Meta evaluation comparator

**Date:** 2026-09-02

**Status:** ACCEPTED for opt-in evaluation; not selected for AWS production

**Decision owner:** User and Codex

**Milestone:** M9 hosted conversation / M10 evaluation

**Context**

Meta released Muse Spark 1.3 with multimodal input, tool use, structured output, and a documented
OpenAI-compatible Responses endpoint. It is not an Amazon Bedrock model, but Strands can use a
custom OpenAI-compatible provider. The user wants a bounded comparison against the same Asset
Shepherd evidence and tool contract. For this local test, the user explicitly chose Meta's cheaper
Contributor model and accepted that Meta may use the evaluation inputs and outputs for model
improvement. That consent does not extend to production or to arbitrary user assets.

**Decision**

Add `meta` as an opt-in provider with the reviewed endpoint `https://api.meta.ai/v1`. Permit only
`muse-spark-1.3` by default. Permit `muse-spark-1.3-contributor` only when the exact model ID is paired
with `ASSET_SHEPHERD_ALLOW_META_TRAINING=1`; otherwise fail closed. Keep the Meta key in the same
Windows current-user DPAPI pattern as the OpenAI development key and expose it only to the launched
child process. Normalize requested `xhigh` to Meta's effective `high` maximum. Move standardized
render images into user messages at the provider boundary because Meta accepts image blocks there,
not inside tool-output messages.

Use the Contributor endpoint only for explicitly designated local evaluation assets. If Meta is
ever selected for production, use `muse-spark-1.3` without the training flag, place the credential
in an approved secret store, and separately approve outbound AgentCore networking and the resulting
non-Bedrock architecture. D094 remains controlling: Kimi K2.5 over Bedrock Converse is still the
current AWS production candidate, and Muse has not passed the full eight-case release gate.

**Evidence and consequences**

Three live Contributor/high cases completed through the unchanged Strands tools and deterministic
verification:

| Case | Result | Input / output tokens | Provider time | Approx. Contributor cost |
|---|---|---:|---:|---:|
| Clean control | Passed; no repair required | 323,527 / 4,092 | 119.57 s | $0.0332 |
| Riding-crop component selection | Passed; kept the intended center component and removed the two extras | 139,300 / 4,058 | 120.81 s | $0.0147 |
| Robot-dog component preservation | Passed; preserved all five intentional forms while scaling and renaming | 149,124 / 6,153 | 175.51 s | $0.0161 |

The sample totals 611,951 input and 14,303 output tokens over 415.88 provider seconds, approximately
$0.0641 at the user-selected Contributor rates of $0.10/M input and $0.20/M output. It demonstrates
basic multimodal and tool-contract compatibility, including both component removal and intentional
component preservation. It does not establish an eight-case pass, a general quality advantage, or
a production privacy decision.

### D094 — Gate production models on one resumable eight-case acceptance set

**Date:** 2026-09-02

**Status:** ACCEPTED; Kimi K2.5 passes, Mistral Large 3 is rejected as the default

**Decision owner:** User and Codex

**Milestone:** M9 hosted conversation / M10 evaluation

**Context**

Model-card feature lists do not establish whether a multimodal model will preserve intentional
parts, choose supported repairs, honor approval, interpret standardized renders, or recover from a
tool error. Replaying every paid case in one long process also proved operationally unsafe: one
Bedrock read remained open for roughly seven hours because the SDK inherited a very long socket
timeout. The product needs a small, repeatable, provider-neutral behavioral gate with measured
tokens and bounded failures.

**Decision**

Use the frozen eight-case matrix in `validation/provider-acceptance/cases.json`. Require 8/8 safety
and at least 7/8 semantic/visual passes. Hash every source, reject any action outside the case
allowlist before approval, forbid position-only welding globally, require exactly one interrupt for
consequential work, re-hash the immutable source afterward, and require positive candidate visual
reassessment where appearance changes. Run cases individually or in small batches; aggregate only
compatible passing records whose provider, model, case, and source hash match. A later failure never
erases an earlier pass. Bedrock reads default to a five-minute timeout with no SDK retry; callers may
configure a bounded 30–900 second value.

Select `moonshotai.kimi-k2.5` over Bedrock Converse as the current AWS production candidate. Keep
direct OpenAI Luna/xhigh as the proven local-development baseline and evaluate Bedrock Luna only
when its account agreement becomes invokable. Do not use Mistral Large 3 as the default: it failed
the riding-crop visual/component case and proposed destructive component removal for the coherent
65-part collar, so it cannot reach the 7/8 semantic threshold.

**Evidence and consequences**

Kimi passes all eight cases: clean no-op, broken normalization, proven degenerate cleanup,
Patchling preservation, Shader Lantern normalization, riding-crop component selection, robot-dog
component preservation, and shattered-heart collar simplification. The aggregate ledger records
1,007,046 input tokens, 14,277 output tokens, 1,021,323 total tokens, and 366.86 seconds of provider
invocation time. At the current standard `us-east-1` Kimi rates of $0.60/M input and $3.00/M output,
that selected passing set is approximately $0.65 before any taxes or account credits. The aggregate
is reproducible with `scripts/summarize_provider_acceptance.py`; large evidence and private GLBs
remain local while the manifest, runner, and scoring rules are tracked.

One riding-crop rerun exposed a renderer-gate false negative rather than a model error: a valid
edge-on crop occupied about 0.5% of pixels while spanning 26% of the frame. The absolute visibility
floor is now 0.1%, with the independent 8% projected-span and clipping checks retained. A regression
test proves that a long slender silhouette passes while a blank mask still fails.

### D093 — Host the web tier on ECS Express Mode beside IAM-controlled AgentCore

**Date:** 2026-09-02

**Status:** ACCEPTED; supersedes D075, implementation and remote acceptance remain open

**Decision owner:** User and Codex

**Milestone:** M9 hosted Bedrock conversation and deployment

**Context**

D075 selected App Runner before AWS announced that App Runner is closed to new customers. AWS now
recommends ECS Express Mode, which provisions an ECS/Fargate service, Application Load Balancer,
auto scaling, and networking from one service definition. The product still needs a public web
process distinct from the private Strands runtime, and neither disposable compute layer may become
the state authority.

**Decision**

Deploy one stateless FastAPI/Jinja container from private ECR through ECS Express Mode. Treat its
managed HTTPS endpoint, Application Load Balancer, TLS, health checks, Fargate service, autoscaling,
and networking as one deployment abstraction rather than separately designed infrastructure. It
owns HTTPS routes, authentication, gallery authorization, presigned exact-object transfer, and
service-to-service invocation. Deploy the Strands workflow and deterministic GLB tools in an
IAM-controlled AgentCore Runtime only after the ARM64/Chromium compatibility spike passes. Keep
immutable GLBs, evidence, packages, and Strands snapshots in private workspace-scoped S3 prefixes.
Keep the current workspace pointer, iteration lineage, approval/command receipts, and optimistic
version in DynamoDB.

Persist an artifact to S3 and verify its hash before conditionally advancing the DynamoDB pointer.
Key every consequential command by a stable action hash so retries return the existing receipt
instead of mutating twice. The web tier submits a command and returns `202 Accepted`; the notebook
polls typed status while AgentCore runs. Browser clients never receive AWS credentials and never
invoke the runtime directly. D105 refines the call path: the web task queues the typed command and a
least-privilege Lambda dispatcher calls the normal regional `InvokeAgentRuntime` API. PrivateLink
and custom AgentCore VPC connectivity are deferred unless a later
requirement justifies them. Route 53 and a custom domain are optional polish rather than contest
dependencies. Preserve the local Uvicorn/offline configuration as the same
product with local storage/runtime adapters.

**Evidence and consequences**

AWS's App Runner availability notice explicitly recommends ECS Express Mode for new deployments.
No ECS, ECR, S3, DynamoDB, or AgentCore resources have been created by this decision. The next
deployment gates remain cloud-portable state, a clean Linux Chromium render, the AgentCore
ARM64/port-8080 protocol spike, then remote browser acceptance. Stop before any architecture choice
expected to exceed the documented development-cost checkpoint.

### D092 — Ask about viewing use and offer one controlled mesh optimization

**Date:** 2026-09-02

**Status:** ACCEPTED; deterministic, direct-Luna, and Bedrock-Kimi gates complete

**Decision owner:** User and Codex

**Milestone:** M9 hosted conversation / M10 evaluation

**Context**

The 30.2 MB shattered-heart collar contains 783,571 triangles. File size alone is not a safe proxy
for mesh complexity because embedded textures may dominate, and ordinary users should not need to
choose a decimation percentage. The previously suggested 200k/75k/25k budgets were also too high
for the intended game-asset workflow. Any lossy operation must remain explicit, reversible, and
independently verified rather than becoming an eager import optimization.

**Decision**

Ask one global product question at target confirmation: how closely the asset will normally be
viewed. Close-up/showcase maps to a 50,000-triangle soft cap, normal gameplay defaults to 15,000,
and small/distant/repeated maps to 2,500. Do not expose these counts as input choices. When measured
geometry exceeds the frozen cap and a supported layout is proven, the agent normally proposes one
separate `SIMPLIFY_MESH` action. The user may reject it and retain the original detail.

Use pinned local `meshoptimizer` simplification separately on each exact source component. Preserve
complete source attribute tuples, material assignment, UVs, normals, named nodes, and every
component below 1,000 triangles. Refuse skinning, morph targets, compression, sparse/shared/extended
accessor layouts, malformed indices, or pending degenerate cleanup. Allow at most two-percent bounds
drift, preserve the bounded near-contact component grouping, reload and validate independently, and
require fresh visual comparison. Report actual output triangles and bytes. Stop above the soft cap
when preservation constraints bind rather than degrading blindly.

**Evidence and consequences**

The deterministic synthetic sphere gate reduces a 20,480-triangle source toward the 15,000 normal-
gameplay cap, preserves its immutable source and required resources, and passes independent
verification. Rejecting the same proposal returns the exact source bytes. On the real 783,571-
triangle collar, the conservative normal-gameplay pass reaches 56,885 triangles and reduces
30,204,480 bytes to 7,709,808 while retaining 3,611 triangles across 63 small protected components.
It honestly remains above 15,000 because attribute and component-preservation limits bind. The full
offline suite passes with 218 tests and two intentional live-provider skips.

Direct OpenAI Luna xhigh then evaluated the isolated feature on the already normalized collar. It
correctly preserved the intentional component assembly, proposed only `simplify-mesh-v1`, and after
approval produced a verified 56,885-triangle, 7,710,004-byte candidate from the 30,204,752-byte
normalized input. Its complete ledger records 376,106 tokens and 123.75 seconds, including bounded
recovery after an early provider end-turn. That recovery exposed a shared-scale renderer bug: two
similarly sized models could hit opposite frame edges because `<model-viewer>` clamped the requested
orbit against only its primary model. Comparison rendering now expands the orbit limit after load,
adds comparison-specific framing headroom, and has a real-browser non-clipping regression test.
After interactive AWS reauthentication, Bedrock Converse/Kimi K2.5 independently proposed the same
single simplification while preserving the intentional construction. It produced the byte-identical
candidate in 94.96 seconds using 159,666 recorded tokens, with no post-approval recovery. That is
23% less observed time and 58% fewer recorded tokens than this Luna run, but it is not a controlled
general model ranking because Luna's total includes the recovery path. The provider-neutral action
contract and deterministic mutation therefore pass on both requested live providers.

### D091 — Use the existing web GLB stack for model-visible evidence

**Date:** 2026-09-01

**Status:** ACCEPTED; local renderer gate complete, Linux container gate open

**Decision owner:** User and Codex

**Milestone:** M9 hosted Bedrock conversation and deployment

**Context**

The interactive viewport already uses a pinned local `<model-viewer>` 4.3.1 distribution built on
Three.js, but the agent's standardized source, candidate, and shared-scale screenshots still invoked
a workstation Blender executable. Shipping Blender inside the first AWS runtime would materially
increase image size, cold start, architecture constraints, and operational complexity. The visual
contract itself only requires four fixed glTF-axis views, true shared scale, masks, material-visible
captures, and deterministic framing checks; it does not require a DCC application.

**Decision**

Use the vendored `<model-viewer>` distribution through a discovered headless Chromium-family
browser as the default evidence backend. Serve only the trusted job inputs and renderer bundle from
an ephemeral loopback HTTP server. Compute world bounds and comparison offset deterministically in
Python, fix a 24-degree camera and four source-axis azimuths, capture transparent 512 px PNGs through
`model-viewer.toBlob()`, derive L-mode masks from alpha, and composite the existing dark audit
frames. Retain the existing mask/framing validator as the acceptance authority.

Discover Chromium from `ASSET_SHEPHERD_CHROMIUM_PATH`, normal command lookup, or known desktop
locations. Keep Blender behind the explicit `ASSET_SHEPHERD_EVIDENCE_RENDERER=blender`
compatibility setting; never silently fall back to it in production. The next AWS image packages
Chromium and must pass the clean-Linux reproducibility and cold-start gate before Step 4 completes.

**Evidence and consequences**

The real clean-robot fixture produced four correctly oriented, textured 512 px PNGs and alpha masks
that passed every existing nonblank, occupancy, span, clipping, and clear-margin check. A
clean-versus-broken comparison retained the true shared scale: the 182 m candidate dominated its
1.8 m reference rather than receiving an independent fit. The 30.2 MB, 783,571-triangle
shattered-heart collar also produced four validated textured views in one local browser invocation,
with roughly 28–30% foreground occupancy and clear margins. Renderer regression coverage exercises
browser discovery and a real four-view capture when Chromium is present. The common gate passes with
213 tests, two opt-in live skips, lock validation, Ruff, formatting, JavaScript syntax validation,
and zero Pyright findings.

This closes the workstation-Blender implementation gap, not the AWS portability gate. Docker is not
installed on the current workstation, so the clean Linux container, packaged-browser size,
cold-start, ARM64-versus-x86 choice, and repeatability measurements remain required. Independent
Blender and Unreal imports remain useful consumer-validation evidence and are not part of the hosted
rendering dependency.

### D090 — Preserve every Shepherd invocation and benchmark ambiguous component cleanup

**Date:** 2026-09-01

**Status:** ACCEPTED; Kimi and direct-Luna comparison complete

**Decision owner:** User and Codex

**Milestone:** M9 hosted conversation / M10 evaluation

**Context**

The 30.2 MB Meshy shattered-heart collar is visually coherent but measures approximately
1.90 × 0.62 × 1.88 m instead of the confirmed 15 × 3 × 12 cm target. Its one indexed primitive
contains 783,571 triangles and presents 65 exact disconnected components, while all 65 belong to one
scale-relative near-contact group. Kimi K2.5 classified 64 tiny components as removable debris. The
approved mutation removed 20,630 triangles, but fresh verification found 12 exact bodies rather
than the planned one and correctly reported **Attempted — verification did not confirm**. The user
then requested the missing scale correction; the second turn succeeded. Before this checkpoint,
Strands metrics were written only when a whole interrupted workflow completed, so the saved Kimi
artifacts retained the two resumed invocations but lost both pre-approval calls. The refinement text
also did not appear in the notebook until the synchronous model turn returned.

**Decision**

Use this exact hash as a provider-comparison benchmark, separate from the rights-confirmed canonical
Tripo corpus. Track its metadata, target, chronology, model outcomes, and metric scope. Keep the raw
GLB and screenshots locally under ignored directories until public-use rights are explicitly
confirmed.

After each completed Shepherd provider call, atomically write `output/agent_invocations.json` before
an approval interrupt or server reconstruction can discard duration, token usage, or tool totals.
Treat Strands metrics as cumulative within one agent instance and record invocation deltas. Aggregate
the durable ledger into the final `agent_result.json`. This ledger covers Shepherd calls; semantic
target-intake usage remains a separately acknowledged gap.

When an active approval or refinement form submits, immediately append the user's selected decision
or exact feedback as a pending right-side conversation turn before showing the working cell. The
server response remains authoritative and replaces this optimistic DOM-only copy on reload.

**Evidence and consequences**

The original Kimi run was slow but effective after refinement: its retained 257,998 tokens are only
a lower bound, and its two retained resumed calls took 167.25 seconds. Direct OpenAI Luna xhigh
preserved the visually coherent 65-part near-contact assembly, declined welding 81,091 protected UV
seams, and produced a verified proportional fit in one repair turn. Its two exactly recorded
Shepherd calls took 161.74 seconds and used 412,929 tokens; intake is excluded. Both final candidates
measure 11.84 × 3.89 × 11.73 cm and are grounded at Y=0. Luna is faster and more conservative here,
but it required the dimensions to be stated explicitly after an incorrect first intake estimate.
These are case results, not a general provider ranking.

Regression coverage verifies a two-invocation ledger whose aggregate equals final metrics and the
three conversation forms that append pending user turns. The benchmark runbook records the partial
Kimi verification, delayed-feedback observation, successful refinement, Luna comparison, and honest
token scopes. The common gate passes with 211 tests, two opt-in live skips, lock validation, Ruff,
formatting, JavaScript syntax validation, valid benchmark JSON, and zero Pyright findings.

### D089 — Bound model-facing render evidence and consume executed approvals

**Date:** 2026-09-01

**Status:** ACCEPTED; exact interrupted Kimi workspace recovered

**Decision owner:** User and Codex

**Milestone:** M9 hosted Bedrock conversation and deployment

**Context**

The bus-sized robot-dog workspace `5919c759657048248bfd8db56968c5b4` accepted its proposed
uniform resize and deterministic name cleanup. The candidate was written correctly, but the resumed
Kimi K2.5 turn stopped after rendering candidate evidence and before recording visual reassessment
or calling verification. The request history contained four source views, four isolated candidate
views, and four shared-scale views as separate full-resolution PNG image blocks. Kimi K2.5's
[Bedrock model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-moonshot-ai-kimi-k2-5.html)
documents a 3 MB maximum image payload; the twelve PNGs exceeded that provider boundary. The UI
then described the executed repair as an unsuccessful attempt and kept the already-consumed approval
clickable, so pressing it again appeared to loop.

**Decision**

Continue rendering and retaining every full-resolution PNG as local audit evidence, UI evidence,
and package evidence. For model input only, combine the first three coordinate-labeled views of each
stage into one left-to-right contact sheet: source, isolated candidate, and shared-scale comparison.
Each sheet uses 256-pixel tiles and JPEG quality 88. A complete action cycle therefore contributes
three compact image blocks rather than twelve full-resolution PNG blocks. This transport reduction
is provider-neutral and does not weaken the immutable evidence record.

Once a resume call has durably produced a repair outcome, any later provider exception consumes the
pending approval. On restart, an older executed job with no candidate reassessment or verification
is migrated to the same bounded recovery boundary. The page must say **Applied — verification has
not completed**, remove **Apply recommendations**, and offer **Finish this iteration**. Recovery may
render and assess the existing candidate and then run deterministic verification/package; it may
not execute the repair again.

**Evidence and consequences**

Regression coverage verifies a 768 × 256 three-view JPEG sheet without modifying its four source
PNGs, a provider failure immediately after durable execution, stale pre-fix restart migration, and
distinct interrupted-versus-failed after-action presentation. The exact robot-dog workspace restored
with its stale interrupt cleared, completed its Kimi visual reassessment using the bounded evidence,
and passed deterministic verification with zero failed checks. Its candidate is ready at
3.50781 × 3.44959 × 7.43772 m, the approved proportional uniform fit to the approximate
2.5 × 3 × 12 m box. Names are verified; the only remaining warning records five intentional
disconnected forms. The common gate passes with 211 tests, two opt-in live skips, lock validation,
Ruff, formatting, JavaScript syntax validation, and zero Pyright findings.

### D088 — The agent proposes approximate target size from ordinary scale clues

**Date:** 2026-09-01

**Status:** ACCEPTED; provider-neutral bounded retry implemented

**Decision owner:** User and Codex

**Milestone:** M9 hosted Bedrock conversation and deployment

**Context**

A Kimi intake correctly recognized a quadrupedal robot dog and its static-game-asset use, but treated
“about the size of a bus” as insufficient for a confidence-gated target box. The target turn then
showed mandatory X/Y/Z inputs beside the genuinely missing engine choice. Although three-axis target
dimensions have been part of the frozen contract since D045, this presentation incorrectly shifted
estimation work from Asset Shepherd to the user and made the existing concept look like a new exact
requirement.

**Decision**

For every recognizable asset, the intake agent proposes approximate final-pose X/Y/Z bounds. Common
relative clues such as bus-sized, person-sized, handheld, tabletop, and building-sized are enough to
make a proposal that the user may confirm or revise. Confidence represents whether the estimate is
useful to present, not whether the object's real-world size is known exactly. Check plausible
proportions and unit conversion before submission.

If an otherwise confidence-gated target omits or suppresses dimensions, every network adapter may
make exactly one focused retry asking for its best approximate proposal. This retry does not apply to
unrecognizable or refused content, and it adds no unbounded conversation loop. The manual fallback
remains available after a repeated failure or genuine ambiguity, but its interface says
**Approximate target size**, not **Tight target bounds**. Repairs continue to use D050's single
proportional best fit; this decision does not authorize non-uniform scaling.

**Evidence and consequences**

A provider-neutral Converse regression starts with a recognizable bus-sized robot dog whose first
tool submission omits dimensions, asserts one strengthened retry, and ends with only the endpoint
missing. A live Bedrock/Kimi call for the exact reported description proposed 250 × 300 × 1,200 cm,
with the endpoint still correctly left for the user. The common gate passes with 207 tests, two
opt-in live skips, lock validation, Ruff, formatting, JavaScript syntax validation, and zero Pyright
findings. A misbehaving model can cost one additional intake call, but only on this narrow omission.

### D087 — End accepted workflows with an explicit gallery return

**Date:** 2026-09-01

**Status:** ACCEPTED; terminal gallery action and original animation implemented

**Decision owner:** User and Codex

**Milestone:** M9 hosted Bedrock conversation and deployment

**Context**

The accepted Download cell provided the model and evidence downloads but no local closing action.
Gallery remained available in persistent chrome, yet completing the chronological notebook did not
visually explain how to leave that asset and choose another one.

**Decision**

End every accepted Download cell with one explicit **Return to gallery** link. Pair the label with a
carriage-return mark and a new local four-frame Patchling sprite that runs right into a cream/mint
dust cloud. Animate only on hover or keyboard focus so the terminal cell remains calm while reading;
hold its first frame for reduced-motion preference. Navigation must not modify, rewind, or duplicate
the already durable accepted workspace. Reconstruct an accepted terminal result from deterministic
artifacts without loading its historical live-model session: viewing and downloading finished work
must not depend on the currently configured provider or the continued validity of an old Strands
snapshot.

**Evidence and consequences**

Hosted-route acceptance verifies the terminal label, carriage-return mark, sprite markup, gallery
destination, PNG payload, provider-neutral accepted-workspace reload, model download, and evidence
package. Static CSS acceptance verifies the local sheet, four frame positions, and reduced-motion
override. Browser acceptance on the completed Rugged Tablet workspace verifies the layout, active
hover frame, carriage-return mark, and successful gallery navigation. The generated project-bound
asset is `asset-shepherd-run-away.png`; the original image-generation prompt used the existing
thinking sprite solely as the mascot/style reference.

### D086 — Explain target engines in terms of operational consequences

**Date:** 2026-08-31

**Status:** ACCEPTED; contextual target help implemented

**Decision owner:** User and Codex

**Milestone:** M9 hosted Bedrock conversation and deployment

**Context**

When intake could not infer an endpoint, the target-selection turn offered Unity, Unreal, Godot, and
Other with terse axis tooltips. It did not explain why Asset Shepherd asks or what the choice changes,
so a user could reasonably mistake the choice for a proprietary-format conversion request.

**Decision**

Place a compact question-mark control beside **Select target engine.** It opens a modal that leads
with the shared operational effect: output remains GLB, while the chosen consumer frame and import
conventions guide judgments about orientation, scale, grounding, pivot placement, naming, and
handoff risks. Explain the Unity, Unreal, Godot, and described-Other paths individually. Explicitly
state that selecting an endpoint does not expand Asset Shepherd into rigging, animation, retopology,
or proprietary-format conversion.

**Evidence and consequences**

Hosted-route acceptance verifies the control, dialog, operational copy, all four choices, and scope
boundary. Browser acceptance verifies modal layout, close behavior, and preservation of the target
radio controls beneath it.

### D085 — Acknowledge synchronous model work with the original Patchling mascot

**Date:** 2026-08-31

**Status:** ACCEPTED; immediate Describe feedback and shared branded animation implemented

**Decision owner:** User and Codex

**Milestone:** M9 hosted Bedrock conversation and deployment

**Context**

Submitting the Describe form performs a synchronous model-backed target proposal. The browser
disabled and hid the form while waiting, but because that route has no separately pollable activity
ledger, it appended no working state. A healthy request therefore looked hung until the response
page arrived. Other agent turns used a rotating dashed circle that conveyed activity but no Asset
Shepherd identity, while the navigation still displayed a literal `LOGO` placeholder. The
temporarily peeked navigation also kept showing its hide chevron even though moving the pointer away
would already hide it.

**Decision**

Every busy form that can wait without an activity endpoint may supply a concise explanation of the
pause. Describe immediately appends an Asset Shepherd message saying that it is reading the
description and drafting a target, locks the completed input cell, and leaves the resulting working
message as the sole active cell until navigation completes. Pollable Shepherd and Refine work keep
their bounded tool labels.

Replace the generic active dashed circle with an original four-frame Patchling thinking sprite and
use a still first frame from the same sheet as the persistent workspace-header brand mark, immediately
left of the page title. It does not move with the collapsible navigation. The sprite is a locally
served transparent PNG with no third-party marks; CSS selects frames so there is no animation runtime
or remote dependency. Respect reduced-motion preferences by holding the first frame. Completed and
failed activity states retain their explicit check and exclamation symbols.

When the collapsed navigation is only being previewed from the desktop edge, replace its left-pointing
hide chevron with the same compact control pointing right. Clicking it makes the rail persistent
again; the persistent state returns to the left-pointing hide chevron. No text label is displayed.

**Evidence and consequences**

Static-route acceptance verifies the sprite payload, Describe busy explanation, working-message
construction, shared active-state treatment, logo markup, pin-state markup, and
reduced-motion-compatible CSS. Browser acceptance verifies the rendered mascot, edge-preview pinning,
and ordinary collapse after pinning; route/script acceptance verifies that synchronous Describe
submission constructs the transient message before navigation.

### D084 — Make workspace chrome adjustable without sacrificing the conversation

**Date:** 2026-08-31

**Status:** ACCEPTED; resizable evidence column and collapsible navigation implemented

**Decision owner:** User and Codex

**Milestone:** M9 hosted Bedrock conversation and deployment

**Context**

The conversation notebook and its single sticky 3D scene serve different reading tasks. Some assets
need a larger viewport for visual inspection, while long agent reports need more text width. The
persistent workflow rail also consumed useful space after it had supplied enough orientation.
Neither region should have one permanently fixed desktop width, and a hover-only recovery control
would make a collapsed rail inaccessible on touch devices.

**Decision**

On the side-by-side desktop layout, place a narrow draggable separator between the conversation and
the 3D evidence. The evidence region may grow from 300 px to the lesser of 880 px or the width that
still leaves 500 px for the conversation. Persist the chosen width locally, clamp it again when the
window changes, support Left/Right/Home/End keyboard operation, and reset to the responsive default
on double-click. At narrower breakpoints the scene remains a full-width notebook region and the
separator disappears.

Let the user collapse the left navigation persistently. A fine-pointer desktop exposes a small
double-line edge target and temporarily peeks the rail while the pointer is near the left edge;
clicking pins it open. A coarse-pointer/touch device replaces that hover affordance with an explicit
right-arrow control that can be tapped. Keep prior notebook navigation and active-turn rules
unchanged: resizing or hiding chrome never changes workflow state.

**Evidence and consequences**

The static web contract covers both templates, both persisted preferences, drag and keyboard
handling, the desktop edge indicator, and the touch restore control. Browser acceptance covers the
live Giant Aria workspace's collapse, expanded notebook width, edge-peek, and pinned restore. The
layout preference remains browser-local presentation state and never enters the workspace or agent
prompt.

### D083 — Make notebook history read-only and require explicit path-dependent rewind

**Date:** 2026-08-30

**Status:** ACCEPTED; active-turn lock, upstream rewind, and durable comparison implemented

**Decision owner:** User and Codex

**Milestone:** M9 hosted Bedrock conversation and deployment

**Context**

An append-only notebook made prior context visible, but its earlier Upload and Describe controls
still looked like ordinary active inputs while a later agent turn was running. That allowed
out-of-turn interaction without explaining that changing an upstream input invalidates every
dependent target and repair decision. A completed repaired model could also lose its combined
before/after viewport after runtime reconstruction because the comparison was gated on transient
in-memory execution state.

**Decision**

Exactly one notebook turn is active. Completed cells are readable history and expose no ordinary
input. Upload and Describe instead expose a deliberate **Rewind…** disclosure which explains the
dependency consequence before staging a replacement. The saved workspace remains intact until the
replacement validates; a valid upstream revision starts a new target and repair path rather than
editing downstream history in place. Historical Shepherd and Refine turns remain immutable model
states; the active result's **Refine…** action is the supported way to promote its input or candidate
into a new iteration.

As soon as an active command is submitted, every prior notebook cell becomes inert and its action
surface disappears while the appended working cell owns the turn. Scrolling remains available for
context, but no prior form, link, disclosure, or button can race the in-flight command. An accepted
Shepherd/Refine cell becomes complete and the appended Download cell becomes the sole current cell.

Build completed before/after scenes from the durable packaged candidate whenever one exists, even
when the reconstructed runtime no longer contains its transient execution outcome. A route arriving
at `#current-turn` preserves that server-rendered comparison until the user actually scrolls; scroll
proximity may then select an earlier immutable scene.

**Evidence and consequences**

The saved Bipedal Woman workspace `147bb61536204af0aa852aa460e9412d` reconstructs after a clean
server restart with **Uploaded model and Candidate**, source plus repaired GLB URLs, two explicit
**Rewind…** boundaries, and exactly one current Download cell. Focused hosted/runtime and web visual
contract tests cover a ready candidate whose transient outcome is absent, the rewind labels, the
inert active-turn lock, and current-scene bootstrap behavior. The common gate passes with 206 tests,
two opt-in live skips, lock validation, Ruff, formatting, JavaScript syntax validation, and zero
Pyright findings.

### D082 — Present the notebook as a typed conversation with contextual actions

**Date:** 2026-08-30

**Status:** ACCEPTED; conversation layout, evidence sidebar, and action routing implemented

**Decision owner:** User and Codex

**Milestone:** M9 hosted Bedrock conversation and deployment

**Context**

The full-lifecycle notebook preserved history, but its wide cells still read like stacked forms.
The 3D scene occupied whichever notebook cell was active, the approval composer was always visible,
and generic Yes/No or submit controls forced the user to translate the current workflow state into
the right kind of response. This obscured the distinction between an immediate transition and a
turn that actually needs new user context.

**Decision**

Render the notebook as a conversation: user messages align right, Asset Shepherd messages align
left, and inspection results remain attached to the relevant Shepherd turn. Keep one live 3D scene
in a sticky right evidence column; scrolling changes the immutable iteration displayed there but
never moves or duplicates the renderer. Collapse the evidence column above the transcript when the
available width cannot support both readable regions.

Expose only context-dependent next actions. Target confirmation offers **Start shepherding** or
**Change target…**. A pending plan offers **Apply recommendations**, structured Keep/Remove choices,
**Add comment…**, and **Download current**; the comment area is absent until requested. A completed
iteration offers **Use this version**, **Refine…**, and the relevant download. Immediate transitions
do not invent a freeform feedback turn: target confirmation starts the initial agent workflow from
the confirmed contract, while accepting or downloading invokes no model. Feedback actions produce
typed `PLAN_REVISION` or `RESULT_REFINEMENT` envelopes; prompt v15 tells the agent how to reconcile
each envelope, select tools, preserve the chosen immutable input, request fresh approval, or stop
honestly when unsupported.

**Evidence and consequences**

Browser acceptance on saved workspace `49384ee553284bd4b5bfc9bdc3b79bdd` shows Upload, Describe, and
Shepherd as alternating left/right messages with one sticky labeled-component scene. The inspection
attachment uses a readable stacked lane layout at narrower desktop widths. **Add comment…** reveals
one multi-row composer and changes the primary action to **Send feedback**; unchanged structured
defaults remain one-click **Apply recommendations**. Focused prompt, hosted-route, script, and visual
contract tests pass. The common gate passes with 206 tests, two opt-in live skips, lock validation,
Ruff, formatting, JavaScript syntax validation, and zero Pyright findings. This supersedes D079's
always-visible wide composer and movable scene host without changing its atomic feedback,
authorization, or immutable-history rules.

### D081 — Make the entire asset lifecycle one editable, append-only notebook

**Date:** 2026-08-30

**Status:** ACCEPTED; full-lifecycle notebook implemented

**Decision owner:** User and Codex

**Milestone:** M9 hosted Bedrock conversation and deployment

**Context**

The shared-scene notebook originally began at Shepherd. Moving from Upload to Describe replaced the
upload screen, and confirming the target replaced Describe with Shepherd. This still made the
workflow feel like a page wizard and hid the evidence and choices that produced the current model.

**Decision**

Represent one asset's complete lifecycle as one chronological notebook: Upload, Describe and target
confirmation, Shepherd, every Refine iteration, and the final Download outcome. Persisted state is
reconstructed as cells in that order; advancing appends below instead of replacing earlier cells.
Upload and Describe remain editable. Editing an earlier cell stages replacement input while keeping
the saved workspace intact until the replacement validates, then starts the dependent work again
from that point. Later results are never silently reused after an upstream edit.

Keep the existing workflow outline as navigation into the notebook, not as a second copy of its
content. Preserve one live 3D renderer: the scene nearest the viewport center owns it and the other
cells retain lazy placeholders. Acceptance appends a Download cell without reloading the page.

**Evidence and consequences**

The saved multi-turn workspace `4bb293f48f86476a9ae08fdadee4fb1b` renders Upload, Describe,
Shepherd, and Refine 4.1 in order with the confirmed target and prior decisions retained, three scene
slots, and exactly one live `<model-viewer>`. Route tests cover Upload-to-Describe persistence,
chronological ordering through completion, a separate Download cell, invalid replacement rollback,
valid replacement promotion, and the lazy source-scene route.

### D080 — Preserve the whole notebook and finish invariant-only work after provider end-turn

**Date:** 2026-08-30

**Status:** ACCEPTED; append-only presentation and bounded completion recovery implemented

**Decision owner:** User and Codex

**Milestone:** M9 hosted Bedrock conversation and deployment

**Context**

The first shared-scene notebook kept one live 3D viewer, but the current proposal was still replaced
by its result after approval. That concealed the actual exchange instead of letting the user read the
description, recommendation, decision, and resulting model state in order. During a successful Kimi
K2.5 riding-crop run, the provider recorded a positive candidate reassessment and said it was ready
to verify and package, then ended the response before calling the final tool. The repair and visual
judgment were complete, but the product reported that the agent ended early and withheld the valid
candidate.

**Decision**

Render the workspace as an append-only chronological notebook. Keep the intake description and each
turn's agent proposal, explicit user decision, agent outcome, saved 3D state, and continuation comment
visible in scroll order. Append the current decision and outcome below its proposal instead of
replacing earlier content. Workflow-rail navigation scrolls to these entries, and the existing single
shared viewer moves to the scene closest to the viewport center; the page never keeps multiple live
3D scenes.

Treat independent verification and packaging as mandatory invariant work once the agent has already
selected and executed the authorized action and, for every visually consequential mutation, recorded
the required candidate reassessment. If a model provider ends precisely at that final boundary,
deterministic code may run `verify_and_package` without another model call. The recovery is fail-closed:
it cannot select, authorize, execute, revise, or visually approve a repair, and it does not run while
an interrupt or required reassessment is missing. The same rule applies when reopening a persisted
workspace so a transient provider end-turn does not strand a completed candidate.

**Evidence and consequences**

The exact Kimi workspace `91b21e479f914f80888c266d473b06d4` contained a valid component-removal
candidate, positive four-view reassessment, hashes, decisions, and provenance but no package. Reloading
under the bounded rule independently verified it, produced the result and verification artifacts, and
changed the failed presentation into a downloadable completed turn without another inference or model
mutation. Browser acceptance on that workspace shows proposal, approval, outcome, and one live current
scene together. A saved two-iteration riding-crop conversation shows all prior exchanges and both scene
slots in order while keeping exactly one `<model-viewer>`; rail navigation activates the requested
iteration. Tests cover the visual-reassessment boundary and notebook structure. This decision does not
weaken the agent's authority over sensing, disposition, action choice, or visual judgment.

### D079 — Make each approval exchange one chronological, atomic user turn

**Date:** 2026-08-29

**Status:** ACCEPTED; approval and shared-scene notebook implemented

**Decision owner:** User and Codex

**Milestone:** M9 hosted Bedrock conversation and deployment

**Context**

The approval page exposed separate comments inside repair lanes, component selectors only when the
agent had already proposed removal, and an overall approval button elsewhere. In workspace
`310d83ab86214295a730395c165f1de4`, deterministic inspection found three exact safely selectable
components, but the agent reasonably interpreted them as three intentional parts of one riding
crop. Because the component controls were suppressed, the human could not directly override that
semantic judgment and had to discover an unrelated feedback affordance.

The user selected a notebook-like interaction model: chronological agent and user turns, one place
for user prose, structured choices submitted with that prose, one active 3D scene, and a workflow
rail that navigates history rather than duplicating controls.

**Decision**

Treat every approval exchange as one atomic turn. Always expose exact Keep/Remove controls when
deterministic diagnostics prove disconnected-component removal is safe, including when the agent's
default is Keep. Preserve the agent's recommendation as the selected default; do not automatically
infer that multiple components are unwanted. Combine all structured lane/component choices and one
optional whole-turn comment into one typed interrupt response. Any changed choice or non-empty
comment archives the proposal without mutation and resumes the same workspace-scoped agent for a
fresh plan and fresh approval.

Use one wide turn composer and one dynamic primary action: **Apply recommendations** when the
structured defaults are unchanged and no prose is present, otherwise **Send revision**. Offer
**Download this version** as the human override that does not authorize pending recommendations.
Remove per-row comment boxes. Render completed turns in order, keep only one live model scene, and
make rail entries scroll targets. Each archived turn resolves its displayed GLB by the immutable
`output_sha256` in `conversation.json`; a missing or mismatched asset fails closed. As the user
scrolls, the scene slot nearest the viewport center receives the one shared scene host. Historical
scene markup loads only when needed and leaves the live DOM when another turn takes over.

**Evidence and consequences**

Prompt v14 tells the agent that general prose and structured responses are one atomic turn and that
a Remove override requests a registered proposal rather than authorizing deletion. The deterministic
revision validator now accepts safe exact component IDs even when the archived plan did not contain
a removal candidate. Unit coverage proves a user can request removal from an all-Keep agent plan
without creating a candidate or mutating the source. This expands review authority, not autonomous
mutation authority. Browser acceptance on the two-iteration Riding Crop proves that scrolling and
rail navigation swap between the archived turn URL and current model URL in both directions while
the DOM remains at exactly one `<model-viewer>` and reports no console errors.

### D078 — Add Claude Haiku 4.5 only through its proven US inference profile

**Date:** 2026-08-29

**Status:** ACCEPTED; least-privilege intake and full workflow passed

**Decision owner:** User and Codex

**Milestone:** M9 hosted Bedrock conversation and deployment

**Context**

The user received an accepted zero-dollar AWS Marketplace agreement for Claude Haiku 4.5 and asked
to evaluate it despite uncertainty about cost effectiveness. The Bedrock catalog exposes the direct
foundation-model ID, but a bounded call proved that on-demand throughput does not accept that ID.
The active US inference profile succeeds and routes across three documented US foundation-model
resources. Marketplace acceptance therefore cannot be treated as proof of a usable application
configuration.

**Decision**

Add Claude Haiku 4.5 to the existing `bedrock-converse` capability registry using only
`us.anthropic.claude-haiku-4-5-20251001-v1:0`. Label it experimental and tell users to compare repair
quality and cost before selecting it routinely. Keep Kimi recommended. Grant the application role
only `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` on the exact US inference
profile and its routed foundation-model ARNs. Do not add an Anthropic-specific adapter or make the
unusable direct ID selectable.

**Evidence and consequences**

The least-privilege `asset-shepherd` profile completed a bounded Haiku call. The existing live typed
intake and full Strands approval-through-package tests then passed in 58.13 seconds without a model-
specific transport change. This validates access, tool/image compatibility, approval/resume, and
deterministic packaging, but it does not establish comparative cost or quality on the real browser
matrix. D077's initial four-model allowlist is extended to five by this decision; its fail-closed,
per-workspace selection and one-adapter architecture remain unchanged.

### D077 — Use one allowlisted Converse adapter with Kimi recommended per asset

**Date:** 2026-08-29

**Status:** ACCEPTED; Kimi live workflow passed, remaining models are bounded alternatives

**Decision owner:** User and Codex

**Milestone:** M9 hosted Bedrock conversation and deployment

**Context**

Maintaining independent local-offline, Nova-Converse, and Luna-Responses implementations would
multiply intake, image, tool-schema, persistence, and UI behavior. The user instead selected a
small allowlist with guidance about when each model is useful. Model choice must not become another
workflow step or let a posted arbitrary model ID bypass tested request contracts. Each asset also
needs a stable model identity across resume and Refine.

Bounded live probes in `us-east-1` showed that Kimi K2.5, Mistral Large 3, Qwen3 VL 235B, and Nova 2
Lite all accept typed client tools and ordinary image input. The three third-party models reject an
image nested inside a Converse tool-result block even though they accept the same image as an
adjacent user content block; Nova accepts both layouts. This is a transport-layout capability, not
a reason to change the model-visible evidence or duplicate the workflow.

**Decision**

Use `bedrock-converse` as the canonical model-neutral provider. Keep a fail-closed capability
registry initially covering Kimi K2.5, Mistral Large 3, Qwen3 VL 235B, and Nova 2 Lite; D078 later
adds Claude Haiku 4.5 through the same contract. Kimi is the
recommended choice. Mark Mistral and Qwen as experimental choices for especially long/complex and
visually ambiguous work; present Nova as a lower-cost diagnostic that may need more user correction.
The existing Luna Responses adapter remains a pending specialist/compatibility path outside this
Converse UI allowlist, and the legacy `bedrock-nova` name remains read-compatible only.

Normalize only proven transport differences. For Kimi, Mistral, and Qwen, move unchanged image
blocks beside their originating tool result in the outgoing Converse user message while retaining
text, image bytes, order, tool ID, and durable Strands history. Keep Nova's reasoning field and
nested-image layout only for Nova. Never translate reasoning controls between providers.

Put one compact **Agent model** disclosure on Upload, not in the numbered workflow. Reject any
submitted ID outside the server allowlist. Persist provider and model ID in the staged upload and
durable workspace, and rebuild both intake and workflow agents from that frozen model selection.

**Evidence and consequences**

Kimi produced a valid Unreal computer-chip intake and completed the real Strands robot workflow in
66.71 seconds through inspection, four-view rendering, typed repair proposal, native approval,
execution, candidate rendering, model reassessment, independent verification, and packaging. The
verified run recorded prompt v13, one interrupt, seven successful semantic/proof tool calls, a
project-ready candidate with one remaining material warning, and explicit `bedrock-converse` /
`moonshotai.kimi-k2.5` provenance. A direct control proved that the image-hoisting normalization
removes the Bedrock validation failure without altering stored tool history.

Browser acceptance confirmed the initial compact four-model allowlist, single recommendation, hints,
default Kimi selection, and preservation across Upload. The subsequent hosted intake was blocked
only because the bootstrap AWS login token expired; the independent live intake and full workflow
had already passed. That authentication checkpoint is now closed: the refreshed login installed
exact Kimi/Mistral/Qwen invoke resources, and all visible models pass least-privilege smoke calls.
Full browser cases, cloud-portable state, AgentCore, and remote hosting remain open.

### D076 — Do not add a Grok provider path until account invocation succeeds

**Date:** 2026-08-29

**Status:** ACCEPTED; blocked by external account/model access

**Decision owner:** User and Codex

**Milestone:** M9 hosted Bedrock conversation and deployment

**Context**

Grok 4.6 is a strong candidate for a non-Anthropic Bedrock comparison because AWS documents image
input, client-side tool calling, the Responses API, and configurable reasoning through `xhigh`.
Asset Shepherd's existing Bedrock Responses bridge is technically close to reusable, except that
its fail-closed inference-profile validator currently permits only the selected OpenAI family.
Adding another maintained model path before proving account access would recreate the provider
maintenance burden the evaluation is intended to reduce.

AWS's model-access API reports `xai.grok-4.6` as agreement-available, authorized, entitled, and
region-available, and reports both `us.xai.grok-4.6` and `global.xai.grok-4.6` as active. A bounded
Responses request still returned HTTP 403, and independent Converse requests against both profiles
returned the same `AccessDeniedException`: Grok 4.6 is unavailable for this account. The test used
the administrator profile with the AWS-managed `AdministratorAccess` policy, so the failure is not
explained by the application's least-privilege role or a missing ordinary `bedrock:InvokeModel`
grant.

**Decision**

Keep Grok as an evaluation candidate, but do not modify the product provider surface until a direct
smoke request succeeds. Treat the live invocation result as authoritative over the optimistic
catalog fields. Do not broaden IAM, create a Grok-specific fourth provider, or claim Grok behavior
from catalog metadata alone. Recheck after AWS resolves the account/model-access restriction.

When access succeeds, extend the existing generic Bedrock Responses profile validator narrowly to
the documented xAI geographic/global IDs, add zero-network acceptance tests, and then run the same
robot browser case used for Nova. Compare first-turn repair completeness, image-evidence use,
sequential tool calls, approval/resume, verification, latency, token usage, and cost before changing
the selected production-parity model.

**Evidence and consequences**

Both documented invocation APIs reached Amazon Bedrock and failed before inference. No Grok model
output or behavioral evidence exists, and no provider code changed. Luna remains the parity target;
Nova remains the only completed Bedrock diagnostic.

### D075 — Host the first remote web product on App Runner beside private AgentCore

**Date:** 2026-08-29

**Status:** SUPERSEDED by D093 before implementation; no App Runner resource was created

**Decision owner:** User and Codex

**Milestone:** M9 hosted Bedrock conversation and deployment

**Context**

This entry is retained as history. D093 replaces its web-host selection with ECS Express Mode after
AWS closed App Runner to new customers; the state, authority, and private-AgentCore boundaries below
remain applicable.

Changing the local model provider to Bedrock does not move the FastAPI/Jinja site, GLB tools,
renderer, or workspace files off the user's workstation. The product needs a separately hosted web
process, durable cloud state, private asset storage, and a private agent runtime before a judge can
open it remotely. The first web host should minimize infrastructure work without becoming a second
workflow or state authority.

**Options considered**

- Run the public FastAPI service as a Linux container on AWS App Runner and invoke a separate
  private AgentCore Runtime.
- Start with ECS/Fargate for both public web compute and private workflow compute.
- Put the interactive website inside AgentCore Runtime.
- Keep the website local while using Bedrock or AgentCore remotely.

**Decision**

Package the existing FastAPI/Jinja application as one stateless Linux container in private ECR and
use AWS App Runner as the first public HTTPS web host. Keep the Strands workflow in a separate
private AgentCore Runtime. Move GLBs, renders, packages, and Strands snapshots to workspace-scoped
private S3 prefixes, and move workspace/command coordination to conditional DynamoDB records before
the remote-product gate. The browser receives application sessions and exact-object transfer URLs,
never AWS credentials.

The local launcher remains a local Uvicorn workflow at `127.0.0.1`; selecting a Bedrock provider
changes inference only and never deploys or redirects the site. ECS/Fargate is a measured fallback
if an App Runner compatibility spike fails on request duration, startup, or cost. The product keeps
one typed workflow, authority contract, and UI across local and AWS configurations.

**Evidence and consequences**

`docs/BEDROCK_DEPLOYMENT_RUNBOOK.md` now records the local/cloud responsibility map, container
spike, App Runner service boundary, remote URL behavior, permissions boundary, durable-state gate,
and rollback requirement. This decision selects architecture; it does not claim that ECR, App
Runner, S3, DynamoDB, or AgentCore resources have been deployed. Step 3 cloud portability remains
the next prerequisite. App Runner instances and filesystems are explicitly disposable, so a
replacement instance must not lose or duplicate a workspace, decision, mutation, or package.

### D074 — Use Nova 2 Lite as a reversible Converse diagnostic, not the Luna parity baseline

**Date:** 2026-08-29

**Status:** ACCEPTED; bounded live intake and one full Strands workflow passed

**Decision owner:** User and Codex

**Milestone:** M9 hosted Bedrock conversation and deployment

**Context**

The selected Luna/xhigh Bedrock Responses path reached AWS but remained unavailable to the account.
The official model-access API now distinguishes that condition: Luna reports authorization,
entitlement, and region availability, but `agreementAvailability=NOT_AVAILABLE`, while an agreement
offer exists. Creating that one-time third-party agreement is an administrator/EULA action and must
not be delegated to the least-privilege application role. Amazon Nova 2 Lite reports every
availability field as available and does not depend on a third-party Marketplace agreement, so it
can independently test the Bedrock, IAM, Strands, and tool-contract path while Luna access is being
resolved.

**Decision**

Preserve `bedrock` as the Luna Responses parity provider and add `bedrock-nova` as an explicit,
reversible provider. Nova uses Strands `BedrockModel` over Converse with
`us.amazon.nova-2-lite-v1:0` in `us-east-1`; it does not use the OpenAI-compatible endpoint or a
Bedrock bearer token. Its intake adapter forces exactly one `submit_target_intake` tool call,
inlines generated schema references, keeps only Nova's supported top-level `type`, `properties`,
and `required` fields, and then applies the unchanged strict Pydantic and confidence gates.

Use medium reasoning for this trial. AWS documents medium as the agentic-workflow setting, and the
live API rejects a bounded `maxTokens` value when Nova high reasoning is enabled. Asset Shepherd
therefore permits only low or medium Nova reasoning, fixes temperature to zero for tool use, and
bounds workflow and intake output at 8,192 and 4,096 tokens respectively. Do not silently translate
Luna `xhigh` to a Nova setting. Keep exact Nova invocation/profile resources in a separate inline
runtime policy so the fallback can be removed without changing Luna permissions.

**Evidence and consequences**

Read-only availability checks found the US Nova inference profile active across the same three US
regions used by the project. A least-privilege 63-token connectivity call returned `NOVA_READY`.
The live intake produced a validated Computer Chip/Unreal/7 × 1.2 × 6.23 cm/one-piece proposal.
The normal opt-in Strands approval-through-package workflow passed in 113.83 seconds through Nova.
This proves that the account, runtime role, Bedrock Runtime, Converse transport, Strands loop, and
typed tools work together; it does not establish Luna behavioral parity or complete the eight-case
browser matrix. Luna remains the selected production-parity model until its one-time agreement is
reviewed and accepted by an administrator or the user deliberately changes that decision.

### D073 — Use one fail-closed Bedrock Responses transport for intake and Strands

**Date:** 2026-08-29

**Status:** ACCEPTED; live behavior gate awaiting the Luna model agreement

**Decision owner:** User and Codex

**Milestone:** M9 hosted Bedrock conversation and deployment

**Context**

D071 selected Bedrock-hosted GPT-5.6 Luna/xhigh for parity with the successful local workflow, but
the code still routed workflow calls through Strands `BedrockModel`/Converse and had no Bedrock
semantic-intake adapter. The AWS Responses endpoint accepts the same client-side custom tools used
by the local workflow, while AWS-login credentials can produce temporary bearer tokens without a
long-term Bedrock key.

**Decision**

Use the OpenAI-compatible `bedrock-runtime` Responses endpoint for both model boundaries. The
Strands model adapter keeps complete non-streaming Responses, sequential tool calls, stateful
response IDs, and the existing typed tool surface. It obtains an IAM-derived short-term bearer
token per request and never stores that token in model configuration. Bedrock intake forces exactly
one `submit_target_intake` function call carrying the unchanged `TargetIntakeInference` JSON Schema;
absent, wrong, repeated, malformed, or Pydantic-invalid submissions fail closed.

Bedrock startup requires an explicit geographic/global OpenAI inference profile and region, removes
any inherited `OPENAI_API_KEY`, and defaults intake to Bedrock when no separate intake provider was
chosen. The optional direct-OpenAI adapter remains available only for local development and is not
a production fallback. AWS CLI login profiles require Botocore's CRT extra, so it is an explicit
runtime dependency.

**Evidence and consequences**

Unit acceptance proves the regional runtime URL, model provenance, Luna/xhigh request controls,
single typed intake submission, sequential workflow tools, stateful response IDs, request-scoped
credentials, safe errors, and Bedrock-aware launcher path. The least-privilege runtime role resolves
and successfully mints a short-term token. The first bounded request reached
`bedrock-runtime.us-east-1.amazonaws.com` but AWS returned HTTP 403 because the new account is still
being verified. Therefore implementation is complete, but Step 2 behavioral parity—including image
evidence, interrupt/resume, usage, and representative workflows—must not be claimed until AWS lifts
that external restriction and the opt-in live tests pass. D074 subsequently isolated the current
Luna blocker to its unavailable one-time model agreement and proved the rest of the path with Nova.

### D072 — Treat official contest compliance as six release gates

**Date:** 2026-08-29

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M11 documentation and M12 release/submission

**Context**

The user requested a current independent review of the Agents for Humans official rules against the
implementation and controlling project documents. The repository contains a genuine local Strands
agent and began during the submission period, but those facts alone do not establish entrant
eligibility, public judge access, complete submission media, ownership attestations, or final
release hygiene. The live rules also contain stale lower-page blog language despite an August 12
notice removing the `#AgentsforHumans` requirement.

**Decision**

Adopt `docs/CONTEST_COMPLIANCE_PLAN.md` as the executable contest release plan beneath the official
rules and the Project Contract. A project may not be described as submission-ready until it closes
six gates: entrant/registration attestation, eligible-build proof, public-repository proof,
free judge-access proof, submission-package proof, and final-freeze proof. Recheck the official rules on
September 10 and on submission day. Keep all personal eligibility and account evidence private;
only record gate status publicly.

Correct project documents that treated a literal `#AgentsforHumans` hashtag as mandatory. Optional
Builder posts should include the plain words **Agents for Humans** in their title, which satisfies
the surviving conservative reading, but the project will not depend on bonus points for basic
eligibility. Bedrock-hosted GPT-5.6 Luna remains allowed: the rule requires real Strands Agents use,
not an Anthropic or Amazon-native foundation model. AgentCore remains optional but beneficial.

**Evidence and consequences**

The 2026-08-29 rules snapshot fixes the submission deadline at September 14, 5:00 p.m. Pacific and
requires free project access through the October 8 judging deadline. Git history begins August 21;
the MIT license and README exist; Strands is the actual orchestrator. The current GitHub repository
is still private, and remote access, final architecture, public sub-five-minute video, Devpost text,
Builder ID confirmation, disclosures, release scans, and entrant attestations remain incomplete.
The current answer is therefore “eligible implementation direction, incomplete submission,” not
“compliant in all respects.”

### D071 — Preserve the local Luna/xhigh workflow through Bedrock Responses

**Date:** 2026-08-29

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 hosted Bedrock conversation and deployment

**Context**

The successful local agent-led runs use OpenAI `gpt-5.6-luna` with `xhigh` reasoning through the
Responses API. The user prefers not to use an Anthropic model and wants the AWS deployment to keep
the same agent baseline rather than introducing a simultaneous provider and model-behavior change.
The account-visible Bedrock catalog in `us-east-1` exposes active US and global inference profiles
for GPT-5.6 Luna with text and image input. Amazon Bedrock's model card supports Responses,
Chat Completions, and Converse for this model, but does not advertise Bedrock structured outputs.

**Decision**

Use OpenAI GPT-5.6 Luna through Amazon Bedrock as the first production-parity model. Freeze the
logical model as `gpt-5.6-luna`, the local Bedrock region as `us-east-1`, the initial geographic
inference profile as `us.openai.gpt-5.6-luna`, and reasoning effort as `xhigh`.

Use the OpenAI-compatible Responses API on the recommended `bedrock-runtime` endpoint for the
parity gate so the workflow retains its existing Responses tool-call and reasoning contract. AWS
credentials and a short-term Bedrock bearer token replace the direct OpenAI API key; production
must not depend on a long-term Bedrock API key. The generic Strands `BedrockModel`/Converse path
remains available for future provider experiments but is not the parity baseline if it cannot
preserve the selected Responses reasoning controls.

Semantic intake uses the same Bedrock-hosted Luna/xhigh model. Because Bedrock does not currently
advertise structured outputs for this model, intake must return its existing exact typed schema
through a constrained tool call or another tested fail-closed adapter and still pass the unchanged
Pydantic and confidence gates. It may not weaken validation or silently fall back to direct OpenAI.

**Evidence and consequences**

The repository already records successful live agent runs with `gpt-5.6-luna`/`xhigh`. Read-only
account inspection confirms `openai.gpt-5.6-luna` is active with text and image input and that
`us.openai.gpt-5.6-luna` routes within `us-east-1`, `us-east-2`, and `us-west-2`. The bounded smoke
test must still prove image input, sequential custom tool calls, typed intake, interrupt/resume,
and usage reporting before this becomes the production provider. No model call is authorized by
this decision alone.

### D070 — Migrate to Bedrock and AgentCore through three independent gates

**Date:** 2026-08-29

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 hosted Bedrock conversation and deployment

**Context**

The local product now has a genuine Strands agent, bounded model-directed tools, per-asset durable
sessions, exact approval, repeatable refinement, and successful real-asset repair runs. Moving it
from the interim OpenAI provider and one Windows workstation to AWS could nevertheless entangle
three unrelated failure domains: model behavior, persistent storage/rendering, and remote hosting.
The current workflow provider already has a Bedrock constructor, while semantic intake remains
OpenAI-only, snapshots and artifacts remain filesystem-backed, and standardized visual sensing
invokes a locally installed Blender executable.

**Decision**

Adopt `docs/BEDROCK_DEPLOYMENT_RUNBOOK.md` as the executable M9 deployment procedure. Prove three
gates in order: the unchanged local product runs entirely through Bedrock; required state,
artifacts, and visual evidence no longer depend on a workstation; and the remote browser product
passes upload-through-download acceptance. Keep `workspace_id` as the single per-asset session
authority. Use Strands S3 session storage for distributed snapshots, private S3 for binary
artifacts, and conditional DynamoDB records for workflow/idempotency state. Do not introduce
AgentCore Memory in the first deployment.

Host the Strands runtime in AgentCore only after local Bedrock behavior passes. Keep the interactive
FastAPI/Jinja web service separate and invoke the private runtime service-to-service. Prefer a
lightweight deployable renderer; if it fails a written acceptance test, a separate bounded x86
render worker requires a fresh cost/architecture approval. Preserve the working local product until
the complete remote gate passes.

**Evidence and consequences**

The runbook maps current code boundaries to eight gated steps, records credential and cost
checkpoints, specifies restart/idempotency acceptance, and links current official Strands and AWS
documentation. Step 1.1 found an existing per-user AWS CLI v2.36.34 installation whose PATH update
has not reached the current Codex process, and no AWS profile/configuration yet exists. Paid calls
and AWS infrastructure still require verified caller identity, model/region access, and a budget
alert; no resource is authorized merely by adopting this procedure.

### D069 — Cycle comparison viewpoints through one icon control

**Date:** 2026-08-29

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 hosted conversation UX

**Context**

The comparison viewer devoted four adjacent controls to one camera concern: a passive fit glyph and
separate Both, Before, and After buttons. The segmented treatment consumed attention and space
without adding four distinct capabilities.

**Decision**

For a before/after comparison, use the existing square fit glyph as one **Cycle viewpoint** button.
Each activation advances Both → Before → After → Both through the existing smooth camera-fit path.
The button's tooltip and accessible name must always state the current view and the next view. A
source-only viewer retains the same glyph as a simple **Fit model to window** action because it has
no alternate viewpoint to cycle.

**Evidence and consequences**

The completed Humanoid Woman workspace renders one viewpoint button plus the independent axes and
banana toggles. Live browser interaction on port 8010 completed the full three-click cycle, updated
the tooltip and accessible name after every transition, and produced no browser-console errors.
The camera, HUD, metric axes, and banana continue to use the same selected-bounds fit function.

### D068 — Route safe component ambiguity into labeled review

**Date:** 2026-08-28

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 agent-led sensing and disposition / hosted conversation UX

**Context**

A live riding-crop pass correctly measured three disconnected, safely removable components but
returned the asset to its creation tool because it was uncertain which form represented the intended
crop. The completion page then falsely said that no supported action could remove the extra forms,
even though exact-ID component removal and per-component Keep/Remove review were already available.
The whole-source bounds also failed the approximate target proportions before the stray forms had
been removed.

**Decision**

When deterministic inspection marks component removal safe and the target expects fewer semantic
pieces, the agent should use all four source views to propose a plausible exact survivor/removal set.
It must disclose uncertainty and lower confidence instead of inventing certainty; the labeled
per-component review remains the user's authority to accept or revise the selection. Semantic
uncertainty alone is not an unsupported-capability failure when this review can resolve it. If the
views are genuinely indeterminate or removal is unsafe, the agent still stops without selecting.

Component selection precedes physical normalization when extra forms distort the whole-asset bounds.
The surviving candidate is remeasured in a later Refine turn. A target-box residual from the
unfiltered source must not suppress a useful component-removal proposal.

**Evidence and consequences**

Prompt v13 encodes the sequencing and authority boundary. The persisted three-form workspace now
states that the pass stopped before choosing labeled forms and offers **Refine current iteration**
over its saved input instead of claiming removal is impossible. Its amber inspection row
distinguishes a recoverable stopped pass from a red, actually ineligible GLB layout. No component is
deleted until the model registers exact stable IDs and the user approves or revises those choices.

### D067 — Preview a proposed origin separately from the current origin

**Date:** 2026-08-28

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 hosted conversation UX

**Context**

An origin-only Refine proposal used imperative agent prose such as “Move the asset origin” while
the approval viewport correctly continued to render the unmodified current iteration. Its lone
`ORIGIN` marker therefore appeared outside the surviving component's bounds and made a correct
pending transform look like a falsely completed repair.

**Decision**

Before approval, keep rendering the current immutable iteration but label its authored coordinate
origin **Current origin**. When the typed pending normalization contains a pivot action, derive its
exact target from the registered payload and render a second, visually distinct **Proposed origin**
marker on the current geometry. Phrase repair assessments prospectively as “I propose this
change…” until authorization and execution occur. Do not execute or simulate the model mutation in
the approval viewport.

**Evidence and consequences**

The recovered Equestrian Riding Crop plan requests `BOUNDS_CENTER`; its deterministic payload
places the preview marker at the measured bounds center
`(-0.0332031623, 0.6083984673, 0.0) m` while retaining the authored origin at `(0, 0, 0)`. Browser
inspection on port 8011 confirms both labels remain attached during orbit and the proposed marker
appears at the wireframe-box center. The proposed translation remains subject to the existing
explicit approval, fresh write, reload, verification, and before/after comparison path.

### D066 — Normalize optional tool arguments and recover incomplete planning

**Date:** 2026-08-28

**Status:** ACCEPTED

**Decision owner:** Codex

**Milestone:** M9 agent-led sensing and disposition / hosted conversation UX

**Context**

A live riding-crop run rendered and interpreted the source correctly, then exhausted its bounded
12-call turn while trying to register a report-only assessment. The Responses tool trace showed two
deterministic interface traps rather than an absent conclusion: the model represented an unused
optional pivot ID as an empty string, and a report-only assessment cited four rendered views that
the validator considered available only when a mutation was requested. The terminal UI discarded
those useful errors and reported only that verification and packaging had not occurred.

**Decision**

Normalize a blank optional pivot-anchor string to absence at the deterministic tool boundary; a
non-empty registered ID remains the only measured-anchor authority. Validate cited source views for
every disposition, including report-only and return-to-creation conclusions, while still requiring
all views for physical, yaw, component-selection, and measured-anchor actions.

When an invocation ends after inspection but before registering an assessment, preserve the source,
target, inspection, and cached renders and expose one **Retry Shepherd** action. That action starts a
fresh bounded planning invocation over the same deterministic job and cannot invent prior approval
or mutation. Keep the existing post-action **Finish this iteration** recovery separate. If planning
still cannot register, state that its tool-call limit was reached and that the saved iteration can
be retried instead of mislabeling the failure as a packaging problem.

**Evidence and consequences**

Regression coverage accepts a rendered return-to-creation assessment with `pivot_anchor_id=""`,
persists the normalized null, and produces a blocked diagnostics package. The original failed
Equestrian Riding Crop workspace was recovered by replaying the model's already-recorded valid
proposal after the boundary fix; it now has a BLOCKED result, no error, and an explicit Asset
Shepherd explanation about the three separated forms and unsupported proportional correction.
Browser inspection on port 8011 confirms the generic **Stopped** alert is gone. This recovery adds
no mutation authority and does not increase the per-asset Refine limit.

### D065 — Present workflow-agent prose as one consistent speaker

**Date:** 2026-08-28

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 hosted conversation UX

**Context**

Agent-authored summaries appeared as ordinary page text, so a correct clarification such as the
unsupported handle-center response looked like an anonymous system verdict. The same ambiguity
could recur at Upload, Describe, approval, completion, and refusal states.

**Decision**

Render the one agent-authored sentence as a compact Asset Shepherd speech bubble with a visible
speaker label and accessible “Asset Shepherd says” prefix at every workflow step. Keep operational
errors in alert styling and retain the one-title/one-message rule; the speaker label is identity
metadata, not a second page subtitle.

**Evidence and consequences**

The shared `agent-message` treatment is used by Upload, Describe, target confirmation, approval,
completion, refusal, and the legacy intake route. Approval now shows the model's concise assessment
above the single check table instead of hiding who formed the proposal. Route tests assert the
shared component on the principal workflow states.

### D064 — Let the agent choose only source-bound measured pivot anchors

**Date:** 2026-08-28

**Status:** ACCEPTED; extends D053 without exposing arbitrary translation

**Decision owner:** User and Codex

**Milestone:** M9 agent-led sensing and disposition / M10 evaluation

**Context**

After retaining the correct riding-crop component, the user asked for the origin at the center of
the handle. The agent understood the request but correctly stopped: D053 exposed only preserve,
bounds-center, and footprint-center-bottom, none of which represented the semantic handle center.
Stronger prompting could not create a missing typed action safely.

**Decision**

Add a deterministic pivot-sensing tool that inventories stable, source-hash-bound geometry
landmarks: authored origin, bounds center, footprint center-bottom, eight bounds corners,
triangle-area centroid, and the area-weighted centers of the outer quarters of the longest bounds
axis. Add a uniform-volume centroid only when virtual-weld evidence proves every analyzed primitive
closed, manifold, and consistently wound; label it as a uniform-density geometric assumption.

The agent may request `MEASURED_ANCHOR` only by an opaque ID returned for the exact current source,
after consulting all four coordinate-labeled views. The server resolves the ID to coordinates and
label, persists the inventory, previews the exact translation, requires approval, and verifies that
the selected point reaches the origin. Unknown IDs, model-supplied XYZ, authored-origin no-ops, and
measured-anchor-plus-grounding conflicts fail closed.

**Evidence and consequences**

The actual surviving riding crop yields separate Z-min and Z-max end-region surface centers in
addition to its coarse centers and corners, giving the agent measured choices it can associate with
the visible handle. Unit coverage proves registered selection, rejection of invented IDs, exact
matrix placement, written inventory, execution, and independent pivot verification. Prompt version
12 and the live tool-activity feed expose the new sensing step without disclosing chain of thought.
This remains an approximation: if none of the finite landmarks matches a hinge, socket, or other
functional point, the agent must ask or defer to the creation tool.

### D063 — Promote an explicit survivor into a looping Refine step

**Date:** 2026-08-27

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 agent-led sensing and disposition

**Context**

The riding-crop component-removal case exposed three coupled failures. A later feedback turn
correctly inspected the prior candidate internally, but the browser source route still served the
original three-component upload. World bounds included deleted-but-unreferenced POSITION tuples,
so the candidate box and origin comparison remained stale. After an application restart, the
Strands agent ID changed from `source` to the candidate filename stem and could no longer resume the
saved interrupt. The product also hid repeated turns inside Shepherd, leaving no explicit decision
about which iteration should continue.

**Decision**

Keep **3 Shepherd** as the first complete assessment/candidate turn. At its result, let the user
choose either the current input or candidate as the surviving immutable **Iteration 1**. Add **4
Refine** to the rail and render loop passes as 4.1, 4.2, 4.3, and so on. Each pass archives its full
evidence, records which side survived and its hash, re-inspects that GLB, and requires a fresh
proposal and approval for any consequential change. A failed candidate remains selectable for
human override; a missing candidate still permits reworking the input.

Serve the selected iteration everywhere a source model is requested. Compute usable world bounds
from indexed positions actually referenced by surviving primitives. Keep deliberately unreferenced
tuples visible as a separate cleanup finding, but exclude them from framing and origin comparisons.
After component deletion, candidate reassessment must use the surviving bounds. If the origin is
now unsuitable, the agent reports it as focused follow-up; a selected candidate is freshly sensed
in Refine and any pivot move is separately proposed and approved.

Use one stable agent ID inside each workspace-scoped session so filename changes cannot break
interrupt restoration. If mutation completed but a transient provider/evidence failure interrupted
the remainder of the turn, expose **Finish this iteration**; it resumes only rendering,
reassessment, verification, and packaging and cannot repeat the mutation.

**Evidence and consequences**

The persisted riding-crop workspace now resolves its source route to turn 0's repaired GLB, renders
one surviving component, and measures referenced bounds of approximately 35.4 × 27.1 × 97.5 cm
instead of the original three-body 97.1 × 74.4 × 97.5 cm box. Its origin remains separately visible
outside the surviving bounds, correctly presenting the next agent decision. The rail shows Refine
and 4.1 Iteration 1. Unit coverage proves referenced-only component bounds, explicit input
continuation and restart restoration, selected-source routing, Step 4 gallery status, prompt
version 11, and a stable agent ID. Existing component removal remains index-only; this decision
does not authorize automatic pivot movement or arbitrary geometry deletion. The persisted approved
cleanup also recovered through visual reassessment, independent verification, and packaging after
comparison framing was corrected to refresh translated Blender world matrices before camera fit.

### D062 — Add agent-selected exact component removal

**Date:** 2026-08-27

**Status:** ACCEPTED; supersedes D060's blanket deferral for the bounded supported layout

**Decision owner:** User and Codex

**Milestone:** M9 agent-led sensing and disposition / M10 evaluation

**Context**

The riding-crop case proved that one primitive can contain several visible copies while node, mesh,
and primitive counts still look normal. The user asked to attempt a repair capability, while
explicitly recognizing the false-positive risk from layered shells, multipart props, and small gaps
between pieces that should be interpreted together.

**Decision**

Enumerate exact bodies after projecting byte-identical positions and connecting faces that share any
projected vertex. Stable IDs bind each body's mesh, primitive, ordinal, and canonical triangle
membership. Separately compute bounded AABB near-contact groups from a numeric floor through 0.1%
of the primitive diagonal. These groups are evidence only and can never weld, select, delete, or
change the exact inventory.

The workflow agent may propose exact component IDs only after using all four source views and the
confirmed piece expectation. The UI shows every body in the existing topology row, highlights its
world-space wireframe box on hover/focus, and lets the user keep, remove, or comment. Any changed
selection archives the proposal and returns to the agent; exact approval is still required before
mutation. Never infer remove-small, keep-largest, or delete-extras.

Restrict execution to one-instance, unskinned, indexed static triangle primitives with dense,
understood, unextended attributes, no morphs/compression, valid indices, and no pending degenerate
cleanup. Filter approved triangles only, append a replacement index accessor, preserve the original
binary prefix and all retained expanded corner attributes, and refuse removal of every body.
Independent verification reproduces the exact count and triangle delta. Leftover unreferenced tuples
remain explicit and require a separate cleanup turn.

**Evidence and consequences**

A synthetic three-body GLB inventories three stable bodies, removes two only after exact approval,
re-inspects as one body/four triangles, and verifies all retained corner evidence. Unknown IDs and
total deletion fail closed. A sub-0.1%-diagonal gap reduces only the largest-tolerance advisory
group count; without an agent selection the plan contains no component mutation. Component-specific
keep and alternate-remove feedback reopens planning without writing a candidate. A live browser run
confirmed the agent/UI/approval/execution/reassessment path. Per-view orthographic evidence fitting
also keeps thin projections visible without changing the shared source/candidate scale contract.
Broader semantic labeling, isolation, skinned/morphed/compressed layouts, automatic selection, and
vertex compaction remain outside this action.

### D061 — Add an approval-bound degenerate-geometry cleanup

**Date:** 2026-08-27

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 agent-led sensing and disposition / M10 evaluation

**Context**

The checked-in `degenerate_triangle.glb` fixture contains one objectively zero-area triangle and
one complete vertex tuple referenced only by that triangle. Inspection already found both defects,
but the result UI concealed them and the registered tool set could only report them. The user asked
whether Asset Shepherd could repair both and explicitly approved addressing the gap. The existing
contract otherwise blocked topology mutation, so this requires a narrow amendment rather than an
implicit expansion to general mesh repair.

**Decision**

Register `CLEAN_DEGENERATE_GEOMETRY` as an agent-selected, approval-required action. It is available
only for indexed triangle-list primitives whose dense, unextended vertex attributes have matching
cardinality and whose surviving geometry is nonempty. The preview freezes exact per-primitive
triangle and position counts. Execution removes only repeated-index or scale-relative zero-area
triangle triples, compacts only complete vertex tuples no surviving triangle references, remaps
every aligned attribute together, and appends replacement accessors while retaining the original
binary payload as an unchanged prefix.

Keep this action separate from physical normalization and exact-tuple welding so one approval has
one unambiguous consequential footprint. Continue to block strips, fans, non-indexed geometry,
sparse or extended accessors, malformed indices or cardinality, morph targets, compressed or
unknown attributes, all-triangle deletion, seam welding, hole filling, normal recalculation,
remeshing, and semantic component deletion. A user decision cannot override those safety proofs.

**Evidence and consequences**

The synthetic fixture now previews removal of exactly one of 12 index triples and one of 24 vertex
tuples. Approval produces 11 triangles and 23 positions in the affected primitive; fresh inspection
reports zero degenerate triangles and zero unused positions. Expanded surviving corner attributes,
materials, textures, node references, and original binary bytes are independently verified. A
rejection writes no changed bytes and preserves both findings. The five-row result table now shows
the two defects, the exact proposed action, and `Addressed` only after verification. General
topology reconstruction remains outside the MVP.

### D060 — Make unsupported dispositions explicit; defer component deletion

**Date:** 2026-08-27

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 hosted agent workflow

**Context**

A real riding-crop input contained three visually distinct forms inside one GLB node, mesh, and
primitive. Objective position-projected topology measured three connected forms, and the workflow
agent correctly selected `RETURN_TO_CREATION_TOOL` because the confirmed target expected one crop
and no registered action could remove geometry. The result page nevertheless showed `GLB structure`
as passing, concealed the three-form observation, and offered a continuation control that could not
run without a candidate GLB.

Deleting disconnected geometry could repair this example, but connected components are not semantic
pieces. Layered shells, hard-surface details, paired objects, and deliberately separate components
can all be valid. Removing triangles is an irreversible topology mutation and is outside the current
registered repair boundary.

**Options considered**

- Keep the existing page and rely on the agent's summary alone.
- Treat every extra connected component as disposable and remove it automatically.
- Make the unsupported disposition and measured mismatch explicit now, and defer a bounded
  component-selection repair domain.

**Decision**

Render `RETURN_TO_CREATION_TOOL` as one unmistakable blocked sentence and a red blocked inspection
lane. When the agent's evidence ties a confirmed semantic-piece mismatch to the objective component
probe, show the measured form count, expected piece count, and the absence of a supported removal
action. Do not show a retry control when the completed turn produced no candidate to seed another
turn; offer diagnostics and Gallery instead.

Do not add geometry deletion to the pre-deployment repair allowlist. A future component-removal tool
is desirable only as an explicitly approved, high-risk action: it must assign stable component IDs,
show each candidate component highlighted, record exactly which components will be kept or removed,
preserve the original as R0, and independently verify the remaining geometry, appearance, UVs,
materials, textures, bounds, and payload. It must never infer that “small” or merely disconnected
means disposable. The deferred design and acceptance gates are recorded in
[`FUTURE_COMPONENT_HANDLING.md`](FUTURE_COMPONENT_HANDLING.md).

**Evidence and consequences**

The saved riding-crop workspace now renders “I can't repair this asset,” reports `3 disconnected
forms detected; target 1 semantic piece`, marks the structure lane with a red blocked icon, and
offers only diagnostics and Gallery. Its inconsistent display-name row also reports the two
unresolved findings instead of claiming no cleanup is needed. A regression test binds these outputs
to structured assessment and geometry facts, and browser acceptance verifies the actual persisted
workspace. Component deletion remains a separately scoped capability rather than a silent expansion
of the deterministic mutation engine.

### D059 — Show workflow status on every gallery project

**Date:** 2026-08-26

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 hosted agent workflow

**Context**

Gallery cards printed raw durable phase names such as `TARGET_CONFIRMATION` and `APPROVAL`. Those
names exposed implementation state, did not locate the asset in the three-step user workflow, and
made successful, attention, blocked, and failed projects visually indistinguishable.

**Decision**

Give every valid persisted asset one compact status line under its agent-assigned name. Translate
the durable phases as follows:

| Durable phase | Gallery status | Tone |
|---|---|---|
| `TARGET_CONFIRMATION` or uploaded draft | `Step 2 · Describe` | Neutral |
| `APPROVAL` | `Step 3 · Review` | Amber |
| `COMPLETE` | `Step 3 · Ready` | Green |
| `BLOCKED` | `Step 3 · Blocked` | Red |
| `ERROR` | `Step 3 · Failed` | Red |

Use both words and a colored dot so color is never the only status carrier. Keep the text at 15 px
and add no legend, status panel, subtitle, or duplicate progress summary.

A rejected Step 1 upload does not have a valid source and therefore is not yet a project. Keep the
user on Upload with the actionable error, create no gallery record, and consume none of the seven
slots. Once a GLB passes upload preflight, its draft appears as `Step 2 · Describe`.

**Evidence and consequences**

Typed mapping coverage exercises all five durable phases. Hosted-route coverage proves one
description card and one approval card render the correct status, tone, and no raw phase name; draft
coverage proves an upload awaiting description survives with the same Step 2 status. Browser
acceptance confirms the compact status line is visually legible in the existing card without adding
another attention region. The common gate passes with 156 tests, one opt-in skip, lock validation,
Ruff, formatting, and zero Pyright findings.

### D058 — Keep source context visible during Shepherd work and reject unusable uploads early

**Date:** 2026-08-26

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 hosted agent workflow

**Context**

The source viewer disappeared when a Shepherd request entered its working state, leaving only a
tool-activity list. Its source-only HUD also used a redundant `Before` leader and did not expose the
measured dimensions on the wireframe bounds. Separately, a parseable asset with an extreme or
degenerate world-space bounding box could enter semantic intake even though its scale made useful
inspection and framing impractical. Malformed GLBs exposed inconsistent upload errors, and the FBX
boundary had not been exercised with a concrete fixture.

**Decision**

Keep the shared source-only viewer visible next to observable tool activity and apply a slow orbit
only while Shepherd work is active; respect reduced-motion preferences. When no candidate exists,
show one adaptive metric `X × Y × Z` label on the measured 12-edge bounds and remove the `Before`
leader. Preserve the existing axes and banana controls.

Treat three positive finite world-space extents and a largest-to-smallest extent ratio no greater
than 10,000:1 as universal preflight invariants. Fail before target intake or agent work when either
condition is false. Keep public upload errors concise: distinguish a non-GLB container from a
damaged or incomplete GLB while retaining parser detail only in server logs.

Maintain the submission's GLB-only boundary. Check in four tiny reproducible upload fixtures for
gibberish, a truncated valid GLB, malformed JSON inside a GLB container, and an FBX-shaped file.
Adding FBX is a later compatibility project, not an extension guessed from a filename: it requires a
native conversion dependency, explicit axis/unit/pivot and payload contracts, exporter-spanning
corpus coverage, security hardening, and revised provenance. A future spike may evaluate static FBX
import to canonical GLB, but lossless FBX round-trip is not promised.

**Evidence and consequences**

Hosted-route tests prove pathological bounds and all four malformed/unsupported files remain at
Upload, do not persist `source.glb`, and never enter the description or agent path. Inspector tests
retain successful GLB parsing and geometry evidence while classifying extreme bounds as unusable.
Browser acceptance confirms one adaptive dimension label, no source-only leader, the 12-edge box,
and no idle auto-orbit. Static behavior coverage proves the viewer remains present and orbit is
toggled only by the working state. The common gate passes with 151 tests, one opt-in skip, lock
validation, Ruff, formatting, and zero Pyright findings.

### D057 — Separate the Gallery from the three-step Workflow and show the source from Describe onward

**Date:** 2026-08-25

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 hosted agent workflow

**Context**

The left rail numbered the asset gallery as if it were the first operation performed on one asset.
That mixed workspace selection with the workflow itself and made Upload step 2 even though every new
run begins by supplying a file. The uploaded model was also invisible during target description and
agreement, while its measured bounds were represented by flat screen-space corner brackets only
after a repair.

**Decision**

Make **Gallery** and **Workflow** the two high-level rail choices. Gallery is the only place to start
or resume an asset. Workflow becomes available only for a selected asset and contains exactly three
steps: **1 Upload, 2 Describe, 3 Shepherd**. Returning to Gallery preserves the current phase.

From Describe onward, render the staged immutable GLB in the existing local shared viewer. Its
metric axes and 20 cm banana remain optional. Project the eight measured world-space AABB corners
through the active camera and connect the canonical 12 edges as a wireframe box. The box therefore
rotates, pans, and zooms with the asset. A completed candidate uses the same component for its
before/after scene; no new renderer, storage authority, or mutation is introduced.

**Evidence and consequences**

Hosted route coverage proves that Gallery has no numbered workflow, Upload activates step 1,
Describe activates step 2 with one source-only viewer, and the durable workspace keeps the source
viewer through target agreement and inspection. Browser acceptance at desktop and 375 px content
width confirms no horizontal overflow, a readable two-column/stacked layout, optional axes and
banana controls, and a 12-edge path that changes with camera rotation. Removing the stale source-map
directive from the pinned minified viewer prevents its optional `.map` request without changing the
vendored runtime or license. One additional real Tripo-to-Unreal asset was reported usable without
game-developer complaints; this is encouraging field use, not a replacement for registered RW
evaluation evidence. The common gate passes with 148 tests, one opt-in skip, lock validation, Ruff,
formatting, and zero Pyright findings.

### D056 — Make the action report reflect verified outcomes

**Date:** 2026-08-25

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 agent-led sensing and disposition

**Context**

The same inspection table appears before authorization and after execution. The completion view
continued to label its final column `Proposed action` and retained attention icons for findings that
the approved candidate had already corrected. That made a finished report look like another pending
proposal and obscured the distinction between attempted, verified, rejected, and report-only work.

**Decision**

Keep one five-lane table, but make it phase-aware. Before execution, show `Proposed action` and the
existing attention state. After execution, show `Action taken`. A previously detected problem that
was executed and independently verified uses the compact `!→✓` transition and an `Addressed` hover
explanation. An attempted action that verification did not confirm, a rejected action, and an
unresolved or report-only finding retain attention styling and explicitly say that no verified
correction occurred. Passing invariant lanes remain plain checks.

**Evidence and consequences**

Hosted route coverage distinguishes successful normalization/name repairs from failed verification:
the accepted candidate renders two `!→✓` outcomes and `Applied` actions, while the forced-failure
candidate renders no repaired transition and says verification did not confirm the attempt. Browser
acceptance checks the completion header, repaired rows, unresolved warning, hover explanation, and
absence of horizontal overflow. The common gate passes with 148 tests, one opt-in skip, lock
validation, Ruff, formatting, and zero Pyright findings.

### D055 — Make proposal feedback typed and hide stale controls during agent work

**Date:** 2026-08-25

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 agent-led sensing and disposition

**Context**

The approval screen showed the agent's proposed actions but offered only one grouped approve/reject
choice. Users could not accept one proposed lane, reject another, or explain a requested change to
the same stateful agent. During long agent requests, the prior question and its Yes/No/feedback
controls remained visible beside the tool-activity trace, implying they were still actionable.

**Decision**

Show `Accept`, `Reject`, and `Comment` only on inspection-table rows containing an actual proposed
mutation. Keep one overall action: all accepted lanes expose `Approve`; any rejection or comment
changes it to `Revise plan`. A revision is not authorization. Archive the exact pending plan,
assessment, interrupt binding, and typed responses; execute nothing; then resume the same
workspace-scoped Strands conversation so the agent can gather evidence and propose again. Keep pass
and report-only rows non-interactive. Preserve the single grouped approval boundary for the exact
consequential action hash.

As soon as a request with observable agent activity is submitted, hide all stale workspace content
and controls and show only the current tool-use summaries. Do not add a decorative Cancel button:
the current synchronous provider call has no cooperative cancellation boundary, so such a control
would be dishonest until cancellation can actually stop the backend operation.

**Evidence and consequences**

Browser verification against a live pending interrupt shows response controls only on Size and pose
and Display names, changes the single button from `Approve` to `Revise plan` when Comment is chosen,
reveals one required 1,000-character comment field, and restores `Approve` when the lane is accepted.
Core regression coverage proves revision archives the pending plan and assessment, records the typed
response, clears the interrupt, and creates no candidate GLB. Prompt version 8 requires the agent to
respect rejected/commented lanes and forbids reusing the archived action. A live names-only revision
honored the scale comment and proposed and executed only deterministic renames. That run exposed and
closed an overbroad visual gate: index-preserving display-name-only candidates now proceed through
exact inventory and payload verification without requiring a meaningless render comparison;
physical and topology mutations still require it. The common gate passes with 148 tests, one opt-in
skip, lock validation, Ruff, formatting, and zero Pyright findings.

### D054 — Flatten proven multi-turn transforms and expose observable agent activity

**Date:** 2026-08-25

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 agent-led sensing and disposition / M10 real-world evaluation

**Context**

Each repair turn promotes its candidate to the next immutable input. Adding another normalization
node on every turn would accumulate a wrapper hierarchy even though the intended result is one
reversible placement transform. Separately, standardized screenshots previously counted as
evidence when the expected files merely existed; a blank, clipped, corrupt, or ineffectively framed
image could therefore reach the workflow model. The browser showed only `Working…` during these
long operations and the approval table and 3D HUD still spent too much space on small text.

**Decision**

When the immediately preceding turn's output hash, archived repair plan, provenance, active scene
root, root identity, and root matrix all prove that Asset Shepherd created the current normalization
root, compose the new agent-requested delta into that root as `delta @ existing`. Do not trust a
name alone and do not mutate an arbitrary authored root. The typed action records the existing root
index, before matrix, after matrix, and application mode; independent verification permits only
that exact matrix change and no new node.

Render an object mask with every standardized view. Before an image can become model evidence,
require a decodable PNG, a matching mask, meaningful image range, measurable foreground, useful
projected span, bounded occupancy, and a clear frame margin. Record image/mask hashes and framing
metrics and return those metrics with the model-visible images. This evidence contract is portable
to a later lightweight renderer; it does not make Blender a hosted dependency.

Replace opaque busy copy on agent transitions with at most three observable action summaries from
the Strands tool-use callback. Never publish reasoning tokens, streamed model prose, or private
chain-of-thought. Keep the activity state isolated by workspace and available through a no-store
endpoint while the form request is in flight. Increase approval-table body text and 3D axis,
target-box, banana, control, and caption text without adding another title or panel.

**Evidence and consequences**

A two-turn regression first scales an offset source, then requests a footprint-center pivot. The
second plan uses `COMPOSE_EXISTING_ROOT`, preserves node count, leaves exactly one Asset Shepherd
root, and passes independent scene-root and payload verification. Invalid blank and clipped masks
fail before visual reassessment. A real Blender 5.1 fixture render produced four decodable views
with 3.4–7.1% foreground occupancy, 43–44% projected span, and 26–27% minimum frame margin.

Hosted route coverage proves actual tool labels progress from measurement through verification,
persist across restart, and contain no reasoning text. Browser inspection confirms one approval
table, one main title, approximately 17 px table body text, 28 px status controls, and 13 px 3D HUD
labels (11 px at the compact breakpoint). The common gate passes with 146 tests, one opt-in skip,
lock validation, Ruff, formatting, and zero Pyright findings.

### D053 — Make pivot placement a bounded agent-selected target condition

**Date:** 2026-08-25

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 agent-led sensing and disposition / M10 real-world evaluation

**Context**

The Computer Chip could be grounded at the project plane while retaining an inconvenient pivot on
its rear edge. Ground contact therefore did not establish a useful placement anchor. Wider pipeline
evidence also confirmed that glTF world bounds must include the complete hierarchy, attribute seams
must not be welded by position alone, render topology need not be watertight, and visual-evidence
failure must remain separate from structural or payload failure.

**Decision**

Expose the file world origin, world-bounds center, footprint center-bottom, and root origins as
objective measurements. The workflow agent—not a shape heuristic—may request one of three typed
states: preserve the authored pivot, put the world-bounds center at the origin, or put the footprint
center-bottom at the origin. The deterministic preview derives the exact translation and groups it
with any compatible approved root normalization. Grounding and pivot placement remain separate
recorded conclusions even when footprint-center-bottom satisfies both. Bounds-center plus grounding
is rejected as contradictory. Doors, wheels, hanging objects, rigs, and ambiguous mechanisms retain
their authored pivot or trigger clarification. Arbitrary translations are not exposed.

The ordinary-language target flow remains unchanged: the agent infers plausible intent and the user
confirms it. Requiring users to manually populate every possible contract field would conflict with
the approved minimum-information intake design. Stable authority and safety instructions remain
always present; specialist playbooks may later become just-in-time skills, but the current prompt is
not near its model context limit.

**Evidence and consequences**

Typed schemas bind pivot targets to explicit normalization components and reject incompatible
targets. Planner tests prove a footprint-center-bottom request becomes only the derived translation,
without invented scale or rotation. A full repair test writes a new GLB, reloads it independently,
and verifies the requested footprint anchor at the origin. The approval table keeps this action in
the existing Size and pose lane, and the What it does page now names pivot placement. The shared 3D
viewport projects the GLB origin as a minimal crosshair, with distinct before/after origin markers
after mutation, so the placement anchor is visible rather than only present in structured evidence.
Existing
source hashing, hierarchy-aware bounds, seam-aware topology stop rules, exact-tuple compaction,
payload preservation, and independent verification remain in force.

### D052 — Make the asset gallery the persistent workflow home

**Date:** 2026-08-25

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 hosted conversation UX

**Context**

A finished asset exposed an Assets link, but earlier workflow states relied on the placeholder logo
or browser navigation. The gallery resumed durable workspaces, but did not offer a clear way to run
the same source through a newly interpreted workflow.

**Decision**

Expose Assets as a persistent navigation control in the header and workflow rail. Returning to the
gallery never advances, resets, or mutates a workspace. Selecting a gallery card reconstructs the
workspace at its last persisted phase. An uploaded GLB awaiting description is also persisted and
appears in the gallery, including after application restart. Every completed workspace card exposes
Redo: it stages the same original GLB and prefills the prior description for a fresh intake. The
saved run remains intact until the new workspace is successfully created, at which point the new
run explicitly replaces that slot.

**Evidence and consequences**

Route coverage proves description drafts survive restart, approval and target-confirmation states
resume independently, Redo preserves the prior run until submission, the replacement receives a
new workspace identifier, and source bytes are identical. Browser review shows the seven-card
gallery retains three visual regions per card: model/state, Redo, and the existing full-gallery
Replace action.

### D051 — Use one inspection-lane table as the approval surface

**Date:** 2026-08-25

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 hosted conversation UX

**Context**

The approval screen repeated inspection state in a six-row checklist and a separate three-row
repair list. Users had to correlate two surfaces to discover what needed attention and what would
happen after approval.

**Decision**

Present exactly one row for each of five check lanes: GLB structure, size and pose, topology,
materials and textures, and display names. Each row owns its concise finding, status icon, and
proposed action. Status icons expose the explanation on hover and keyboard focus. Do not create a
synthetic `Repair plan` lane or a second repair table. Small measurements use adaptive metric units
so the finding remains readable.

The local OpenAI Responses adapter consumes a complete non-streaming response before leaving its
client context. It preserves the response identifier and tool-call events while avoiding the
non-fatal async stream-finalization warning observed after successful requests.

**Evidence and consequences**

Desktop and 390 px mobile browser checks show one table, five rows, no horizontal overflow, and no
console errors. The Computer Chip topology row now states that 5,312 coincident positions preserve
`TEXCOORD_0` seams and therefore proposes no weld. Targeted web and agent coverage passes with 44
tests and one opt-in skip.

### D050 — Fit approximate target boxes proportionally and explain unavailable welding

**Date:** 2026-08-25

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 agent-led sensing and disposition / M10 real-world evaluation

**Context**

The Computer Chip target was approximately 5 × 5 × 2 cm. The prior median-ratio uniform fit made
one axis exact, left expected residuals on the other two axes, and the candidate-reassessment agent
then incorrectly rejected the result because one residual did not equal the target. The same run
did not tell the user whether its 5,312 coincident positions had been welded. Engine clarification
also needed a focused, concise choice rather than generic missing-information copy.

**Decision**

Treat confirmed X/Y/Z lengths as one approximate target box after any agent-requested orientation.
Choose the single proportional scale that minimizes squared log-relative error across all three
axes: the geometric mean of the three target/source ratios. Preserve proportions and report every
residual. No individual axis is an exact acceptance requirement. Candidate reassessment may reject
new damage, a wrongly executed transform, or a genuinely worse fit, but not an expected residual
from the approved proportional best fit alone. Non-uniform scaling remains unavailable.

Inspection must state whether attribute-safe vertex compaction is available. If every coincident
position crosses a protected vertex attribute, the topology control explains that no weld is
proposed and names the protected seam class. If lossless compaction is planned, it appears as an
explicit repair item. Engine clarification says only `Select target engine.` and presents the three
canonical engines plus Other. Use product-neutral animated orbit glyphs and linked engine names;
do not animate third-party logos without the required trademark permission.

**Evidence and consequences**

The supplied `computer-chip-candidate.glb` has SHA-256
`8918f4642787ea98b15dbbe001d364e5dcf18e27e59bb1941cf206518d528ed0`, matching the run's rejected
candidate. Fresh inspection measures 5.000 × 4.452 × 1.732 cm and confirms 5,312 coincident
positions, zero attribute-safe merges, and `TEXCOORD_0` as the protected conflict. The file was not
welded: its vertex count and protected texture-coordinate seams were preserved. Planner tests prove
one geometric-mean scale is applied to all axes, prompt version 6 makes residual acceptance
explicit, and route coverage preserves the focused clarification flow.

### D049 — Ban redundant visible subtitles and normalize harmless provider orphans

**Date:** 2026-08-25

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 hosted conversation UX

**Context**

The Describe screen repeated its sole task with a visible `Model description` caption. A live
computer-chip intake also returned `endpoint=null` plus evidence explaining that no endpoint was
specified. The strict pair validator rejected the entire otherwise valid proposal instead of
letting the workflow ask only for the missing endpoint.

**Decision**

Default task screens may not show subtitles, field captions, or labels that merely restate their
single obvious task. Keep the textarea's accessible name through ARIA while removing the visible
caption. This is a project-wide design rule, not a one-screen copy exception.

At the semantic-provider boundary, discard evidence and endpoint detail attached to a field the
provider explicitly returned as null. Preserve the reported confidence and continue rejecting a
null field at or above the 0.8 confidence gate. A low-confidence unknown endpoint therefore becomes
the existing focused clarification state rather than a provider-validation error.

**Evidence and consequences**

Route coverage requires no visible `Model description` text while retaining its accessible name.
A reproduction of the chip response now produces a valid target contract whose only missing field
is `endpoint`. No target is invented and the schema, confidence gate, and server-owned validation
remain authoritative.

### D048 — Treat protected attribute splits as representation, not a repair decision

**Date:** 2026-08-24

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 agent-led sensing and disposition / M10 real-world evaluation

**Context**

The Computer Chip has 5,312 duplicate POSITION rows, but every potential merge crosses a
`TEXCOORD_0` difference. The user asked whether those merges could be exposed as a safe/unsafe
choice, then agreed that approval cannot turn texture-coordinate loss into a safe operation.

**Decision**

Treat duplicates separated by UVs or another protected vertex attribute as expected glTF
representation. Do not present their count as a defect, wasted data, or a repair choice. Continue
to refuse position-only welding. Show the read-only position projection separately and direct the
agent's topology explanation toward residual boundary, non-manifold, and winding evidence. Keep
lossless complete-tuple compaction available only when every attribute is byte-identical.

**Evidence and consequences**

The Computer Chip remains unchanged: 5,312 UV seam splits are ignored as repair candidates, while
the projected 91 boundary edges, 50 non-manifold edges, and 11 inconsistent shared edges remain
available for agent interpretation and downstream repair-tool planning. No topology reconstruction,
hole closing, normal recalculation, or destructive override is added.

### D047 — Separate virtual position welding from lossless vertex-tuple compaction

**Date:** 2026-08-24

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 agent-led sensing and disposition / M10 real-world evaluation

**Context**

The Computer Chip inspection contained 5,312 coincident positions. Blender's broad non-manifold
selection fell from 7,743 to 141 after a position weld, but that result alone did not prove the GLB
could be mutated without damaging its texture mapping. The user requested that Asset Shepherd detect
duplicate positions and repair them when possible. The user also clarified that target X/Y/Z metrics
are approximate fitting evidence and must never authorize non-uniform scaling.

**Decision**

Add two distinct deterministic topology facts. A read-only virtual weld groups exact POSITION values
to estimate underlying position topology. A stricter attribute-safe count groups only complete
byte-identical vertex tuples across every primitive attribute. Only the latter may become an
agent-requested `WELD_IDENTICAL_VERTICES` action. It is preauthorized as a lossless representation
compaction, never as topology reconstruction. Position-only welding, hole filling, remeshing, and
normal recalculation remain unavailable.

When confirmed X/Y/Z dimensions differ, treat them as approximate. Choose one deterministic median
uniform factor after any requested orientation change, preserve proportions, and record the residual
extent mismatch on all axes. Never expose or execute non-uniform scaling.

**Evidence and consequences**

The new sensor reproduces the chip evidence exactly: 7,811 source positions, 5,312 coincident
positions, a 2,499-position virtual projection, 91 boundary edges, 50 true non-manifold edges, and
11 inconsistently wound edges. It reports zero attribute-safe merges because all 5,312 duplicates
cross `TEXCOORD_0`; therefore Asset Shepherd does not weld this chip. A synthetic complete-tuple
duplicate compacts from five to four positions while preserving both triangles, all expanded
per-corner attributes, bounds, materials, resources, and glTF validity under independent
verification. Checked-in schemas and the on-demand job details expose the new provenance.

### D046 — Keep target intake API-compatible and move examples on demand

**Date:** 2026-08-24

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 hosted conversation UX

**Context**

Adding tight X/Y/Z targets changed the model-facing Pydantic field from one number to a fixed tuple.
Its generated JSON Schema used `prefixItems`, and the OpenAI Responses strict-output request failed
with HTTP 400 before the model could interpret any description. A successful structured response
could also redundantly populate `endpoint_detail` for a canonical Unity, Unreal, or Godot enum and
then fail the stricter server-owned semantic validator. The description screen exposed its three
examples through an unexplained question-mark control beside the field label.

**Decision**

Represent target dimensions at the model boundary as a closed `{x_cm, y_cm, z_cm}` object, then
convert it to the existing immutable tuple before constructing the target contract. Canonical
endpoint enums discard redundant model-authored detail; only `OTHER` may retain endpoint detail.
Provider failures keep diagnostics in server logs and show concise retry copy instead of raw HTTP
status language.

Replace the question-mark disclosure with a small **Show description examples** text link. It opens
one large native modal that first explains the four useful description clues and why they matter,
then gives exactly three examples: a rigged humanoid, a static prop, and an animated multi-part
system. The default screen does not gain another title or visible explanatory panel.

**Evidence and consequences**

The request-schema regression asserts that no `prefixItems` keyword is emitted. Analyzer tests cover
X/Y/Z conversion, canonical endpoint-detail normalization, safe 400/429 copy, and credential/body
redaction. A configured live OpenAI intake accepted a Unity humanoid description and redirected to
a durable workspace. Browser review confirms the plain link, modal sizing, lead explanation, three
examples, and absence of the former question-mark disclosure. The official OpenAI Responses API
continues to receive one strict JSON Schema request with `store: false`; the frozen target and
downstream deterministic authority boundary are unchanged.

### D045 — Freeze endpoint and three-axis target bounds; keep rejected candidates downloadable

**Date:** 2026-08-24

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 agent-led sensing / M10 evaluation

**Context**

A single target height can misdescribe wide, flat, or deep assets, while an engine-neutral target
omits useful Unity, Unreal, or Godot import expectations. A one-centimeter Computer Chip repair also
exposed two visual-review errors: Blender's fixed near-clipping distance made an isolated candidate
look absent, and a shared-scale source/candidate view could not by itself prove that a much smaller
candidate was missing. Automated rejection then made a mechanically valid candidate unnecessarily
difficult for its human owner to retrieve.

**Decision**

Version 3 target intent freezes the inferred endpoint as Unity, Unreal, Godot, or a described Other,
plus tight final-pose X/Y/Z bounds. The agent extracts these values from the user's description and
asks only when the minimum contract remains ambiguous. These are target-state dimensions, not raw
transform controls. Repairs remain uniform-scale-only; incompatible proportions are reported rather
than silently corrected with non-uniform scaling.

Visual reassessment uses three complementary evidence sets: isolated source views, isolated
candidate views, and a shared-scale comparison. Presence and appearance are judged from isolated
views; relative size is judged from the shared view. The local Blender acceptance camera derives
near/far clipping from measured bounds. Blender remains a local development and acceptance consumer,
not a hosted AgentCore dependency; the competition renderer remains a separate lightweight-runtime
decision.

An executed candidate rejected by automated verification remains directly downloadable under the
agent-assigned asset name. Download does not change the verification record, confer a verified or
project-ready label, or suppress diagnostics. The human may use the candidate or request another
agent turn.

**Evidence and consequences**

Strict schemas, intake tests, provenance tests, and route tests cover endpoint and three-axis target
state. A real 1 cm Computer Chip candidate renders visibly in an isolated 256 px Blender view after
proportional clipping; its deterministic preservation checks pass while its report-only topology
warning remains explicit. Browser acceptance exposes `Download candidate` before human acceptance,
and the route returns the exact candidate bytes as `computer-chip-candidate.glb` with private,
no-store headers. The official Khronos executable was not configured on this workstation, so that
optional validation layer was not rerun for this candidate.

### D044 — Public capabilities use three worker questions; yaw uses labeled visual evidence

**Date:** 2026-08-24

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 agent-led sensing / M10 evaluation

**Context**

Asset workers need a concise explanation of the defects Asset Shepherd looks for and why they
matter. A separate failure mode remained in orientation reasoning: the semantic front of an asset
can be obvious in an image while disagreeing with the file's declared forward direction. Bounds
and dominant extents cannot resolve that question.

**Decision**

Add a brain-icon **What it does** utility page organized around three questions: whether the GLB
will import, look as intended, and remain practical to ship. Keep the public page concise while the
existing authority document retains the exhaustive implementation detail.

Version the standardized render contract. In source glTF coordinates, +Y is up, +Z is forward, and
-X is right. Front/right/back/left renders identify camera positions +Z/-X/-Z/+X respectively.
The workflow agent compares semantic cues across all four views before requesting yaw. A clear
front on +X, -X, or -Z may request the corresponding typed Y-axis quarter turn; an already-correct,
symmetric, or ambiguous front requests no yaw. Deterministic code validates the typed action and
requires all four labeled views, but never invents the rotation. Existing cached renders without
the versioned coordinate contract are regenerated. Correct the former right/left source-axis labels.

**Evidence and consequences**

Route and focus-budget tests enforce one title and three public groups. Prompt and workflow tests
enforce glTF axis semantics, semantic rather than extent-based reasoning, and four-view evidence for
yaw. Blender scaffolding tests lock the source-to-Blender camera conversion. This adds no free-form
matrix input, automated yaw heuristic, or new mutation domain.

### D043 — The agent owns semantic assembly expectations; tools expose mesh health facts

**Date:** 2026-08-24

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 agent-led sensing / M10 evaluation

**Context**

After upload, **Piece count unspecified · valid GLB required** mixed a semantic target question with
an already-completed file-validity check. The inspector also lacked deeper facts about defective
edge relationships, fragmented index topology, unused vertices, and likely vertex-cache cost. Those
facts are useful to the workflow agent, but several are legitimate modeling choices rather than
universal failures.

**Decision**

The intake model derives an expected semantic piece count from the description. It defaults to one
and chooses a larger count only when the request clearly identifies a multi-object deliverable such
as a pair or set. The frozen target and asset-intent records preserve both the count and its concise
evidence. This count is not inferred from nodes, meshes, primitives, or edge-connected components,
and it does not authorize merge, split, or geometry repair.

Add a deterministic, read-only mesh diagnostic tool for triangle primitives. It measures boundary,
non-manifold, and inconsistently wound edges; edge-connected face components; unused and coincident
positions; average vertex reuse; and a FIFO-16 ACMR estimate. Non-manifold and inconsistent shared
edges are objective report-only defects. Unused data and very poor estimated cache locality are
report-only performance attention. Boundaries, component counts, coincident positions, and cache
estimates remain observations for agent interpretation because seams, hard edges, open surfaces,
and target hardware can make them intentional. No topology or optimization mutation is added.

Comparison fits use the viewer's camera interpolation instead of jumping. The optional banana
twirls into the shared scene and flattens before disappearing, with reduced-motion behavior honored.
Public downloads use an agent-derived asset-name slug; the contracted evidence ZIP keeps its
required internal `repaired.glb` name.

This decision supersedes D027 only where it prohibited an agent-authored semantic piece-count
expectation. D027's distinction between semantic pieces and structural counts, and its prohibition
on merge/split repair, remain controlling.

**Evidence and consequences**

Unit tests cover closed, non-manifold, duplicate/unused, and deliberately cache-hostile meshes.
Inspector tests prove typed measurements and report-only findings. Intake, provenance, prompt, and
route tests prove the semantic count is frozen and displayed without reintroducing structural-count
guessing. Browser acceptance proves plain Enter still inserts a line break, Ctrl+Enter submits, and
the comparison banana completes both animations. The diagnostic design follows established
concepts from Khronos glTF Validator, Blender and trimesh mesh diagnostics, and meshoptimizer's
cache metrics; actual target-GPU profiling remains authoritative for performance.

### D042 — Upload-first shepherding and a two-text screen hierarchy

**Date:** 2026-08-24

**Status:** ACCEPTED

**Decision owner:** User

**Milestone:** M9 hosted conversation UX

**Context**

The remaining form-led intake placed description and agreement before file selection, then combined
rules and upload in a nested two-step workspace. Its default view contained nine title-like texts:
the global page title, eyebrow, hero title, target subtitle, story disclosure, substep navigation,
step counter, panel title, and policy-card title. Those layers repeated workflow state instead of
helping the user perform the next action. The hosted rail also still showed Describe before Upload
and treated agreement as a visually separate phase even though objective GLB preflight is valid
without a target.

**Decision**

Make the authoritative public path **Assets → Upload → Describe → Shepherd**. Upload first validates
and stages one GLB and performs objective preflight only. Description then supplies the minimum
target contract. Target agreement and inspection both occur inside Shepherd, followed by any action
review, repair, verification, user feedback, and repeated agent turns. `/` redirects to the hosted
gallery so a stale form-led entry cannot become the apparent primary product.

Give every default screen one global workspace title and, only when useful, one agent-authored
informative sentence. Do not add visible eyebrow labels, step counts, nested section titles, card
titles, subtitles, context bars, or duplicate state summaries. Concise control labels and factual
row labels are not titles. Complete rules, evidence, and provenance stay available through closed
disclosures or the on-demand Job details dialog; a dialog may use the single accessible title it
needs.

Keep the historical form-led routes as the offline acceptance harness, but remove their visible
Rules/Upload sub-navigation and nine-title intake stack. Its deep intake link now renders one agent
sentence, the GLB control, and one collapsed **Review rules** disclosure.

This decision supersedes D041's Describe-before-Upload ordering and D012/D018 ordering for the
authoritative hosted surface. It does not change the agent/tool authority boundary, minimum target
contract, policy schema, supported actions, authorization, verification, or package contract.

**Evidence and consequences**

Route acceptance proves that `/` redirects to `/workspace`, the left rail orders Upload before
Describe, both start screens expose only one task, and neither contains any `h2` or `h3` title below
the one global `h1`. The staged GLB must pass extension, size, magic-byte, and parse validation before
description; refusal removes its temporary copy. The legacy intake likewise has one global title,
no subordinate heading elements, and retains complete profile values plus schema-validated advanced
fields inside disclosures. The seven-slot replacement remains destructive only after the new
durable workspace succeeds.

### D041 — Four-step hosted flow and one explicit approval surface

**Date:** 2026-08-24

**Status:** ACCEPTED

**Decision owner:** User

**Milestone:** M9 hosted conversation UX

**Context**

The hosted start screen combined the gallery, description, file upload, and replacement choice. At
approval, a second context bar and multiple headings repeated workflow position; the checklist
showed six results and then repeated those same six results in a tiny table. Attention icons did
not explain themselves, and the approval prompt said that three changes needed review while showing
only the physical normalization. A separate recorded-evidence question added another unrelated
control.

**Decision**

Use four hosted steps in the persistent left rail: **Assets**, **Describe**, **Upload**, and
**Shepherd**. The gallery only selects a new slot or resumes an existing workspace; description and
upload are separate screens; all inspection, action, approval, repair, verification, feedback, and
repeat turns remain in Shepherd. At seven assets, replacement is selected from the gallery before
description.

Each screen has one global title and no separate workflow context bar or approval subtitle. In Shepherd, show each of the
six checks once. A pass is a checkmark. An attention item uses a colored row and exclamation icon;
hover or keyboard focus on the icon explains the condition. Do not repeat the list as a status
table or display an obvious completed-count label.

At approval, show the exact selected plan in no more than three visible groups: physical
normalization, mesh display names, and node display names. Exact single-name changes stay visible;
larger name groups disclose their individual mappings on demand. Keep only Reject and Approve as
the decision controls. Remove the recorded-evidence question from the hosted product surface;
complete structured evidence remains available through **Job details**.

**Evidence and consequences**

Route acceptance proves gallery-only, description-only, and upload-only states, the four-step rail,
one six-row checklist with six hover explanations, no duplicate result table or count, three visible
change groups, and absence of the recorded-evidence control. Live browser review of the persisted
Polar Robot Puppy approval shows the active Shepherd step, one title, colored attention rows, and
the exact scale, mesh-name, and node-name changes before the decision buttons. Target inference is
performed once during the description transition and carried into upload; durable workspace and
Strands session state still begin after the GLB is accepted.

### D040 — Each named asset is one resumable conversation

**Date:** 2026-08-24

**Status:** ACCEPTED

**Decision owner:** User

**Milestone:** M9 hosted conversation UX

**Context**

The hosted completion view repeated its outcome as a large heading, a status card, and a dense
recap. The persistent Job Contract occupied a narrow right column, while returning users had no
visual list of processed assets. Filenames and opaque IDs stood in for asset identity even though
the intake agent had enough context to name the described model. The existing hosted runtime
already scoped Strands session storage by workspace ID and did not need another conversation store.

**Decision**

Make the hosted home a seven-slot visual asset gallery. The first semantic intake turn assigns a
concise asset name from the user's description; the deterministic offline analyzer supplies a
bounded fallback. A card resumes the exact durable workspace phase and source preview. Creating an
eighth workspace requires the user to select one of the visible seven to replace; no workspace is
silently evicted.

Keep each asset's existing `workspace_id` as its server-side conversation/session authority and
retain the workspace-owned `strands_state` directory. Do not introduce a shared transcript or a
second session database. Move the structured Job Contract into a modal opened by **Job details**.
At completion, show one compact sentence from the workflow agent instead of the prior headline,
status card, and recap; comparison, review, fixed-model download, and evidence remain available.

**Evidence and consequences**

Tests prove stable intake names, seven-slot enforcement, explicit replacement, gallery previews,
exact-state resume, distinct Strands session roots, one completion sentence, the details dialog,
and the existing inline acceptance transition. Existing records without a name derive a bounded
compatibility label and fall back to **Untitled asset** only when none is usable. Replacement is
destructive only after the new upload and preflight have been persisted successfully. Live browser
review showed seven rendered GLB cards,
resumed a pending approval, opened and closed the modal contract, and confirmed that Yes reveals
the fixed-model download at the same URL.

### D039 — Inspection progress and acceptance stay in the conversation

**Date:** 2026-08-24

**Status:** ACCEPTED

**Decision owner:** User

**Milestone:** M9 hosted conversation UX

**Context**

The active conversation route called its first action **Measure my asset**, omitted the progressive
inspection checklist already present in the form-led route, and handled result acceptance with a
full-page redirect that changed little on screen. The wording understated the agent workflow, the
missing checklist hid useful progress, and the acceptance reload interrupted the final handoff.

**Decision**

Call the action **Shepherd this asset**. Reuse the shared six-row inspection checklist in the hosted
conversation, replaying structured results from checking to pass, attention, or blocked status and
keeping row details collapsed. Persist **Yes** asynchronously and replace the question in place with
**Ready to download**, a direct fixed-GLB action, and a secondary evidence-package link. Retain the
ordinary POST/redirect path as the no-JavaScript fallback.

**Evidence and consequences**

Route tests cover the new copy, shared checklist, durable 204 acceptance transition, and accepted
download state. Live browser review confirmed that the URL does not change when Yes is selected,
the question disappears, the fixed-model and evidence actions appear, the six checks resolve, the
390 x 844 layout has no horizontal overflow, and browser diagnostics are empty.

### D038 — Repair is a bounded user-agent loop, not a two-pass workflow

**Date:** 2026-08-23

**Status:** ACCEPTED

**Decision owner:** User

**Milestone:** M9 durable agent conversation

**Context**

The D037 checkpoint completed one agent-authored action and visual reassessment, but its handoff
described the remaining work as a “second repair.” That wording implied a special retry. The product
requires an ordinary conversation: intake, analysis, repair attempt, user feedback, and as many new
evidence/decision turns as the configured usage allowance permits.

**Options considered**

- Add one hard-coded correction attempt after verification.
- Keep each attempt as a separate job and lose conversational/authorization continuity.
- Treat every completed candidate as a versioned state in one append-only conversation, with a
  configurable turn limit and a completely fresh action/approval boundary on every iteration.

**Decision**

Use the third option. A completed turn may be accepted or continued with up to 1,000 characters of
user feedback. Continuation archives all current output and rendered evidence, makes that turn's
candidate the next immutable source, resets per-turn assessment/plan/decision/verification state,
and invokes the same stateful Strands agent. Every consequential mutation therefore needs a new
assessment, typed preview, action hash, interrupt, approval, execution record, candidate
reassessment, and independent verification.

Freeze a per-job maximum from `ASSET_SHEPHERD_MAX_TURNS`, defaulting to five and validating the
range 1–50. The limit is persisted and restored rather than changing with the server environment.
Both the form-led result and durable hosted workspace ask only **Did we get it right?** Yes closes
the conversation; No reveals one feedback field and starts another turn when allowance remains.

Use `turns/turn-NNN/` for immutable prior output, assessments, and model-visible render evidence.
Persist ordered turn records in `conversation.json`, runtime state, hosted structured events, and
the current `provenance.json`. Records link source/output hashes, plan and assessment IDs,
verification state, result-ZIP hash, and continuation feedback. The current seven-file ZIP contract
does not expand; its provenance carries the prior-turn chain.

**Evidence and consequences**

The regression suite completes three ordinary turns, proves that each repaired GLB becomes the next
source, restores the current turn and frozen limit after reconstructing `AgentJob`, and rejects a
turn beyond the allowance. Existing authorization, source-preservation, schema, web, hosted,
restart, and package tests remain passing. `docs/AGENT_LOOP_FLOW.md` records the loops, resources,
tools, allowed mutations, durable state, and stop conditions.

A live hosted OpenAI Responses run also exercised **No** plus feedback after a clean verified turn.
The runtime archived the complete turn-0 package and source renders, promoted its candidate, ran a
fresh turn-1 inspection, and produced new provenance with one ordered prior-turn link. Browser
review passed at desktop and 390 x 844 without overflow or browser diagnostics.

Turn count is the implemented local usage guard. Provider token, time, and cost ceilings remain
deployment configuration and must fail closed. Changing the confirmed target or project rules is
not repair feedback; it still creates a new job and inspection.

### D037 — Live model authors the first repair preview and reassesses the candidate

**Date:** 2026-08-23

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 agent-orchestrated planner checkpoint

**Context**

D036 established that semantic height, pose, grounding intent, and repair choice belong to the
workflow agent. The implementation still filtered a target through a deterministic planner that
equated longest extent with vertical. The resulting quadruped was rotated onto its back, and the
same heuristic then declared the mistake correct. The interim Luna intake call had never inspected
the GLB or viewed a render.

**Options considered**

- Patch the quadruped orientation heuristic while retaining automatic grouped normalization.
- Let the model veto deterministic candidates after they are manufactured.
- Give the live Strands model objective measurements and standardized views, require one typed
  evidence-cited disposition/action request, compute only its exact bounded preview, and require a
  second model-visible source/candidate comparison before invariant verification.

**Decision**

Use the third option. In agent mode, legacy height, dominant-axis orientation, and grounding
findings are removed from the observation surface. The model chooses semantic height axis and each
supported scale, quarter-turn rotation, grounding, and display-name component. The preview layer
rejects malformed, no-op, uncited, repeated, unsupported, or non-repair action requests and never
adds a component. Consequential execution retains the exact Strands interrupt and approval hash.

For the authorized local transition, use the stateful OpenAI Responses adapter with
`gpt-5.6-luna`/xhigh until Bedrock is configured. Four local Blender source renders are tool-visible
evidence for physical conclusions. After execution, four new candidate renders must be compared by
the model and recorded before deterministic verification can run. Both assessments and their
originating Strands tool-call IDs are embedded in final provenance; the contracted ZIP filenames do
not change. The scripted provider remains a legacy/offline test double.

**Evidence and consequences**

The fresh quadruped run identified source Y as its 0.463 m standing height and Z as body length,
producing scale only and preserving its already upright, grounded pose. A separate paid live fixture
run completed inspect, render, plan, approve, execute, candidate render, visual reassessment,
independent verification, and seven-file packaging. The suite passes with 116 tests and one opt-in
skip.

This decision completes the first action loop; D038 generalizes it to an arbitrary bounded number
of versioned feedback/action turns. Ambiguous-orientation and materially changed-goal live
evaluations remain required. The non-fatal OpenAI/httpcore streaming-generator close warning observed after
interrupted Responses runs remains a dependency-level diagnostic to isolate before deployment.

### D036 — The agent owns sensing, assessment, disposition, and repair choice

**Date:** 2026-08-23

**Status:** ACCEPTED

**Decision owner:** User

**Milestone:** M9 hosted agent architecture correction

**Context**

The grasshopper-sized quadrupedal robot run exposed the actual authority error. The source was
already grounded on Y, but the deterministic inspector equated its longest Z extent with semantic
vertical, emitted `ORIENTATION_NOT_Y_UP`, created a rotation, and later verified success by checking
that the same longest extent had moved to Y. The intake model had inferred only use and size; the
scripted workflow did not visually reason about the model or choose the repair. Fixing that one
orientation heuristic would leave the same mistaken architecture in place for scale, grounding,
naming, assembly, and future tools.

**Options considered**

- Add a quadruped-specific orientation exception or improve the dominant-axis heuristic.
- Keep deterministic planning but allow the agent to veto generated candidates.
- Make deterministic components sensors, bounded action capabilities, enforcement, and proof while
  the agent chooses what to inspect, what the evidence means, what disposition to take, and which
  supported action and parameters to request.

**Decision**

Adopt the third option. `docs/AGENT_ORCHESTRATED_WORKFLOW.md` is the controlling start-to-finish
architecture. Sensors return observations without contextual verdicts. The workflow agent forms and
revises target-dependent conclusions, chooses whether to accept, investigate, ask, report, repair,
or stop, and initiates every mutation. The agent may call bounded preview tools for supported scale,
rotation, translation, grounding, and display-name primitives and compose them into an exact proposed
action. Deterministic code calculates consequences, validates schemas and capability limits, binds
approval, applies the authorized action, verifies invariants and declared postconditions, and
packages evidence. It never adds an unrequested variable fix.

Universal invariants remain non-negotiable and may block any call, but even a preauthorized
non-consequential mutation begins with an explicit agent tool call. Consequential actions retain exact
structured user approval. Standardized before/after renders become agent-accessible sensor evidence;
the browser comparison remains available to the user. After each mutation the agent re-observes the
candidate and may continue through fresh sensing and a fresh approval turn within explicit
operational limits.

The scripted provider remains a deterministic test double only. It cannot prove agent behavior. A
representative live workflow model must pass the corrected acceptance gate before M9 is complete.

This decision supersedes the deterministic semantic-planning and fixed-sequence portions of D002,
D018-D023, D026-D027, and D032-D034. Their durable state, target confirmation, narrow repair scope,
content boundary, exact authorization, source preservation, and independent-verification decisions
remain active. D035's viewer implementation remains useful, but its renders must also become recorded
sensing artifacts rather than user-only decoration.

**Evidence and consequences**

The controlling contract is amended to version 1.5, the agent operating contract is rewritten, and
the complete product path plus ten-part acceptance gate are documented. The present deterministic
prototype is now explicitly classified as a repair-engine test harness, not evidence that the
product is agent orchestrated.

Implementation has not been silently claimed. The next local milestone must separate sensor facts
from agent assessments, replace auto-generated candidates with typed action previews initiated by a
real model, provide rendered evidence to that model, and prove multi-turn reassessment. Existing GLB
scope and mutation primitives remain narrow; no topology, material, texture, rigging, animation,
Blender-hosting, or Unreal-plugin scope is added.

### D035 — One shared comparison scene uses the viewer's supported camera and transform syntax

**Date:** 2026-08-23

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 hosted conversation

**Context**

The completed workspace rendered metric axes, banana annotation, and HUD target boxes while both
GLBs were invisible. The HUD uses measured bounds and therefore remained plausible even when the
WebGL camera was invalid. Isolated browser probes proved both GLBs were valid and independently
renderable. The pinned `model-viewer` fork parses `extra-model` offsets with `Number`, so values such
as `1.5m` are invalid, and its former extreme `min-camera-orbit`/`max-camera-orbit` attributes put
the primary camera into a state where a loaded model did not draw.

The same approval state also repeated one decision across a headline, explanatory card, two metric
tiles, and buttons even though the exact component evidence can remain progressive detail.

**Decision**

Keep source, repaired candidate, and banana in the existing single shared `model-viewer` scene.
Supply plain numeric offsets to `extra-model`, including dynamic banana placement; remove the
unsupported orbit-limit attributes; and eagerly load this one result comparison. Keep fit controls,
metric axes, target boxes, shared rotate/pan/zoom, and the banana toggle unchanged.

Present normalization approval as one compact exact question plus Reject/Approve. Put component
evidence behind one `Details` disclosure and remove duplicate before/target tiles and source-file
reassurance.

**Evidence and consequences**

Rendered desktop acceptance shows source and repaired GLBs together at their measured relative
scales. Both, Before, and After fits execute; axes and the 20 cm banana toggle on; dynamic banana
offsets remain numeric; and browser diagnostics report no warning or error. A 390 × 844 pass keeps
the models, controls, HUD labels, and interaction hint within the viewport. Route tests enforce one
viewer, two numeric extra-model offsets, compact approval copy, one detail disclosure, and absence
of the removed reassurance.

The comparison remains a browser preview rather than verification evidence; deterministic and
independent verification continue to decide package readiness.

### D034 — Prose explains; structured controls decide

**Date:** 2026-08-23

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 hosted conversation

**Context**

The version-1 workflow prompt was primarily a seven-step tool script. It protected execution order,
but did not adequately teach the model the user's goal, distinguish explanatory prose from interface
controls, define the product's voice, carry the confirmed target into the run, or resist instructions
embedded in user and asset data. Tool descriptions were too short to tell a hosted model their
prerequisites, important outputs, and failure behavior.

**Decision**

Adopt the version-2 operating contract in `docs/AGENT_OPERATING_CONTRACT.md`. Treat the model as a
technical-art collaborator for one existing GLB. Keep the initial model description as the primary
open text input and use structured choices and buttons for later decisions. Let the model produce
free-text explanations of inference, evidence, failure, and next action, but never let prose approve
a repair, alter the Job Contract, or override a deterministic result.

Keep stable role, authority, tone, cross-tool order, stop conditions, topic limits, and private
content boundaries in the system prompt. Put exact tool behavior in concise tool descriptions. Append
the confirmed target and frozen policy as delimited JSON job data, explicitly untrusted as
instructions. Share the same prompt-injection and content boundary with the interim semantic-intake
model. New runs record prompt version 2 while old version-1 results remain loadable.

**Evidence and consequences**

Focused zero-network tests prove version provenance, stable/dynamic separation, confirmed intent and
policy delivery, prompt-injection treatment, shared refusal behavior, and the unchanged native
Strands approve/reject/verify flow. The public artifact schema accepts prompt versions 1 and 2 and
defaults new records to 2.

This establishes the contract a live Bedrock model must follow; it does not claim that the current
scripted hosted harness produces model-authored prose or that live conversational quality has passed
evaluation. Representative live traces remain required at the existing AWS checkpoint.

### D033 — The Job Contract owns conversation state across model providers

**Date:** 2026-08-23

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 hosted conversation

**Context**

The interim Luna integration uses OpenAI's Responses API, but an API endpoint and a coherent
multi-turn product are different things. The current intake request has `store: false`, supplies no
previous response or conversation identifier, and sends only the normalized asset description.
Luna proposes the typed intake fields once; it does not see GLB measurements, findings, plans,
decisions, verification, or later evidence questions. Meanwhile, the hosted scripted Strands path
already persists snapshots, but the Bedrock factory did not accept the same session configuration.

**Decision**

Keep provider conversation storage non-authoritative. The durable Job Contract, typed artifacts,
minimized event ledger, exact approval state, and Strands snapshot are the coherent picture of the
job. Model turns may consume that state and produce explanations or tool choices, but neither an
OpenAI response chain nor Bedrock-side history may replace it.

Keep Luna's current role explicitly limited to one-shot semantic intake. A future Luna-based full
conversation test must pass forward the relevant structured Job Contract and bounded recent turn
state; merely adding `previous_response_id` is not sufficient. When moving the workflow model to
Strands/Bedrock, construct the live agent with the same explicit session ID and isolated snapshot
storage contract used by the offline hosted runtime.

**Evidence and consequences**

Both scripted and live-agent factories now use one provider-neutral snapshot-session builder. It
requires both a session identity and an isolated storage root or fails closed. The opt-in Bedrock
test supplies those values, while zero-network tests validate the configuration contract without
credentials or model calls.

This wiring makes durable Bedrock conversation available, but the hosted application still uses
the scripted model until the contract's AWS profile, model access, region, cost, and live acceptance
conditions are satisfied. The current Luna intake must not be described as an end-to-end agent
conversation.

### D032 — Post-transform rules are planned up front; failed candidates are reassessed

**Date:** 2026-08-23

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M7 agent correction / M9 conversation and web product

**Context**

A grounded Z-up asset could receive an approved scale-and-orientation normalization whose rotated
bounds crossed below Y=0. The planner considered grounding only when the source inspection already
contained `NOT_GROUNDED`, so it omitted the translation created by its own rotation. Verification
correctly rejected the candidate when a fresh planning pass found one remaining repair. The
scripted agent then called its nominal correction tool, but that tool only reapplied the identical
authorized matrix and could never resolve a newly discovered post-repair condition. The final web
screen collapsed this verification failure into the same **Blocked / inspection-only** copy used
for unsupported source content.

**Decision**

Derive grounding from the bounds produced by the complete proposed scale-and-orientation matrix.
When ground contact is required, include grounding in the one grouped normalization whenever those
post-transform bounds fall outside tolerance, even if the original asset was grounded.

Replace the same-plan retry with one bounded candidate reassessment. The Strands agent calls a
deterministic tool that reloads the failed candidate, runs inspection again, and derives a fresh
registered plan. It never reuses the earlier approval and never executes the new plan silently. A
new consequential transform must be presented through a new explicit approval turn before a future
repair iteration may run. The deterministic core continues to own measurements, matrices, binary
mutation, verification, and packaging; the model owns tool sequencing, explanation, and approval
pause/resume.

Render verification failure as its own result state. Show the exact failed check and measured
post-repair finding, label the ZIP as diagnostics, and expose the failed GLB only as a clearly
marked **candidate not ready** comparison preview. Keep the shared camera, targeting HUD, fit modes,
metric axes, and banana scale aid available for diagnosis. Never package or label that GLB as
project-ready.

**Evidence and consequences**

The exact elephant-scale quadruped source now produces a normalization containing scale,
orientation, and derived grounding. A local rerun completes `PASSED_PROJECT_READY`, measures 3.5 m
on Y, places minimum Y at exactly 0, and produces an empty second plan. A regression fixture starts
grounded and Z-up, proves the source has no `NOT_GROUNDED`, and verifies the repaired result is
Y-up, grounded, and idempotent.

The previously persisted failed workspace remains useful negative evidence. Browser acceptance now
states that 30 checks passed, grounding remained at -1.75 m, and `SECOND_PLAN_EMPTY` expected 0 but
observed 1. It labels the candidate rejected, withholds it from the ZIP, and renders source plus the
rejected candidate in the shared viewer. The bounded-agent test proves verification runs once, the
failed candidate is reassessed once, the old plan is not reapplied, and the job remains failed.

This change does not authorize chained physical mutation under an old decision. A complete second
repair iteration still needs a versioned approval/provenance link before execution; until that
exists, reassessment ends with diagnostics and an explicit fresh-approval requirement rather than
a false retry.

### D031 — Repaired assets share one spatial before/after viewer

**Date:** 2026-08-23

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 conversation and web product

**Context**

Completed repairs were shown in two unrelated viewers. Separate cameras obscured the physical
scale change and made visual comparison harder, especially when normalization made one model tiny
relative to the other.

**Decision**

When at least one repair executes and the candidate passes verification, show source and candidate
in one `<model-viewer>` scene. Preserve each model's real scale and place the candidate to the
right of the source with a scale-relative gap. Provide three explicit fit targets—both, before, and
after—using the same orbit, pan, and zoom camera.

Project each model's world-space bounds into a minimal screen-space schematic overlay. Camera
changes update targeting corners, labels, and leader lines. If either model's longest dimension is
less than 18% of the other's, identify it as **Before model here** or **After model here** rather
than allowing it to disappear visually.

Add two optional scale aids. Metric X/Y/Z rulers follow the selected fit bounds and use 1/2/5
intervals with five major ticks per axis. **Banana for scale** loads a deterministic stylized GLB
at ordinary banana size (approximately 20 cm along its curve). Both aids are display-only and do
not enter repair or verification artifacts.

Serve the existing Google `<model-viewer>` 4.3.1 dependency from the application instead of a
public CDN. Preserve its Apache 2.0 license beside the unchanged distribution.

**Evidence and consequences**

Route acceptance covers the single shared scene, three fit modes, projected HUD hooks, local
viewer dependency, metric ruler logic, and the banana asset's measured size. Browser evidence
covers the very large source versus 1.8-meter candidate: the small candidate remains targeted in
the combined view; After fit recenters it; the axes change to 0.5-meter intervals; and the banana
overlay reports 20 cm. The source GLB, repaired GLB, contracted ZIP, repair authority, and
verification gates are unchanged.

### D030 — Public help explains the task, not the release

**Date:** 2026-08-23

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 conversation and web product

**Context**

The help page ended its workflow explanation with a product-version heading, an implementation
scope inventory, and a repair-domain caveat. Those facts describe the prototype to its builders;
they do not help a person understand what to do with an asset.

**Decision**

Public help is task-oriented and limited to three steps: describe and upload, review what was
found, and download the result. It does not present release numbers, roadmap framing, internal
tool names, provenance terminology, or a generic repair inventory. Limitations appear in the
workflow only when a particular asset or requested outcome makes one relevant.

Remove implementation version labels from the active-rule proposal and user-visible finding
descriptions as well. Versioned policy and artifact metadata remain unchanged in durable records;
only their unsolicited presentation is removed.

**Evidence and consequences**

Route acceptance requires exactly three help steps and rejects the removed scope, version, tool,
and provenance copy. Desktop and mobile browser checks cover the rendered hierarchy and overflow.
Deterministic checks, repair eligibility, authorization, verification, packaged evidence, and
policy versioning are unaffected.

### D029 — Inspect is one progressive result, one summary, and one question

**Date:** 2026-08-23

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 conversation and web product

**Context**

Inspect exposed three dense columns containing target assumptions, measured facts, previews,
findings, policy evidence, and proposed actions. The surrounding page then repeated the target
story and workflow navigation. Accurate evidence was competing with the one conclusion and one
decision the user actually needed.

**Decision**

Present Inspect as exactly three sequential areas. First, replay the completed deterministic work
as one compact check log: each row briefly says **Checking …** and resolves to a green check or an
attention marker. Second, generate a concise structured summary containing measured size,
topology, and resources, one compressed sentence for normal domains, and no more than three grouped
attention areas. Third, ask **Do these issues look fixable?** before exposing the repair decision.
Direct navigation or submission to Decide remains gated until that acknowledgement.

Keep the complete expectations, findings, rule provenance, measurements, plan candidates, stages,
frozen policy, and preview in one closed **More details** table. Remove the repeated target-story
panel, duplicate Inspect/Decide/Download rail, redundant section headings, and public copy about
internal source or guardrail mechanics. Internal authorization, unsupported-domain, mutation, and
verification invariants do not change.

Both upload controls now say **Choose or drop your GLB**. Click-to-choose and Windows Explorer drop
share one validated file state; a drop must contain exactly one `.glb`. If semantic intake is
declined, create no job or uploaded-file copy and show only a concise refusal, such as **Sorry, I
can't engage with this type of content. Let's work on something else.** Exact punctuation is not a
contract.

**Evidence and consequences**

Route acceptance proves the three-area result hierarchy, closed details, acknowledgement gate,
concise decline response, no declined-content storage, and shared chooser/drop implementation. A
real-browser run with the broken fixture confirms the progressive check transition, three grouped
attention areas, hidden 48-row detail table, preserved chooser path, and empty browser diagnostics.
At 1366 × 900 the confirmation question appears in the same working view; at 390 × 844 the page has
no horizontal overflow and the opened table scrolls within its own container. No repair operation,
policy field, model authority, artifact contract, or acceptance behavior is added.

### D028 — Apply progressive rule-of-three disclosure and one contextual feedback path

**Date:** 2026-08-23

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 conversation and web product

**Context**

The target proposal rendered six assumption cards, provenance labels, explanatory text, a separate
evidence disclosure, confirmation, correction, restart, and implementation notes on one surface. Although
the facts were accurate, the interface exposed the implementation taxonomy and required too much
simultaneous reading and choice.

**Decision**

Present exactly three closed groups: **Purpose**, **Scale and pose**, and **Structure**.
Each group shows one agent-written conclusion and reveals at most three supporting facts only after
the user opens it. Replace the competing controls with one question, **Did I get it right?**, and
two answers: continue to inspection or edit the prefilled description and try again. The same text
may be resubmitted to request a retake.

Add one reusable `/feedback` page. Links provide an allowlisted workflow context, an opaque local
reference, and a safe app-local return path. The page offers four bounded reasons and an optional
1,000-character note. Development feedback is written atomically below the configured work root;
no network service, credential, analytics SDK, or new product authority is introduced.

**Evidence and consequences**

Route acceptance verifies the three-group budget, binary decision, reusable feedback context,
reason bounds, note limit, and local JSON record. Desktop and 390 × 844 browser review show the
complete default decision surface without horizontal overflow or browser warnings. Existing typed
target, deterministic inspection, exact repair authorization, source preservation, and independent
verification behavior remain unchanged.

### D027 — Replace use-mode selection with an expectation-to-evidence contract

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 conversation and web product

**Context**

The target-adjustment UI exposed `static game asset`, `rig-ready character`, and `playable animated
character` in a dropdown. That presentation made them look like validation presets with different
repair behavior. They are not. The current repair engine has one static-GLB domain; non-static
intent is retained only to state the narrowed external handoff honestly. The same screen also made
it difficult to distinguish assumptions inferred from a user's description, universal safety
invariants, measured GLB facts, and the resulting plan.

**Decision**

Remove the intended-use dropdown from confirmation, clarification, and the hosted workspace.
Corrections are natural-language edits that run through the same schema-validated analyzer. Before
upload, list every active target assumption with its source and list the universal checks
separately. After inspection, organize the active view into three areas: target expectations,
deterministic GLB observations, and findings plus action plan. Label finding authority in public
language. If the registered plan is blocked, explicitly recommend returning to the model creation
or export tool with the recorded reasons.

Intended use remains typed provenance and a support-boundary input, not a repair preset. Static
intent receives the full supported workflow. Character intent receives static inspection and an
external rigging/animation handoff. Assembly expectations remain explicitly unspecified: the tools
report roots, nodes, meshes, and primitives, but no semantic piece count is invented and no
merge/split repair is added.

**Evidence and consequences**

Route acceptance proves that complete and missing-intent screens contain no target-use selector,
natural-language reinterpretation updates the typed proposal, and inspection renders assumptions,
measured assembly facts, finding authority, candidates, report-only warnings, and blocked handoff.
The full offline suite passes with 100 tests and one opt-in live-provider skip. Desktop and 390 × 844
browser review show the expectation sheet without horizontal overflow; the compact document width
is 375 pixels inside a 390-pixel viewport.

No new repair type, model authority, transform control, topology operation, or GLB mutation is
introduced. A future semantic assembly contract must define measurable evidence before it can
become a finding or repair goal.

### D026 — Check authority is explicit and validation is layered

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** Codex

**Milestone:** M10 evaluation strengthening

**Context**

The product already separated model proposals from deterministic repair authority, but findings and
verification did not make that distinction uniformly visible. The selected Python glTF validator
also covers only part of the specification, and count-only preservation cannot prove that material,
texture, accessor, or binary content remained unchanged.

**Decision**

Classify every finding and verification check as a frozen project-policy assertion, universal
invariant, objective source diagnostic, or external-consumer evidence. Preserve exact policy-rule
sources on findings. Add direct primitive/accessor and resource-graph diagnostics, deep semantic
section and binary-payload preservation checks, an optional pinned official Khronos validator
adapter, and typed equally-framed render comparison. Keep all newly detected topology/resource
issues report-only unless they violate glTF validity or an existing universal safety rule. Add no
repair operation.

The LLM remains limited to proposing supported intended use and semantic target height. Those
values pass a confidence gate and explicit user confirmation before becoming policy. Universal
validity, authorization, and preservation checks cannot be changed by the model, the user's target
description, or advanced policy fields.

**Evidence and consequences**

Acceptance tests distinguish model/user-derived policy findings from universal blockers, corrupt
attribute cardinality and topology intentionally, and prove that a parseable material mutation
fails deep preservation. The official validator reports zero errors for the clean fixture and the
same two pre-existing `ACCESSOR_MIN_MISMATCH` errors for untouched Patchling and Shader Lantern.
The strengthened Shader Lantern workflow introduces no official errors and retains them as explicit
source warnings. Typed render comparison reproduces the established four-view maximum MAE of
0.081863/255 for raw versus Shepherd and 0.000334/255 for Shepherd versus Blender re-export.

The native validator is an optional local/release tool, not a Python or hosted Blender dependency.
If configured, failure to execute it fails verification. A source-retained official error prevents
a zero-error conformance claim but does not authorize out-of-scope accessor repair.

### D025 — Target confirmation uses space for readable scale and optional rationale

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 semantic-intake presentation

**Context**

The concise target confirmation was understandable, but its 920-pixel content cap forced a very
large headline into narrow lines and left substantial workspace unused. Tiny objects were also
shown as decimal meters, such as `0.02 m`, rather than in the unit a person would naturally scan.

**Decision**

Use a wider confirmation canvas and a smaller, bounded headline scale. Format sub-centimeter
targets in millimeters, sub-meter targets in centimeters, and larger targets in meters while
preserving canonical centimeters in the contract. Keep the primary view minimal, but add one
collapsed **Why this target?** disclosure containing the already-recorded use and scale evidence
and a reminder that the proposal is interpretation, not source measurement.

**Evidence and consequences**

Route acceptance covers readable unit selection, model evidence, the source-measurement boundary,
and unchanged adjustment/confirmation behavior. Browser review covers the wider layout, attention
budget, disclosure behavior, and horizontal overflow; the existing compact breakpoint stacks the
decision row and makes its action full-width. No additional model call, policy field, repair scope,
or authorization behavior is added.

### D024 — One-command Windows launcher protects the local OpenAI key

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 local semantic-intake ergonomics

**Context**

The user cannot reliably paste multiline PowerShell commands and should not need to place a raw API
key in command text, shell history, a repository file, or a persistent environment variable.

**Decision**

Provide two repository scripts, each invoked with one line. `Save-OpenAIKey.ps1` reads the key through
a hidden secure prompt and stores only Windows current-user protected ciphertext under local app
data. `Start-AssetShepherd.ps1` unlocks it for the same Windows user, makes it available to the web
process for the duration of the command, restores any prior process state in `finally`, and clears
the temporary byte buffers. No key material or encrypted secret is written inside the repository.

**Evidence and consequences**

Both scripts pass Windows PowerShell 5.1 parser and runtime validation. Static acceptance requires
hidden input, current-user data protection, an external local-app-data path, scoped environment
injection, and cleanup. This is a local Windows development convenience, not the production secret
mechanism; Bedrock deployment must use the approved hosted secret-management design.

### D023 — Provider-neutral semantic intake uses OpenAI Luna until Bedrock

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9 conversational intake

**Context**

The D022 explicit-text extractor made the entry screen look like a questionnaire: descriptions such
as “a mountain of goop” produced two required fields even though an LLM can propose a reasonable
game use and semantic scale. The repository already used Strands for workflow sequencing, but the
running intake path did not invoke a model. The user authorized interim paid OpenAI API use with
`gpt-5.6-luna` at `xhigh` reasoning and directed that Bedrock replace it later.

**Decision**

Add a provider-neutral `TargetIntakeAnalyzer` boundary. The normal CLI web process uses the OpenAI
Responses API with `gpt-5.6-luna`, `xhigh` reasoning, low answer verbosity, strict structured output,
and `store: false`; `--offline-intake` retains the deterministic explicit-text acceptance path.
Only the normalized description is sent to the intake provider, never the GLB. Server code validates
the returned `TargetIntakeInference`, applies the existing 0.8 confidence gate, and constructs
`TargetIntakeContract` itself. Provider and model identity are retained in that contract.

The model should propose a supported use and plausible semantic vertical height whenever one
interpretation is useful enough for confirmation. It asks a natural-language follow-up only when a
required field remains genuinely ambiguous. The proposal is not a fact or authorization: the user
may adjust it and must explicitly confirm it before policy inspection. Model output cannot specify
transforms, policy safety settings, repair candidates, approvals, mutation, verification, or
readiness. Bedrock will implement the same interface and schema rather than changing downstream
contracts.

**Evidence and consequences**

Mock-transport acceptance verifies the exact Luna/xhigh structured request, semantic use/scale
proposal, confidence fallback, safe provider errors, and credential-free offline selection. Web and
durable-workspace acceptance verify concise questions, editable proposals, persisted analyzer
provenance, restart-safe adjustments, and exactly-once commands. This changes intake collaboration
only; the deterministic workflow, policy family, explicit physical approval, source preservation,
and repair scope are unchanged.

### D022 — Minimum target-intake contract asks only for unresolved required information

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M8/M9 conversational intake correction

**Context**

The intent flow should feel like an agent understanding what the user is trying to make, not a
fixed questionnaire that repeats information already present in the description. At the same time,
the deterministic policy resolver cannot safely derive a physical normalization without an exact
intended size, and source measurements describe what the file currently represents rather than what
the user intended.

**Decision**

Define a strict, versioned `TargetIntakeContract` as the boundary before target confirmation. Its
minimum required information is a normalized description, one supported intended-use enum, and a
positive intended real-world target height. Each populated target field requires concise evidence,
source, and confidence of at least 0.8; absent, ambiguous, conflicting, or lower-confidence values
are represented as explicit
`missing_fields`. Ask only for those fields. Never ask the user to repeat an already-supported
answer, never infer intended height from measured source bounds, and never treat conversation text
as repair authorization.

The ordinary entry form therefore asks only what the user was trying to make. The local
zero-network reference extracts explicit supported use and measurement phrases, displays only the
unresolved questions, and requires one final confirmation of the complete target. The durable
hosted path writes `target_intake.json`, persists clarification evidence and exactly-once command
state, and consumes the completed draft without re-requesting its values. A future Bedrock model
must produce the same validated schema. Grounding, tolerances, naming, and budgets remain policy
resolution concerns and do not enlarge the minimum questionnaire.

**Evidence and consequences**

Acceptance covers complete extraction, missing-height-only and missing-use-only clarification,
conflicting use language, invalid values, schema inconsistency, final-confirmation gating,
job-snapshot persistence, hosted application restart, and the unchanged approved deterministic
workflow. This decision adds no model call, repair operation, appearance inference, AWS activity,
or editable safety rule. It refines D018–D021 intake without weakening their confirmation, policy,
authorization, or verification boundaries.

### D021 — One parameterized policy family replaces user-visible scale baselines

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M8/M9 policy-resolution correction

**Context**

The intent flow already asks the user what the asset should become and freezes intended real-world
height. Asking the same user to choose between `Human-scale static mesh` and `Compact static mesh`
made them reverse-engineer an implementation detail, while asking for height again contradicted the
confirmed target story. Selecting the nearest preset also discarded useful semantic information in
the description, such as whether an asset is meant to stand, hang, or hover.

**Decision**

Use one immutable, versioned `Unreal Static Game Asset Policy Family` as the parameter source for
new form-led and hosted conversational jobs. The agent proposes a complete job-specific
`ProjectProfile` from confirmed typed intent and bounded semantic derivation. Target height comes
from the already-confirmed story; tolerance scales with intended height; explicit supported
grounding language may set ground-contact policy; and unspecified naming, resource budgets,
orientation, authorization, and safety values retain family defaults. A source asset's observed
defects may inform questions and evidence but may not relax the target policy to make that source
pass.

Show the proposed rules before inspection, keep complete active parameters and their sources
inspectable, and permit advanced edits only for the existing supported `ProjectProfile` fields.
Validate and freeze the result server-side with a resolved identifier, family identifier, explicit
differences from the family, per-rule source, version, and canonical hash. The legacy
`base_preset_id` provenance field mirrors the family identifier for schema compatibility. Changing
intent or any supported adjustment creates a new job. Never expose raw transforms or make safety
classes, source preservation, unsupported repair domains, verification invariants, or
authorization behavior editable.

Historical repository presets remain byte-for-byte immutable and valid for reproducible CLI,
fixtures, and old evidence. They are no longer choices for new conversational jobs. This decision
supersedes only the user-visible preset-selection and nearest-preset portions of D013, D019, and
D020; their safety, durability, Job Contract, and deterministic workflow decisions remain active.

**Evidence and consequences**

Acceptance covers removal of named baseline controls and duplicate height entry, intent-derived
height/tolerances, suspended versus grounded descriptions, family-default fallback, server-side
advanced validation, immutable historical policy bytes, family/resolved provenance, per-rule
source citations, distinct jobs after rule or intent changes, and unchanged inspect through package
behavior. This decision adds no repair operation, appearance inference, paid model call, AWS
activity, or editable safety boundary.

### D020 — Durable local hosted reference uses structured workspace state and Strands snapshots

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** Codex, implementing approved D019

**Milestone:** M9

**Context**

D019 requires the exact approval interrupt and deterministic job to survive browser, application,
and agent-runtime restart without expanding the repair engine or depending on paid infrastructure
during local development. The existing M8 web registry retained Python objects only, while the
deterministic artifacts already contained most stage outputs.

**Decision**

Implement a versioned filesystem-backed hosted reference path at `/workspace`. Persist one private
atomic `workspace.json`, profile-free `preflight.json`, the frozen profile and intent, structured
event ledger, command idempotency records, retention/deletion status, and artifact references inside
each isolated workspace. Store the Strands agent's native session snapshot separately with its
exact interrupt state. Reconstruct `AgentJob` from private runtime state plus validated contracted
artifacts after restart. Keep the M8 form-led routes and outputs unchanged.

Before target confirmation, allow only `PreflightResult`: source identity, glTF structure, bounds,
transform facts, supported-feature counts, resource counts, and declared material metadata. Derive
the closest immutable preset by target height, apply explicit supported overrides, validate the
result as `ProjectProfile`, and freeze its provenance. Treat ordinary dialogue as non-authorizing;
only the exact structured interrupt response may resume repair. Store bounded evidence categories
and references rather than raw questions, routine response prose, hidden prompts, or chain of
thought in hosted provenance.

This local storage shape is a reference and test harness, not the final remote concurrency model.
An AWS deployment must replace local atomic-file coordination with an appropriate isolated durable
store and retain the same schemas, idempotency semantics, privacy boundary, and acceptance tests.

**Evidence and consequences**

Automated acceptance covers profile-free preflight, schema-valid advanced rules, narrowed-goal
agreement, clean no-mutation control, native interrupt restoration in a new store/application,
structured chat non-authorization, duplicate decision replay, verification, and exact ZIP output.
The rendered browser path was checked through preflight, approval, and completion with the source
and candidate previews visible and no console warnings or errors. This decision authorizes no AWS
activity, paid invocation, new repair operation, or public release.

### D019 — Conversation-led hosted workspace with typed target and objective preflight

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M9

**Context**

The M8 form-led product safely completes the full static-GLB workflow, but the remaining human
ambiguity is intent: what the asset should represent, its real-world size and use, and which
unsupported goals require an external handoff. D012 and D018 required agreement before upload,
which prevented measured source facts from improving follow-up questions. The user asked for a
Codex-like collaboration around one asset, and a completed ChatGPT Pro review recommended a
conversation-led, contract-anchored workspace while explicitly rejecting a chat-only product.

**Options considered**

- Keep the M8 form-led interaction as the only product interface.
- Replace structured state and approval with an open-ended chat interface.
- Make conversation the primary hosted navigation while retaining a visible Job Contract, typed
  confirmation, deterministic execution, and exact structured approval.

**Decision**

Adopt the third option for the M9 hosted path. Keep the M8 form-led product intact as the reference,
offline acceptance harness, comparison baseline, and fallback.

After minimal context, permit GLB upload and objective measurement-only preflight before final target
agreement. Clearly label this state as measured source facts without an agreed target. Do not create
policy-relative findings, a registered repair plan, an approval interrupt, a readiness result, or
any mutation until the user explicitly confirms typed target state.

Show a persistent structured Job Contract beside the conversation. It contains source status,
target, rules, measurements, findings, plan, decision, verification, and package status. Ordinary
users confirm a schema-valid job copy derived from the nearest immutable trusted preset and explicit
target overrides rather than choosing a named scale baseline. Preserve the resolved policy's ID,
base preset, overrides, version, canonical hash, and complete read-only rules. Advanced users may
edit only fields already supported by `ProjectProfile` and the deterministic engine. Changing
confirmed intent or rules creates a new job.

Preserve `original_intent`, a narrower `supported_job_goal`, and an explicit support status.
Playable-character, rigging, skinning, or animation requests may proceed only after the user accepts
a static-mesh or inspection-only goal; the final result must disclose the external handoff and may
not claim unsupported readiness.

Conversation may decide what to ask and explain only recorded evidence. Appearance-related
statements require deterministic material or texture metadata and must be classified as supported,
contradicted, or not evaluated. The human grants or rejects consequential authorization through the
exact structured interrupt. The deterministic core validates and enforces its binding. Chat prose
and the agent have no authorization role.

Persist enough structured state to survive browser, application, and agent-runtime restart with
exactly-once mutation and packaging. Hosted provenance records confirmed typed state, versions and
hashes, deterministic tool-call ledger, action and decision events, artifact references, and
external handoffs. Do not package chain-of-thought, hidden prompts, routine prose, or a raw
transcript. Prefer structured intent plus a canonical hash in the package; raw description text is
private short-lived job state or an explicit opt-in.

Limit M9 to dialogue, typed-state confirmation, existing narrow tools, exact approval, durable
resume, evidence-grounded follow-up, and the unchanged registered repair pipeline. Defer every new
repair operation, visual-model judgment, model-generated transforms, conversational authorization,
hosted Blender or Unreal workers, multi-asset workspaces, cross-job memory, accounts and teams,
shared profile libraries, arbitrary policy upload, general shell access, and open-ended editing.

This decision supersedes D012 and the ordering portion of D018 for the hosted M9 path. Their current
form-led behavior remains the executable reference until the versioned M9 implementation passes its
gate. D013's frozen-policy and editable-safety boundaries remain controlling.

**Evidence and consequences**

The accepted direction and its seven-part review are recorded in `docs/INFLECTION_POINT.md`.
`docs/PROJECT_CONTRACT.md` version 1.1 incorporates the hosted input, web, Strands, privacy,
durability, and M9 gate changes. The GLB-only boundary, source preservation, registered repair set,
exact human approval, independent verification, seven-artifact package, and real-world validation
addendum are unchanged.

The interaction change remains a hypothesis until controlled comparison shows better target
accuracy, completion time, or comprehension without worse unsafe authorization, false readiness, or
verified-output rate. This decision does not authorize AWS spending, paid model invocation, resource
creation, or any new repair capability.

### D018 — Confirmed asset intent replaces audience-mode selection

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M8 / M9 preparation

**Context**

The three audience presentations helped explore product language but asked who the user was before
capturing what they actually needed. Real-asset diagnosis also showed that intended height and a
description of the desired asset are essential context: measurements alone cannot decide whether a
99-meter lantern should be a prop, or whether a static character was intended to become playable.
The user described the desired experience as working on an asset together in a Codex-like
conversation, eventually using Bedrock rather than Codex.

**Options considered**

- Keep the role selector and add more questions to every audience route.
- Let free text directly select repair operations or allow a model to decide target state.
- Replace the selector with a bounded target-story dialogue, require explicit agreement, and feed
  only confirmed structured fields to the deterministic workflow.

**Decision**

Make `/` ask what the user was trying to make, whether the target is a static asset, rig-ready
character, or playable animated character, and its intended real-world height. Draft an exact
first-person target story and require the user to agree before policy selection or upload.

Freeze the confirmed record with a version, opaque ID, original description, target-use enum,
height in centimeters, exact story, confirmation timestamp, and canonical SHA-256. Write
`intent.json` beside the job inputs and embed the same record in `provenance.json`. The agreed height
becomes the target-state profile parameter; if it differs from a preset default, derive a validated
custom profile copy. Never expose or accept a raw transform through this flow. Changing intent or
rules creates a new inspection/job.

Treat the description as untrusted metadata, not executable instructions, repair authorization, or
deterministic evidence. A later Bedrock/Strands conversation may ask follow-ups and construct the
same schema, but the deterministic engine remains authoritative for measurements, repair planning,
approval, mutation, verification, and readiness. Rigging, skinning, animation, material, texture,
topology, and other unsupported repair domains remain out of scope.

Retire the audience selector from the primary UI and redirect legacy `/stories/{role}` bookmarks to
the new entry point. Preserve the two-column shell, one-visible-step attention budget, versioned
policies, grouped normalization approval, and Inspect → Decide → Download job flow. This decision
supersedes the role-navigation portions of D008, D010, and D014–D016 without invalidating their
progressive-disclosure or layout evidence.

**Evidence and consequences**

Acceptance covers invalid-intent rejection before job creation, explicit agreement before upload,
non-static scope disclosure, canonical hash validation and tamper rejection, frozen intent in job
and package provenance, height-derived target policy, distinct jobs for intent or rule changes,
legacy-route redirects, and the existing approved, clean, invalid, and inspection-only workflow
paths. The current local path remains deterministic and zero-network. Adaptive Bedrock follow-ups,
semantic comparison of a description to appearance, persistent conversations, and AWS deployment
remain future work behind the existing M9 credential and cost-control checkpoint.

### D017 — Scale-oriented labels preserve immutable legacy profile identity

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M8

**Context**

The first preset appeared in the UI as `Unreal Indie Robot`, which suggested a robot template or a
different repair feature set. Direct comparison of both profile documents showed that engine and
asset type, orientation and grounding, naming, budgets, auto-renaming, and approval behavior are
identical. Only target height and tolerance differ.

**Options considered**

- Keep the asset-specific names and explain them in more text.
- Rename the profile IDs and JSON content, invalidating immutable hashes and existing provenance.
- Use truthful human-readable scale labels in the web presentation while retaining canonical
  profile bytes and identifiers as legacy evidence.

**Decision**

Present `unreal-indie-robot-v1` as **Human-scale static mesh**, with a 1.8 m target and 1.7–1.9 m
accepted range. Present `small-stylized-static-mesh-v1` as **Compact static mesh**, with a 1.2 m
target and 0.9–1.5 m accepted range. Ask users to choose the asset's intended scale. State through
the collapsed rule review that all other current behavior is identical. Do not modify either preset
file, canonical hash, profile ID, frozen job policy, or historical validation artifact.

**Evidence and consequences**

Web acceptance requires both scale-oriented labels and ranges and rejects the old asset-specific
display name. Profile IDs remain trusted server inputs and remain visible in expanded provenance.
Choosing a preset changes only `HEIGHT_OUT_OF_RANGE` evaluation, the derived scale factor, and any
resulting physical-normalization proposal; it does not unlock different repair capabilities.

### D016 — Large-type, disclosure-first presentation

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M8

**Context**

The clarified application frame matched the requested geometry, but the workspace still rendered
too much explanatory and policy text at small sizes while leaving useful whitespace around it. The
user asked for less default text, larger content that uses the workspace, and hover or expansion for
details.

**Options considered**

- Increase every font without changing information density.
- Remove policy and finding evidence from the product.
- Keep the complete evidence in the document, but expose only the current choice or finding title
  by default and enlarge the primary interaction surfaces.

**Decision**

Make the Help workspace one large question plus three large choice cards. Move each audience's
question to the choice's hover title and remove repeated explanatory paragraphs. Enlarge the
audience heading, panel headings, workflow labels, navigation tiles, policy choices, metrics, and
finding titles. Collapse preset summaries and complete active parameters under `Review rules`,
finding descriptions and policy provenance under `Details`, and upload behavior under
`Upload details`. Keep all content in accessible server-rendered HTML and preserve the single-step
workflow.

**Evidence and consequences**

Acceptance asserts that intro/promotional copy and secondary workflow captions are absent by
default, both policy summaries remain inside collapsed reviews, and every finding retains a detail
disclosure. Desktop browser evidence measures a 1160 px chooser with three 376 × 260 px choices and
a 112 px question; the Rules step shows only two policy names, two review controls, customization,
and the next action. Inspect shows four enlarged metrics and ten compact finding headings, with
policy evidence restored when a detail is expanded. Compact review retains a 76 px left pane, 32 px
workflow headings, one-column 274 px policy cards, and zero horizontal overflow. Backend behavior,
policy completeness, provenance, authorization, repair, and package output are unchanged.

### D015 — Clarified two-column frame replaces narrow-rail proportions

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M8

**Context**

D014 correctly established five persistent presentation modes and a one-step workspace, but its
112 px icon rail did not match the user's intended spatial hierarchy. A follow-up wireframe made the
layout explicit: a dedicated logo cell above a wider three-tile style selector on the left, a title
cell above the workspace on the right, and aligned dividers forming a two-by-two application frame.

**Options considered**

- Keep the narrow icon rail and treat the clarification as documentation only.
- Move the selector into the workspace or redesign the workflow itself.
- Preserve D014's behavior while widening and restructuring the left pane to match the clarified
  frame.

**Decision**

Use a 248–320 px desktop navigation pane below the placeholder logo cell. Make Game developer,
3D artist, and Technical artist prominent full-width tiles. Keep Help me choose and Advanced user
as smaller secondary tiles in the same pane. Align the 96 px logo cell exactly with the workspace
title header. At compact widths preserve the left-side orientation as a 64–76 px icon pane with an
aligned 72 px header. Do not change role routes, policy controls, workflow steps, job state, repair
authorization, or product scope.

**Evidence and consequences**

Web acceptance asserts exactly three primary style tiles, two secondary guidance tiles, five modes,
dynamic titles, and the one-focus-area budget. Live browser measurements confirm the equal-height
logo/title row, 320 px desktop and 76 px compact navigation widths, one visible workflow area, and
zero horizontal overflow. The wider pane consumes more desktop width, deliberately giving the
style selector the prominence shown in the user's wireframe; compact screens retain the prior
icon-only behavior.

### D014 — Persistent five-mode rail with a single-step workspace

**Date:** 2026-08-22

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M8

**Context**

The progressively disclosed role-first site still spent substantial horizontal space on repeated
audience framing and presented source preview, result, and technical evidence together on job
pages. The user requested a more efficient application shell: three audience styles permanently on
the left, Help me choose and Advanced user beside them, and only one workflow step visible in the
main workspace at a time. The supplied visual reference rendered as a uniform black image, so the
written layout specification was the only actionable design input.

**Options considered**

- Keep the existing centered role chooser and two-column story hero, then shorten its copy.
- Create five separate products or expose advanced transform operations.
- Keep one shared workflow, add a persistent icon rail for five presentation modes, and make
  Rules/Upload plus Inspect/Decide/Download explicit single-visible-step workspace navigators.

**Decision**

Use a fixed left rail with placeholder `LOGO` text; Game developer, 3D artist, and Technical artist
style icons; and separate Help me choose and Advanced user icon tiles. Every icon has an accessible
label, native title, and hover/focus hint. The workspace header is exactly
`Asset Shepherd -- [style]`, with the style updated by the active mode.

Render only Rules or Upload during intake. Render only the selected Inspect, Decide, or Download
job view, using a read-only query parameter over the same frozen in-process job. Default directly
to Decide while approval is pending and Download after completion or blocking. Advanced mode uses
the same supported profile-copy form and deterministic workflow; it does not unlock raw transforms,
safety policy, unsupported repair domains, verification invariants, or source mutation.

**Evidence and consequences**

Parameterized web acceptance runs the complete approved broken-fixture workflow through all three
audience styles and Advanced mode. Additional assertions cover all five rail modes, dynamic titles,
hidden Upload startup state, explicit job views, exactly one focus area per server-rendered state,
policy provenance in Inspect, authorization in Decide, and verification/package evidence in
Download. The original role routes, profile schema validation, native Strands interrupt, grouped
normalization approval, source preservation, and seven-artifact package contract remain unchanged.

The left rail remains visible at narrow widths and therefore consumes a small fixed slice of mobile
space. This is intentional: the user explicitly chose persistent orientation over moving the mode
navigator to a bottom bar.

### D013 — Freeze versioned policy copies per inspection job

**Date:** 2026-08-21

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M8

**Context**

The explicit rules-then-upload intake prevented users from confusing a profile with a model, but a
profile was still presented mostly as a short radio label. Job provenance recorded only its ID and
version, findings exposed only a bare rule path, and the web job read the repository preset directly.
The user asked to make profiles first-class versioned project policies, preserve presets as
immutable, support bounded customization, and prove exactly which frozen rules governed a job.

**Options considered**

- Keep presets read-only and add descriptive copy only.
- Allow arbitrary profile JSON or raw transform input in the browser.
- Build a general policy-management service with mutable saved profiles.
- Keep the existing role/intake flow, show complete preset policy evidence progressively, validate
  only supported target-state overrides, and freeze the resolved copy inside each new job.

**Decision**

Keep repository JSON profiles immutable and expose them as presets with concise summaries and a
collapsed full rule review. Add one collapsed `Customize a copy` section inside the existing intake
focus area. Allow only height/tolerance, Y-up and ground-contact target state, an engine-compatible
bounded naming pattern, and report-only budgets. Do not expose matrices or make repair safety,
authorization classes, vertical inference, uniqueness guarantees, verification invariants,
unsupported repair domains, engine/type, or source preservation editable.

Every upload writes a resolved `profile.json` into its opaque job workspace. A custom policy receives
a deterministic frozen ID derived from its base preset and explicit overrides. Provenance records
that ID, the base preset, only changed values, profile version, and canonical SHA-256. Findings retain
their primary rule path and add the exact frozen policy parameter values that caused them. Existing
jobs have no policy mutation route; changing rules requires a new upload-backed inspection/job.

**Evidence and consequences**

Web acceptance covers preset summaries and collapsed reviews, successful validated custom copies,
invalid numeric and naming-rule rejection before job creation, unchanged repository preset bytes,
canonical-hash agreement, explicit override recording, finding rule citations, and distinct job and
inspection records for different policies over the same source. Existing three role routes, the
two-focus-area intake, single grouped normalization approval, clean/blocked/error behavior,
independent verification, source preservation, and seven-artifact ZIP remain unchanged.

Custom copies are deliberately job-scoped rather than a reusable policy library. This avoids adding
accounts, mutable shared policy state, or deployment architecture before M9 while making every
current result reproducible from its frozen policy evidence.

### D012 — Require an explicit validation-rule choice before GLB upload

**Date:** 2026-08-21

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M8

**Context**

The intake card presented a dropdown labeled `Project target` above the GLB upload. A first-time
user reasonably could not tell whether the dropdown selected an example asset, replaced the upload,
or configured the inspection. It also silently defaulted to the first profile, making an unintended
1.8-meter character target possible for a prop such as Shader Lantern.

**Options considered**

- Keep the dropdown and add a short helper sentence.
- Preselect a profile based on the user's story route or uploaded filename.
- Show both trusted profiles directly, require an explicit choice, and separate rules from the
  actual file as two numbered steps.

**Decision**

Replace the dropdown with two visible radio choices and no default. Label step 1 `Choose validation
rules` and explicitly state that it does not choose a model. Label step 2 `Upload the GLB you want
checked` and state that this is the actual 3D model. Keep both steps inside the single intake focus
area and preserve the same trusted profile IDs, upload boundary, and workflow behavior.

**Evidence and consequences**

All three story routes render the same two-step intake and tests assert the explanation, two
required profile choices, absence of the ambiguous label, and unchanged end-to-end workflow. Live
desktop and phone-width review shows no horizontal overflow; selecting the small-stylized profile
sets `small-stylized-static-mesh-v1`; and the console has no errors or warnings. Users must now make
one deliberate rule choice before submission, trading a single click for protection against a
silent, inappropriate scale target.

### D011 — Approve Shader Lantern normalization and preserve its report-only warning

**Date:** 2026-08-21

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** RW2 / M10

**Context**

Shader Lantern's frozen blind plan correctly stopped at a consequential physical-size decision. The
raw export represented a 99.908905-meter object, while the user has now stated that the intended
real-world height is 1.2 meters and approved `normalize-root-v1`. The same plan contains two safe
display-name repairs and a 1,564-triangle budget overage that is explicitly report-only.

**Options considered**

- Reject or defer normalization despite the supplied intended height.
- Execute the approved scale and safe display-name repairs while preserving all authored content.
- Expand scope into topology reduction or attempt to recreate transparent/emissive effects visible
  in the Tripo preview but absent from the exported GLB.

**Decision**

Execute the approved `0.0120109414×` uniform root normalization and both policy-safe display-name
repairs. Preserve geometry, topology, materials, images, textures, and samplers exactly. Leave
`TRIANGLE_BUDGET_EXCEEDED` unresolved and report-only. Treat the source export's opaque,
non-emissive material state as a disclosed corpus limitation rather than inventing preview-only
content. Use a Blender re-export as the third Unreal diagnostic arm and label it as a control, not a
human-cleaned reference.

**Evidence and consequences**

Independent verification measures a grounded 1.2-meter candidate with unchanged 77,545 vertices,
101,564 triangles, one material, and three textures; its second plan is empty and its only remaining
warning is the triangle overage. Raw and repaired GLBs have byte-identical binary geometry and
material/texture/image/sampler/accessor records. Blender 5.1.2 imports both with matching resources
and near-zero rendered difference, successfully re-exports the repaired candidate, and Unreal 5.8
imports raw, repaired, and the Blender control with zero errors. The isolated Unreal visual pass
finds no appearance, texture, normal, opacity, or emissive-behavior regression. The full RW4
three-way gate remains incomplete because no human-cleaned Lantern reference or manual-time record
exists.

### D010 — Progressive disclosure limits every web state to three primary focus areas

**Date:** 2026-08-21

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M8

**Context**

The first story chooser asked a new visitor to understand eleven separate visual and textual areas
before choosing a role. Its three route cards also embedded mini workflows, promises, and product
boundaries, while later screens exposed stage rails, metrics, previews, decisions, findings, and
verification simultaneously. The behavior was correct, but the presentation made the product feel
more complicated than the three actions a user actually performs.

**Options considered**

- Shorten individual paragraphs while retaining the same card and panel hierarchy.
- Remove role-specific journeys and return to one generic technical-art page.
- Keep the three functionally equivalent role routes from D008, but reveal only the next useful
  action and collapse detailed evidence behind one explicit disclosure.

**Decision**

Make the role question the first visible content on `/`. Limit the chooser and each intake to two
primary focus areas. Limit approval, blocked, and completed job states to three: the decision or
result, the model preview, and one collapsed technical-details disclosure. Use the short visible
sequence `Inspect → Decide → Download/Package`; retain all seven contracted stages, findings,
checks, metrics, and session behavior inside technical details. Keep all workflow behavior, safety
policy, output artifacts, and role distinctions unchanged.

**Evidence and consequences**

Automated acceptance tests count `data-focus-area` regions and fail any rendered state above three,
while still completing the exact approval and seven-file ZIP workflow through every role. Desktop
and 390 × 844 browser review confirms the chooser starts with `Which best describes you?`, all three
role pages render without horizontal overflow, and pending/completed states expose only their three
primary areas. The source, Strands interrupt, deterministic repair, independent verification,
preview routes, and download package are unchanged. Detailed evidence now requires one intentional
click, which is the deliberate tradeoff for a much clearer first scan.

### D009 — Track Shader Lantern and preserve its pending blind decision

**Date:** 2026-08-21

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** RW2 / M10

**Context**

The user supplied the untouched Shader Lantern GLB and its authenticated Tripo workspace reference.
The 12.8 MB file was generated through the same paid Tripo account for which the user confirmed
commercial public-use rights. Blind inspection found a standards-compliant but implausible
99.908905-meter represented height and proposed a consequential scale normalization to the selected
general small-asset profile's 1.2-meter target. The user has not yet stated the lantern's intended
real-world height.

**Options considered**

- Guess the intended physical size and approve the root normalization.
- Reject the proposal on the user's behalf and complete a name-only result.
- Preserve the registered source and frozen inspection/plan at the approval boundary until the user
  approves or rejects the exact transform.
- Keep the rights-confirmed input private despite its modest size and reproducibility value.

**Decision**

Track the byte-identical raw GLB as the second distributable corpus input and freeze its blind result
at `normalize-root-v1`. Do not open the Lantern in Blender, Unreal, or a visual preview and do not
execute even safe names until the human physical-size decision is recorded. Record only workspace
settings actually exposed by the authenticated item page; mark Smart Mesh version and speed preset
as unverified.

**Evidence and consequences**

The raw SHA-256 is
`be2c9cab8d4e51f7a948c7c54db7a10c932f24faf69bc3166ff724ccc00c49b9` before and after
registration. Blind evidence reports a valid static GLB with 77,545 vertices, 101,564 triangles,
three embedded 4096² PBR images, no rig/animation/morph targets, two safe name candidates, a
report-only 1,564-triangle budget overage, and the pending reversible `0.0120109414` scale. This
preserves the addendum's prediction-before-diagnosis discipline and makes the missing user decision
explicit instead of disguising it as autonomy.

### D008 — Three story-first web concepts share one product core

**Date:** 2026-08-21

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** M8

**Context**

The first M8 surface exposed the complete workflow but explained it with one generic technical-art
layout. A new game developer, 3D artist, and technical artist arrive with different questions: ship
readiness, preservation of artistic intent, and policy evidence. A single information hierarchy made
the underlying product harder to understand even though the workflow itself was correct.

**Options considered**

- Replace the existing page with one compromise layout for every audience.
- Fork the backend or available capabilities by audience.
- Build three complete presentation concepts that reorder and rephrase the same profile, upload,
  Strands interrupt, deterministic repair, verification, preview, and result package.

**Decision**

Make `/` a transparent three-concept chooser and provide full routes for game developer, 3D artist,
and technical artist journeys. Store the selected story with the in-process job so refreshes and the
approval/completion page preserve that mental model. Keep all behavior, safety boundaries, profiles,
actions, output artifacts, and local zero-network provider identical.

**Evidence and consequences**

Parameterized acceptance tests run the complete broken-fixture approval and exact seven-file ZIP
audit through every story. Clean, invalid, and inspection-only paths remain covered. Live Chrome
review passed for all three desktop layouts; 390 × 844 responsive review found no horizontal
overflow; Patchling's textured before/after previews render in the artist flow; and the application
console is clean. The repository deliberately keeps all three concepts available for user comparison
rather than declaring a canonical audience hierarchy before review.

### D007 — Track Patchling as the first distributable real-world input

**Date:** 2026-08-21

**Status:** ACCEPTED

**Decision owner:** User and Codex

**Milestone:** RW1 / M8 / RW5

**Context**

The addendum requires the final public repository to contain enough original or distributable assets
to reproduce at least one complete demo workflow. D003 intentionally ignored all real-asset binaries
until rights and repository-size policy were known. The user has now confirmed that Patchling was
generated under a paid Tripo account with commercial/public-use rights, and the immutable GLB is
4,860,944 bytes.

**Options considered**

- Keep every real-world binary private and defer reproducibility to an external handoff.
- Track Patchling with Git LFS despite its modest size.
- Track only the byte-identical Patchling raw GLB in ordinary Git, while continuing to ignore
  repaired outputs, ZIPs, DCC files, Unreal content, and screenshots.

**Decision**

Add an exact `.gitignore` exception for `patchling_01/raw/asset.glb` and track that file in ordinary
Git. Continue ignoring all other raw corpus assets until their individual rights and size are
confirmed. Keep generated outputs reproducible from the raw input, profile, approvals, and code.

**Evidence and consequences**

The tracked file's SHA-256 remains
`dc2f03ae8ed368f46c2a4ac9e2ebb71f23e980b0c9e6913c685d011e273f418d`, matching the download,
registration record, frozen blind inspection, and pre/post registration checks. Its size is well
below GitHub's ordinary file limit and does not justify LFS overhead. Public reproduction no longer
depends on the owner's authenticated Tripo workspace link.

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
failure originally caused one same-plan retry; D032 supersedes that behavior with one fresh
candidate inspection and unexecuted plan assessment. Strands metrics expose tool outcomes,
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
