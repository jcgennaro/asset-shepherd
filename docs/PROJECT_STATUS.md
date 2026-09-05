# Asset Shepherd Project Status

**Last updated:** 2026-09-05
**Current commit:** Collapsible long sub-component inventories (this file is included)
**Current milestone:** M9 agent-led sensing and disposition / RW2 Minimum Asset Flock / M10 evaluation
**Overall state:** IN_PROGRESS

## Milestones

| Milestone | State | Evidence | Commit | Notes |
|---|---|---|---|---|
| M0 Repository bootstrap | COMPLETE | pytest, Ruff, format, Pyright, lock check | 112b649d52009ffa544f7787fb4c0d59efc39272 | Baseline |
| M1 Project control docs | COMPLETE | Common quality gate passed; control files agree on direct-main workflow | e03b4b876a4f1a616da7e077d42620929816eee1 | Completed 2026-08-21 |
| M2 GLB capability spike | COMPLETE | Automated round trip preserves resources/counts and verifies transformed bounds independently | ac10f6bb1ff12837bf45c0a5fcdd8ac99b9db5bf | Completed 2026-08-21; D001 |
| M3 Schemas and fixtures | COMPLETE | Schemas validate; clean and broken robot artifacts regenerate byte-for-byte and independently reload | 444a99877a01694020209d22dab831660c84a47e | Completed 2026-08-21 |
| M4 Inspector | COMPLETE | Broken fixture yields all 10 expected defects; clean has no false severe/auto-safe findings; deterministic CLI artifacts | 4f7434b6ba58127d38e35f793db8ed27fddd3331 | Completed 2026-08-21 |
| M5 Repair engine | COMPLETE | Registered plan, strict authorization, approve/reject paths, stable counts/references, source preservation, idempotence | 27781e2d8afb185171a29982d3cad173e55fe90d | Completed 2026-08-21 |
| M6 Deterministic CLI MVP | COMPLETE | Happy, rejected, and clean-control runs; schema/ZIP audit; Blender 5.1.2 import; full gate | a077077ca94c44b9693893672a7208d84d1f05b8 | Completed and checkpoint-reviewed 2026-08-21 |
| M7 Strands orchestration harness | COMPLETE | Real Strands loop; native interrupt/resume; approve/reject; bounded correction; metrics; offline and opt-in live tests | 02876da55e2dd0bee3dfbe80bd01cd50f87ba76d | Historical tool/interrupt gate; D036 live agent judgment and action choice remain open in M9 |
| M8 Web product | COMPLETE | Intent-first target-story agreement; D021 single-family policy resolution; D022 ask-only-what-is-missing intake; frozen intent and policy provenance; single-visible-step Rules/Upload and Inspect/Decide/Download; Strands interrupt/resume; dual GLB preview; verification/download | e6b9046c86b96dc43f3f4e255f00e759f2d3d22e | D006–D018 establish the flow; D021/D022 remove implementation choices and repeated target fields without changing acceptance behavior |
| M9 Hosted Bedrock conversation and deployment | IN_PROGRESS | D019 durable workspace; D036 authority contract; D037 agent-authored planning; D038 bounded multi-turn loop; D039 hosted handoff; D040 named asset gallery; D041 explicit approval; D042 upload-first flow; D043 semantic assembly and mesh health; D044 coordinate-aware yaw sensing; D073 Bedrock Responses adapters; D074 Nova diagnostic; D077 model-neutral Converse allowlist; D078 Claude Haiku 4.5 least-privilege gate; D093 ECS Express/AgentCore topology; D094 fixed provider acceptance; D095 opt-in Muse comparator; D096 opt-in Gemini comparator; D103 cloud state foundation; D104 ARM64 runtime and typed AgentCore boundary; D105 durable SQS/Lambda command dispatch; D106 bounded observability and verified purge; D107 immutable Bedrock content boundary; D108 private alarm notification route |  | Kimi passes the fixed 8/8 gate; live S3/Dynamo state, Linux ARM64 rendering, private AgentCore, and the public ECS/SQS/Lambda browser path pass through accepted download and forced task replacement; the immutable Guardrail now passes direct and rebuilt public-application acceptance; all eight live alarms are wired to one confirmed private topic and the AWS alarm-to-SNS test passes; Step 7 identity isolation and the full Step 8 remote matrix remain |
| M10 Evaluation | IN_PROGRESS | `docs/REAL_WORLD_VALIDATION_PLAN.md`; typed corpus/evidence harness; D026 authority classes, deeper diagnostics/preservation, official Khronos adapter, render comparison | 085545efdda09aa3a77aa115ce521ab4dfecb3b0 | RW0–RW5 addendum controls real-world evaluation; untouched RW2 assets and full human-reference arm remain open |
| M11 Docs and Builder posts | IN_PROGRESS | Official-rules audit and `docs/CONTEST_COMPLIANCE_PLAN.md` |  | Public repo, final architecture, video, Builder posts, and submission copy remain open |
| M12 Release and submission | NOT_STARTED |  |  | Mandatory checkpoint before submission |

## Real-world validation milestones

| Milestone | State | Evidence | Notes |
|---|---|---|---|
| RW0 Adopt and scaffold | COMPLETE | Canonical addendum; typed schemas; ignored corpus; generation card; registration, mutation, Blender, Unreal, and report tooling | 085545efdda09aa3a77aa115ce521ab4dfecb3b0; D003; no product behavior change |
| RW1 Patchling blind baseline | COMPLETE | Registered untouched raw hash; frozen inspect/plan/repair/verify/package; Blender raw/repaired evidence; turntable views; human rights and visual adjudication | D004 and D005; zero unsafe repairs or visual/resource regressions |
| RW2 Minimum Asset Flock | IN_PROGRESS | Patchling and Shader Lantern registered; Lantern approved deterministic/Blender/Unreal checkpoint complete | D009 and D011; two more untouched assets still required |
| RW3 Controlled realistic variants | SCAFFOLDED | Repeatable normalization, hierarchy, and material/texture mutation code; fixture dry runs | Real variants wait for registered corpus assets |
| RW4 Blender and Unreal acceptance | IN_PROGRESS | Blender 5.1.2 Lantern import/re-export; isolated Unreal 5.8 raw/repaired/control import and visual evidence | Lantern has no human-cleaned third arm, so the full three-way gate remains open |
| RW5 Evaluation report and demo | SCAFFOLDED | Typed adjudication and traceable case-study report renderer | Public claims remain prohibited until evidence exists |

## Current gate

M9's local Bedrock-provider gate is complete. D094's fixed matrix gives Kimi 8/8 safety and 8/8
semantic/visual passes through the least-privilege Bedrock role, and rejects Mistral Large 3 as the
default. D103 deploys and live-tests the Step 3 foundation: private content-addressed S3 artifacts,
S3 Strands sessions, and conditional DynamoDB records. D104 and D105 prove that state through
AgentCore replacement and ECS task replacement, including a completed accepted workspace.

D037 replaces the first target-dependent planning pass with
a live model-authored assessment and exact typed action preview. Agent-mode inspection exposes
measurements without legacy height/orientation/grounding verdicts; the agent selects semantic axes
and requested scale, rotation, grounding, pivot, and naming components; deterministic code adds
none. An
executed action cannot verify until the agent compares recorded source and candidate renders.

D038 and D063 make that action cycle repeatable rather than adding a special second pass. After
Shepherd, the user chooses the current input or candidate as Iteration 1; Refine archives each pass,
shows 4.1/4.2/4.3 in the rail, and invokes the same workspace-scoped agent with fresh sensing and
authorization. D036's representative remote restart/idempotency acceptance now passes.
Deterministic code remains the measurement, enforcement,
exact-mutation, invariant-verification, and packaging layer.

## Latest evidence

- D118: inventories above seven sub-components now start collapsed, with all rows available on
  expansion; shorter lists remain inline. Nine focused tests prove the threshold and retention of
  all 65 form choices across collapse/reopen. Common gate: 306 passed, three skipped; clean
  Ruff/format/Pyright and lock checks. CodeBuild `e6006dba-978e-4ac6-a4b0-74d651266dec`
  passed the Linux upload smoke (0.013 s acknowledgement, READY in 1.112 s, zero model calls).
  Combined D117/D118 web image `cd489a7-components-web` / task revision 16 serves all traffic;
  CloudFormation UPDATE_COMPLETE / ECS SUCCESSFUL, with zero old tasks. Live CSS/tour script match
  source, health 200, anonymous workspace 401,
  all eight alarms OK. No authentication or model/runtime configuration change.

- D117: removed upload progress's model-running sentence and redundant bottom Gallery link.
  Added a four-step navigation-only tour on first Gallery visit, Skip/Done persistence, native
  keyboard dismissal, and FAQ replay. It does not click controls or interrupt processing screens.
  Real-browser navigation/storage/focus checks pass, with desktop and 390 px visual QA. Common gate:
  297 passed, 3 skipped; Ruff, formatting, Pyright and lock checks pass. CodeBuild
  `ae2f9aa0-7e16-4a8c-9f1c-bb4821d32752` succeeded for `bb40c41-navigation-tour-web`;
  Linux upload smoke reached READY in 1.106 s (0.012 s acknowledgement), with zero model calls.
  Rollout was initially held for the staged collar, now released in the combined D118 web image following
  the user's confirmation that intake completed. No model/runtime/auth configuration change.

- D116: fixes the collar's synchronous upload/preflight bottleneck in shared local/hosted code.
  The 30 MB collar returned in 0.125 s locally and passed asynchronous validation by 20.19 s;
  the mascot/progress cell stayed available and health/status requests remained responsive.
  Cache reuse is bound to source SHA-256 and bytes, avoiding duplicate preflight after Describe.
  Pending checks block intake/preview, and timeout/interruption offers explicit recovery. No paid
  model calls or asset mutations. Local full test suite: 293 passed, 3 skipped; Ruff, formatting,
  Pyright and lock checks pass. Real Linux image upload smoke passed: 0.012 s acknowledgment,
  READY in 1.11 s for the synthetic fixture, zero model calls. Web image
  `d02b33bf7b22-upload-check-web` is deployed as task revision 15: ECS SUCCESSFUL,
  CloudFormation UPDATE_COMPLETE, one new task at 100% traffic and zero old tasks.
  Live JavaScript matches source, health is 200, and anonymous progress/retry/source requests
  remain denied. All eight alarms are OK. No runtime/model configuration or task-size change.
  The authenticated hosted collar retry remains for the user.

- User-confirmed hosted Luna tablet end-to-end acceptance after D115: the user reports completing
  the full tablet workflow successfully. This is human acceptance evidence, not a new measured
  token ledger or proof that the entire hosted acceptance matrix is complete.

- D115: fixes missing clicked-button decision in remote FormData, the cause of the user's Apply
  recommendations 422 before queue dispatch. Four real headless-browser cases retain exact
  approve/reject/revise/accept values and associated fields; no approval is inferred. The signed-out
  page now matches the mascot/dark/mint branding, with visually checked desktop and 320 px layouts.
  Common gate passes: 290 passed, 3 skipped; lock, Ruff, formatting, Pyright clean. Web-only image
  `f459c9376886-web-actions-web` passed CodeBuild and is deployed as task revision 14: ECS SUCCESSFUL,
  CloudFormation UPDATE_COMPLETE, one new task at 100% traffic and zero old tasks. Live signed-out template, normalized JavaScript,
  health, and anonymous route denial checks pass. No user command, model request, or repair was
  executed during diagnosis/validation. Reloading and explicitly retrying the pending approval is
  left to the user.

- D114: live Cognito classic client now uses the static mascot/Asset Shepherd wordmark, dark card,
  mint actions, rounded fields, readable labels, and matching reset-screen contrast. CSS version
  `20260905065315`; checked-in assets/publication script in `infra/branding/` and `scripts/`.
  Actual hosted desktop capture and fetched-markup 320/390 px preview frames were visually checked;
  no form was submitted and no user browser was attached. OAuth, session, service tier, web/runtime
  images, and model configuration are unchanged. Common gate: 285 passed, 3 skipped; lock, Ruff,
  format, Pyright pass. See `infra/branding/README.md` for acceptance limitations and reapplication.

- D113: fixes the hosted Redo rejection by using same-origin referrer policy for app responses,
  while keeping no-referrer on authentication routes and the exact-origin CSRF check unchanged.
  Eight focused auth tests pass, including real native form submission in isolated headless
  Chromium; no owner browser attachment, model invocation, or injection-attempt testing occurred.
  Common quality gate passes: 285 passed, 3 skipped; lock, Ruff, formatting, and Pyright pass.
  Web-only image `3aad48575c31-form-origin-web` passes CodeBuild and is deployed as task revision 13:
  ECS SUCCESSFUL, CloudFormation UPDATE_COMPLETE, one fixed task at 100% traffic, zero old tasks.
  Live application/auth policy headers and anonymous workspace/download/OpenAPI/Redo denial pass.
  Runtime/model configuration stays unchanged. The owner must reload Gallery before retrying their
  authenticated Redo; no real workspace was restarted or repair approved during acceptance.

- D112: one renewed administrator Bedrock Responses/Luna xhigh request still returns 403 account
  unavailability. The existing DPAPI-protected OpenAI key is now in a separate Secrets Manager
  secret; a local SDK check using that secret completes with 16 tokens in 2.91 seconds. This does
  not alone prove AgentCore access. Runtime/web share one allowlisted model resolver, retain Kimi
  workspaces, and bind optional OpenAI to an exact role-readable ARN with xhigh for both boundaries.
  The selector explicitly labels separate OpenAI API billing. Docker access logging and public
  SDK error-body redaction were corrected during the secret review. Both `f0fe26a-openai` images
  pass CodeBuild. AgentCore runtime 8/DEFAULT are READY and the stack is UPDATE_COMPLETE. Its saved
  Smartpad probe reached APPROVAL without mutation/error in 75.83 seconds (55.61 seconds inside
  Strands), using 47,230 input and 4,360 output tokens. Kimi remains the deployment default; the
  website's explicit Luna selector is deployed as task revision 12. ECS reports SUCCESSFUL,
  CloudFormation UPDATE_COMPLETE, one new task at 100% traffic, and zero old tasks. Authenticated
  Chrome shows both choices and the saved proposal/interactive 3D preview; anonymous workspace,
  activity, download, OpenAPI, and command requests return 401, while health remains 200 and browser
  navigation redirects to login. No repair approval or injection-attempt test was sent. Full
  browser intake-through-repaired-download acceptance remains open. See `HOSTED_OPENAI_RUNBOOK.md`.
  Common gate passes: 283 tests passed, 3 skipped; lock, Ruff, formatting, and Pyright pass.

- D111: user requested a website login after confirming anonymous access was possible. Cognito
  stack creation passes with admin-only signup, code-only OAuth, and no client secret. The app
  gates data and actions with Authlib OIDC/PKCE and a Secrets Manager-backed secure session signer;
  this is a shared-gallery gate, not tenant isolation. Web image `70f78cd-auth-web` passes CodeBuild
  and is deployed as ECS task revision 11. The deployment is SUCCESSFUL, with all traffic on the
  authenticated task and zero old unauthenticated tasks running. Anonymous data/download/action
  requests return 401; HTML gallery navigation redirects to Cognito with S256 PKCE. The login page
  returns 200 and has no public signup link. Health remains 200 and all eight project alarms are OK.
  The owner rejected the generic invitation (spam/unrecognizable branding); the updated Cognito
  template names Asset Shepherd and includes responsive HTML/app link. A replacement invitation
  was delivered, invalidating the temporary password exposed in the owner's screenshot. The new
  password was not retrieved or printed. Human first-login/password-change acceptance remains open.
  Common gate passes: 277 tests passed, 3 skipped; lock, Ruff, formatting, and Pyright pass.
- D110 deployment completed: AgentCore runtime 7 READY; web task revision 10 completed its rollout
  with `0838caf-render` images. Both CodeBuild gates pass, including fixed 512px ARM64 captures;
  `/healthz` returns 200 and all eight operational alarms are OK. The subsequent auth change is
  a separate deployment, not part of that completed renderer rollout.

- D110: Smartpad Tablet failed because adaptive rendering cropped the back/left screenshots;
  the evidence validator was correct. Fixed-scale capture produces four 512px images with clear
  margins. Repeated identical sensing failures stop after two tool results while retaining usage.
  Luna xhigh and Muse Contributor/high reached native approval in 53.14s and 69.07s respectively,
  with the saved source/target unchanged and no consequential mutation. See
  `TABLET_RENDER_REGRESSION.md`; these are local proposal-stage comparisons, not deployment or
  full-output acceptance. The public default remains Kimi pending explicit provider enablement.
  Common quality gate: 271 passed, 3 skipped; lock, Ruff, formatting, and Pyright clean.

- D109 reduces prompt-attack input strength from HIGH to LOW after the saved tablet request
  reproduced a LOW-confidence prompt-attack block with all other categories undetected. Guardrail
  version 2 is published and passes 4/4 benign input checks, including the full reconstructed
  tablet start message. All three stacks reached UPDATE_COMPLETE; AgentCore runtime 6 is READY and
  ECS task definition 9 completed its rollout with one running task and zero pending tasks. Both
  consumers explicitly pin Guardrail version 2. All eight project alarms are OK. The user prohibited
  injection-attempt tests; none were run for this change. Existing content categories and
  deterministic mutation approvals remain unchanged. Common quality gate: 268 passed, 3 skipped;
  lock, Ruff, format, and Pyright clean.

- Hosted progress regression: the web-process activity endpoint returned an empty `IDLE` trace
  while AgentCore ran elsewhere, clearing the mascot from the notebook. Hosted forms now retain
  their initial sprite and use durable command receipts for queued/running/reconnecting labels;
  failures remove the busy trace and restore the form. Local empty initial activity preserves the
  indicator until sensor events arrive. A second bug used fragment navigation on the same notebook
  URL after dispatch success, leaving stale content onscreen; completion now explicitly reloads
  saved results for the same document. The browser fixture in
  `tests/browser/workflow_activity.html` exercises these transitions without model calls. Chrome
  checks pass for queued, running, reconnecting, failure, same-document completion, and local
  sensor progress after an initially empty trace. Common
  quality gate: 268 passed, 3 skipped; lock, Ruff, formatting, Pyright, and JS syntax pass.
  CodeBuild accepted image `2dfaac2-progress-web`; the web stack reached `UPDATE_COMPLETE` with
  ECS task definition 8, one running task, zero pending tasks, and completed rollout. The public
  JS matches the committed source after line-ending normalization; health, the saved notebook, and
  the mascot asset return HTTP 200. All eight project alarms are `OK`. The user's Chrome tab loaded
  the new script fingerprint `169156b2c775`. No AgentCore image or model configuration changed.
  The user's Smartpad Tablet run exposed a separate unresolved Guardrail compatibility issue:
  recorded `stop_reason=guardrail_intervened` after 0.799 seconds, zero tool calls, and zero reported
  input/output tokens. Its dispatch receipt succeeded but the workspace correctly persisted
  `ERROR`; the old same-URL navigation hid that outcome. No retry or model call was made while
  diagnosing this run. D107's earlier probes do not establish acceptance for this ordinary asset.

- D108 private alarm notification route: `asset-shepherd-operations` reached `UPDATE_COMPLETE` with
  one deployment-parameterized SNS topic. All eight `asset-shepherd-contest-*` alarms have exactly
  one enabled action on that topic and remain `OK`; the email subscription is confirmed. A bounded
  test moved only `asset-shepherd-contest-dispatcher-throttles` to `ALARM`, CloudWatch recorded
  successful execution of its SNS action, and the alarm was immediately restored to `OK`. No
  application workflow or model was invoked. The address is supplied only through a `NoEcho`
  parameter and is absent from repository content and stack outputs. The recipient confirmed the
  email for the 2026-09-04 15:36:18 UTC test, completing end-to-end notification acceptance.

- D107 immutable Bedrock content boundary: `asset-shepherd-guardrail` is `CREATE_COMPLETE` with
  Guardrail `xadkxnj292qu`, immutable version `1`, and the exact public refusal. Direct
  `ApplyGuardrail` probes allow five legitimate game-art cases (railgun, horror monster, medieval
  sword, FPS rifle, and pet collar) and block three disallowed categories plus sexualized-minor
  content, 8/8 overall. Direct Kimi Converse accepts the fictional sword request and returns
  `guardrail_intervened` with the exact refusal for extremist recruitment. The checked-in adapter
  now fails closed on partial or `DRAFT` configuration, applies the latest-message/image boundary to
  Strands Kimi turns, and applies the same immutable version to direct target intake. Focused tests
  and all three deployment templates validate. CodeBuild accepted ARM64 and x86_64 images from
  commit `47d728b`; AgentCore runtime v5 and ECS task definition 7 now use those images with the
  Guardrail version visible in deployment-owned configuration. The public intake returns the exact
  refusal once without echoing a blocked request, while an ordinary 30 cm Unreal robot request
  reaches its target proposal. That allowed test workspace was purged and independently verified
  empty. A no-model status call cold-started runtime v5 and recovered the accepted workspace at
  `COMPLETE`. Ten health calls, the accepted notebook, and its exact 24,580-byte GLB download pass;
  all eight alarms remain `OK`.

- D106 bounded operations foundation: `asset-shepherd-operations` is `CREATE_COMPLETE` with the
  `asset-shepherd-contest` CloudWatch dashboard and eight alarms for Lambda errors/throttling/
  near-timeout duration, SQS backlog/DLQ depth, Bedrock client/server errors, and a 5 GiB private
  storage soft limit. All five discovered CodeBuild, ECS, Lambda, and AgentCore log groups now have
  seven-day retention. The dispatcher and runtime emit only workspace ID, command ID, operation,
  phase/state, and duration as shared correlation fields. The administrator-only exact-workspace
  purge was dry-run and then exercised on the known corrupted deployment-test workspace; independent
  queries confirm zero S3 workspace versions, zero Strands session versions, no DynamoDB pointer,
  and zero command receipts. All eight alarms settled to `OK`. The correlation proof used
  AgentCore runtime version 4 and accepted image `e0356a6-ops-agentcore`; D107 subsequently promotes
  runtime v5. A no-model status command crossed SQS/Lambda/AgentCore and
  reached `SUCCEEDED`; its exact command ID appears in bounded start/success events on both services,
  while the accepted workspace remains version 6 and download-ready. Its two recorded Kimi workflow
  turns have an observed provider subtotal of about $0.114 before the separate intake and AWS
  compute. The web service is now bounded to one 0.5-vCPU/1-GiB task and two public subnets after
  live metrics showed only 43.1% peak CPU and about 235 MiB peak memory on the larger task. Published
  us-east-1 Fargate, ALB-base, and three-public-IPv4 rates put the fixed hosting floor at about
  $1.49/day or $44.77 per 30-day month, down from the six-subnet default's $76.95/month; traffic and
  other variable service charges remain additional. A fail-closed subnet script dry-ran against only
  the tagged Express ALB, then applied and verified `us-east-1a` plus `us-east-1b`; the ALB and managed
  endpoint DNS now expose two addresses. Ten health requests, the accepted notebook, and exact GLB
  download passed after the resize, with all eight alarms still `OK`. Detailed model logging remains
  disabled. D107 subsequently closes Guardrail wording/compatibility; multi-user authentication,
  and the full remote failure matrix remain open; D108 closes notification delivery acceptance.

- D105 remote web command boundary: hosted agent actions now become schema-versioned DynamoDB
  receipts and encrypted SQS messages when the deployment queue is configured. The web request
  returns HTTP 202 immediately; a one-message Lambda consumer invokes the private workspace-bound
  AgentCore session, and the notebook polls bounded status before reloading durable state. Local
  Uvicorn keeps its existing synchronous adapter. Focused tests prove actor binding, command-ID
  conflict rejection, safe pre-dispatch resend, in-flight duplicate suppression, and an accepted
  target route that does not start a local agent. The web build and deployment templates add a
  gated x86_64 image, separate least-privilege roles, encrypted queue/DLQ, dispatcher, and one-task
  ECS Express service. The live stack reached `UPDATE_COMPLETE` with a successful deployment alarm
  bake at
  `https://as-73038a3f3e8d40819c72ccb90d068ec4.ecs.us-east-1.on.aws`. A clean Kimi run returned HTTP
  202 in about 0.5 seconds, persisted the exact approval interrupt, completed the approved repair,
  and reached accepted record version 6. Its two recorded workflow invocations used 175,184 input
  plus 2,934 output tokens over 84.0 seconds. The 24,580-byte repaired GLB downloads with the exact
  `model/gltf-binary` type and `upright-robot-prop_shepherded_090426.glb` filename. After forced ECS
  task replacement, the gallery, terminal notebook, and download rehydrated from S3/DynamoDB with no
  duplicate model call or mutation. Managed HTTPS forwarding, non-retrying long AgentCore dispatch,
  exact parent/runtime-endpoint IAM authorization, and terminal accepted-workspace rehydration were
  all corrected during the live gate. Step 6 is complete. The post-deployment common gate passes
  with 259 tests, 3 intentional skips, a valid lockfile, Ruff, formatting, Pyright, all four live
  CloudFormation templates, the editable SVG/rendered PNG architecture pair, and `git diff --check`.

- D104 complete AgentCore acceptance: the frozen `broken-normalization` provider case used its exact
  122 × 182 × 40 cm target through the deployed private runtime. Planning stopped at the approval
  interrupt; approval completed normalization, name repair, packaged Chromium evidence, deterministic
  verification, and visual reassessment. The durable result is `COMPLETE` and download-ready with no
  failed checks and only the expected material-budget warning. Kimi confirmed corrected orientation,
  scale, grounding, retained parts, and names at 0.95 confidence. The paid turn took 114.76 seconds
  and used 169,391 input plus 1,909 output tokens. An exact duplicate approval preserved record
  version 5. After `StopRuntimeSession` terminated the managed microVM, the same session and command
  rehydrated that identical `COMPLETE`, version-5 result, proving exactly-once behavior without
  process memory. Step 5 of the deployment runbook is complete.

- D104 live AgentCore proof: CloudFormation deployed the immutable ARM64 AgentCore image and a
  separate service-only execution role. A direct typed `status` invocation returned HTTP 200 for a
  workspace hydrated from S3/DynamoDB. The next call used Bedrock Kimi to inspect and plan, then
  stopped at its exact `execute_selected_repairs` approval interrupt. An approved decision resumed
  in AgentCore, executed the selected normalization/naming actions, rendered source/candidate/shared
  evidence through packaged Chromium, passed every deterministic invariant, and wrote the evidence
  package and monotonically versioned state back to AWS. Kimi rejected its own synthetic-robot
  candidate as visually inverted, so the workflow correctly persisted `BLOCKED` rather than
  declaring success. A second turn fixed orientation but retained 3.4 m height because this smoke
  seed bypassed semantic intake: its height-only target had been expanded to a synthetic 1.8 m cube,
  whose deterministic log-space fit selected scale 1.0. Kimi again rejected the candidate. The two
  paid turns recorded 642,488 input and 16,402 output tokens in total. Replaying the exact second
  approval returned the same result with durable record version unchanged at 8, proving persisted
  command idempotency. This proves the remote architecture path but intentionally leaves a
  representative fully specified successful completion and replaced-runtime replay open.

- D104 ARM64 runtime and typed AgentCore boundary: the retained
  `asset-shepherd-container-build` stack now owns a private immutable-tag ECR repository, a
  two-day build-source bucket, and a small ARM64 CodeBuild project. The first build correctly
  failed when Debian Chromium could not initialize its inner sandbox; its accidentally published
  image was deleted, publication now requires an explicit accepted-gate marker, and Chromium keeps
  a bounded stderr diagnostic. The corrected build proved `arm64/linux`, four source renders, four
  shared-scale renders, masks, and application import before publishing a 387,633,373-byte
  compressed image. A versioned AgentCore command boundary now accepts only status, target
  confirmation, exact interrupt decisions, typed plan feedback, result review, and bounded retry;
  rejects extra/raw-prompt fields; binds actor and `workspace-<id>` session; and returns bounded
  workflow state rather than HTML or private descriptions. A separate service-only role/runtime
  CloudFormation template is ready for the next remote gate. Focused and common checks pass with
  253 tests, three intentional live skips, lock validation, Ruff, and zero Pyright findings.

- D103 cloud workspace state foundation: the `asset-shepherd-state` CloudFormation stack now
  deploys one private encrypted/versioned S3 bucket, a seven-day lifecycle, one encrypted
  on-demand DynamoDB table with owner/update index and TTL, and an exact-resource policy on the
  existing restricted runtime role. The application retains its local filesystem implementation
  by default and selects S3/DynamoDB only from complete deployment-owned configuration. Cloud
  artifacts are content-addressed and hash-verified; immutable manifests accompany monotonically
  versioned conditional DynamoDB pointers. Runtime iteration paths are now workspace-relative
  while legacy absolute local snapshots remain readable. Unit acceptance proves process-cache
  replacement, stale concurrent-write rejection, unchanged-GLB deduplication, unsafe-path
  rejection, and fail-closed partial configuration. A live restricted-role proof replaced the
  process cache after intake, after the approval interrupt, and after verified packaging; it
  rehydrated exact GLBs, preserved the interrupt, performed one authorized repair, preserved an
  exact duplicate download/package, queried the owner index, and removed the active smoke record.
  The cloud-configured hosted app also returned its gallery through the same adapters. Live
  agent-orchestrated refinement replacement remains open.

- D102 verified-model filenames: direct local and hosted GLB downloads now use
  `<asset-slug>_shepherded_MMDDYY.glb`; `Tabletop Radio` produces
  `tabletop-radio_shepherded_090326.glb`. The HTML download hint and HTTP
  `Content-Disposition` agree, while immutable working names and the evidence ZIP's required
  `repaired.glb` member remain unchanged. The common gate passes with 240 tests, two intentional
  live-provider skips, lock validation, Ruff lint/format, and zero Pyright findings.

- D101 completed-simplification recovery: Muse workspace
  `ac4d03a975844b8cb8b3d6b721767517` successfully executed and verified the second repair turn for
  the 65-part broken-heart collar, reducing 783,571 triangles to 56,831 and the measured GLB from
  about 28.8 MiB to 7.4 MiB. Its raw 500 page came only from the result renderer reading the transient
  `candidate.glb` name after packaging had correctly renamed it to `repaired.glb`. Completed
  summaries now use durable inspection and verification measurements, and hosted approval events
  record the selected action ID instead of the old normalization constant. Browser verification
  recovered the existing workspace without another model run. The common gate passes: lock check,
  239 tests passed with 2 skipped, Ruff lint/format, and Pyright.

- D100 typed sequential repair continuation and FAQ: an agent that selects physical normalization
  before an independently lossy optimization now records `SIMPLIFY_MESH` in a validated deferred
  repair field. The topology row identifies the queued work, and a verified candidate offers
  **Continue to mesh optimization** or **Finish with this version**. Continuing uses the candidate
  as a fresh refinement input with separate sensing, proposal, approval, and verification; the
  first approval cannot authorize the simplification. A persistent FAQ explains the use-case caps,
  repair sequencing, pivot behavior, source preservation, formats, and the Windows Internet
  Options remedy that restored a GLB download on an unmanaged personal computer with no Chrome
  policies. Targeted prompt, model, schema, and hosted-web coverage passes; common-gate evidence is
  238 passing tests with two intentional live-provider skips, lock validation, Ruff, formatting,
  and zero Pyright findings.

- D099 target-form recovery: saved Gemini workspace `d53910f6f898440b8b447a9801ad9b5e`
  remained valid after a clarification request failed because a browser-restored Other-destination
  string accompanied the selected canonical engine. Canonical Unity, Unreal, and Godot choices now
  discard irrelevant endpoint detail at both clarification and revision boundaries; the Other text
  control is disabled and hidden until Other is selected. Unexpected typed-contract failures are
  presented as concise retryable target errors rather than raw Pydantic diagnostics. A viewing-use
  choice made beside the engine is no longer repeated on the following review; first-time review
  paths still ask once. The persistent technical sentence moved behind a `?` dialog that explains
  the 50,000 / 15,000 / 2,500 triangle guidelines and the user's right to decline optimization.
  The common gate passes with 235 tests, two intentional live-provider skips, lock validation,
  Ruff, formatting, and zero Pyright findings.

- D098 Gemini response-limit recovery: workspace `c839d09e26b6450fa092615f0055302e`
  completed deterministic inspection and a single compact 768 x 256, three-view JPEG evidence
  sheet, then Gemini exhausted its 16,384 generated-token allowance before submitting a typed
  assessment. Browser viewport rotation made no workflow request and was coincidental. The
  truncated turn contained only 236 visible words, localizing the consumption to the model's
  high-level thinking rather than excess screenshots. Gemini intake and workflow evaluation now
  default to medium reasoning while explicit high/xhigh remains available. The recoverable
  conversation says that the response limit was reached, confirms no repair was applied, preserves
  saved measurements, and offers the existing user-triggered Retry Shepherd action without
  exposing raw provider diagnostics or silently purchasing another model call. The common gate
  passes with 233 tests, two intentional live-provider skips, lock validation, Ruff, formatting,
  and zero Pyright findings.

- D097 responsive target and active-scene presentation: destination and viewing-use choices now
  share one target card, use labels describe the user's use case rather than polygon terminology,
  and reflow from the conversation lane's actual width. Below 1,151 pixels the one shared 3D scene
  moves into the active notebook cell instead of occupying an inaccessible side column; desktop
  keeps the sticky resizable scene. The Topology action now states how the confirmed use case
  affected simplification. The saved Stylized Radio Handset run therefore explicitly reports that
  4,327 triangles were preserved because they are below the 15,000-triangle normal-gameplay soft
  cap. The repaired-GLB response was independently verified as a named attachment; Codex's embedded
  browser requests it and then resets the connection, so Chrome or Edge remains necessary for local
  downloads. The common gate passes with 231 tests, two intentional live-provider skips, lock
  validation, Ruff, formatting, and zero Pyright findings.

- D096 Gemini 3.8 Flash comparator: native Gemini structured intake and Strands workflow adapters
  now preserve the same typed authority boundary and standardized rendered evidence used by other
  models. The exact `gemini-3.8-flash` ID is allowlisted; `xhigh` maps to Gemini `high`; tool-result
  screenshots are emitted as native image parts; and the Windows launcher decrypts a separate
  current-user DPAPI secret only for the server child process. The fixed acceptance runner accepts
  Gemini. A live structured-intake smoke proposed plausible riding-crop bounds, and the full
  `broken-normalization` case passed safety, semantic, visual, approval, and packaging gates in
  89.91 provider seconds using 307,454 input and 20,274 output tokens. This is one representative
  pass rather than D094's eight-case release gate. Gemini remains outside the canonical AWS
  production topology. The common gate passes with 231 tests, two intentional live-provider skips,
  lock validation, Ruff, formatting, PowerShell parsing, and zero Pyright findings.

- D095 opt-in Muse Spark 1.3 comparator and architecture-diagram review: the Meta Model API now
  sits behind the same Strands model boundary for local evaluation, with one reviewed endpoint,
  fail-closed model IDs, DPAPI-protected credentials, and a provider shim that places standardized
  renders in user messages. The lower-cost `muse-spark-1.3-contributor` model cannot run unless the
  exact `ASSET_SHEPHERD_ALLOW_META_TRAINING=1` consent flag is present; production must use the
  standard model without that flag. Three live high-reasoning cases passed: clean no-op,
  riding-crop component selection, and robot-dog preservation. They used 611,951 input and 14,303
  output tokens over 415.88 provider seconds, approximately $0.0641 at the selected Contributor
  rates. This is a promising three-case sample, not D094's eight-case production gate, so Kimi on
  Bedrock remains the AWS candidate. A separate Terra/xhigh review simplified the canonical AWS
  diagram into a clearer left-to-right browser → web → agent flow, consolidated deterministic GLB
  mutation and Chromium rendering, and retained every storage, identity, observability, and deploy
  relationship without implying that any AWS application resource is already deployed. A follow-up
  architecture review collapses ALB/TLS/Fargate/networking into the ECS Express abstraction,
  removes Route 53/custom-domain polish, and labels AgentCore as an IAM-authorized regional API
  rather than implying PrivateLink or custom VPC networking. The common
  gate passes with 228 tests, two intentional live-provider skips, lock validation, Ruff,
  formatting, PowerShell parsing, valid SVG/PNG artifacts, and zero Pyright findings.

- D094 provider acceptance and bounded completion: the checked-in provider-neutral matrix freezes
  eight representative cases and requires 8/8 safety plus at least 7/8 semantic/visual passes.
  Kimi K2.5 passes 8/8 on both measures: clean no-op, broken normalization, degenerate cleanup,
  Patchling preservation, Shader Lantern normalization, riding-crop component selection, robot-dog
  component preservation, and shattered-heart collar simplification. Compatible split runs
  aggregate only when provider, model, case, and source hash match. The selected ledger records
  1,007,046 input, 14,277 output, and 1,021,323 total tokens over 366.86 provider seconds—about
  $0.65 at the current standard `us-east-1` rates before credits. Mistral Large 3 fails the
  riding-crop visual/component decision and proposes destructive component removal for the coherent
  collar, so it cannot meet the 7/8 semantic threshold. An inherited Bedrock socket wait that held
  one call for roughly seven hours is replaced by one bounded five-minute read with no SDK retry.
  A thin-render regression also lowers the absolute mask floor to 0.1% while retaining the separate
  8% projected-span, clipping, and blank-image checks; the riding crop then passes end to end.
  The common gate passes with 224 tests, two intentional live-provider skips, lock validation,
  Ruff, formatting, and zero Pyright findings.

- D093 deployment topology: this decision established the AWS boundary before deployment. D103–D105
  subsequently made the browser-facing ECS Express service, SQS/Lambda bridge, AgentCore/Strands
  runtime, Bedrock inference, S3/DynamoDB state, ECR/CodeBuild images, and IAM roles live. The
  checked-in AWS-style SVG and rendered PNG now distinguish that deployed request/data flow from the
  remaining Step 7 operations and optional external-provider work.
  AWS has closed App Runner to new customers, so D093 supersedes D075 and selects one stateless ECS
  Express Mode web container beside an IAM-controlled AgentCore Runtime, with S3 as immutable
  artifact/session storage and DynamoDB as the conditional workspace/command pointer.

- D092 use-case-driven controlled mesh simplification: target confirmation now asks whether the
  asset will normally be seen close-up/showcase, at ordinary gameplay distance, or
  small/distant/repeated. Those ordinary-language choices freeze soft caps of 50,000, 15,000, and
  2,500 triangles; normal gameplay is the explicit default, and the user may reject any later
  optimization proposal. A typed approval-required `SIMPLIFY_MESH` action processes each exact
  source component separately through pinned local meshoptimizer, copies components below 1,000
  triangles exactly, retains only complete source attribute tuples, and preserves materials, UVs,
  normals, named nodes, bounded near-contact grouping, and bounds within two percent. Unsupported
  layouts fail closed. Independent verification reloads the result, proves protected components and
  untouched payload, and reports actual triangle and byte changes. A synthetic 20,480-triangle
  sphere reduces toward the 15,000 cap and passes; rejection preserves exact bytes. The real
  783,571-triangle shattered-heart collar reaches 56,885 triangles and 7,709,808 bytes while
  protecting 3,611 triangles across 63 small components; it correctly reports that preservation
  constraints prevented reaching 15,000. Direct OpenAI Luna xhigh independently chose the isolated
  simplification, preserved the intentional component assembly, and produced a ready 56,885-
  triangle, 7,710,004-byte candidate from the normalized 30,204,752-byte input. Its ledger records
  376,106 tokens and 123.75 seconds including bounded recovery. The live run also revealed and fixed
  shared-scale comparison clipping caused by `<model-viewer>` clamping orbit distance against only
  its primary model; comparison-specific headroom, an expanded post-load orbit limit, and a real-
  browser two-model framing test now cover it. The common offline suite passes with 218 tests and
  two intentional live-provider skips. After interactive AWS reauthentication, Bedrock Converse/
  Kimi K2.5 independently selected the same action and produced the byte-identical candidate in
  94.96 seconds using 159,666 tokens, without post-approval recovery. This was 23% less observed
  time and 58% fewer recorded tokens than the Luna run, although Luna's total includes recovery and
  the result is evidence for provider parity on this case rather than a general model ranking.

- D091 portable model-visible rendering: agent-required evidence now uses the vendored
  `<model-viewer>` 4.3.1 runtime through headless Chromium, not a locally installed Blender process.
  The loopback-only renderer fixes the four glTF source-axis views, preserves shared-scale
  source/candidate placement, captures transparent PNGs, derives object masks, composites the dark
  audit frames, and passes the unchanged visibility/framing checks. A clean robot passed all four
  views; a comparison preserved the actual 1.8 m-versus-182 m scale difference; and the exact
  30.2 MB, 783,571-triangle shattered-heart collar rendered four validated 512 px textured views in
  about 3.5 seconds in the local smoke invocation. Blender remains an explicit local compatibility
  fallback. The Step 4 clean-Linux container and cold-start gates remain open because Docker is not
  installed on this workstation. The common gate passes with 213 tests, two opt-in live skips,
  lock validation, Ruff, formatting, JavaScript syntax validation, and zero Pyright findings.

- D090 shattered-heart collar benchmark and conversation observability: the exact 30,204,480-byte
  Meshy GLB (`30ca4838…`) measures 1.898 × 0.623 × 1.880 m, contains 783,571 triangles, and presents
  65 exact disconnected components in one near-contact group. Kimi K2.5 inferred the intended
  15 × 3 × 12 cm target, proposed removing 64 tiny fragments, and produced a partial candidate whose
  independent check still found 12 bodies. After the user's explicit scale refinement, its second
  turn passed at 11.84 × 3.89 × 11.73 cm. Direct OpenAI Luna xhigh preserved the coherent 65-part
  assembly and reached the same grounded proportional fit in one repair turn. Luna's complete
  Shepherd ledger records 161.74 seconds and 412,929 tokens; the old Kimi artifacts retain a
  257,998-token lower bound and 167.25 seconds from only their resumed calls, so no exact cost ranking
  is claimed. Every future completed Shepherd call is now atomically recorded in
  `agent_invocations.json` and aggregated after interrupt/resume. Approval and refinement submissions
  immediately append the user's exact pending message before synchronous work begins. The tracked
  benchmark runbook records both outcomes while its raw GLB and screenshots remain local and ignored
  pending explicit public-use confirmation. The common gate passes with 211 tests, two opt-in live
  skips, lock validation, Ruff, formatting, JavaScript syntax validation, valid benchmark JSON, and
  zero Pyright findings.

- D089 bounded visual evidence and interruption recovery: the robot-dog workspace
  `5919c759657048248bfd8db56968c5b4` executed its approved uniform resize and name cleanup, then
  Kimi rejected the next request because the accumulated twelve full-resolution PNG evidence blocks
  exceeded its documented 3 MB image-payload limit. Model-facing evidence is now three compact
  768 × 256 JPEG contact sheets—source, candidate, and shared-scale—while every original PNG remains
  unchanged for the UI and evidence package. A provider error after durable execution consumes the
  old approval, restart migrates the equivalent pre-fix state, and the UI distinguishes **Applied —
  verification has not completed** from an actual failed verification. The exact saved run resumed
  without another mutation, passed Kimi visual reassessment and every deterministic check, and now
  offers its verified 3.50781 × 3.44959 × 7.43772 m candidate. Five intentional disconnected forms
  remain an explicit warning. The common gate passes with 211 tests, two opt-in live skips, lock
  validation, Ruff, formatting, JavaScript syntax validation, and zero Pyright findings.

- D088 agent-proposed approximate sizing: recognizable assets no longer fall through to mandatory
  X/Y/Z entry merely because a model treats an ordinary scale analogy as uncertain. Intake now
  defines relative clues such as bus-sized, person-sized, handheld, and building-sized as sufficient
  for a confirmable approximate proposal, makes dimension confidence about usefulness rather than
  exact knowledge, and performs at most one focused retry when an otherwise valid proposal omits or
  confidence-gates its size. The fallback label is **Approximate target size**, not **Tight target
  bounds**. A live Bedrock Converse/Kimi check of `a quadrupedal robot dog, about the size of a bus`
  proposed 250 × 300 × 1,200 cm and left only the genuinely missing endpoint unresolved. Regression
  coverage reproduces a first-pass omission and successful retry. The common gate passes with 207
  tests, two opt-in live skips, lock validation, Ruff, formatting, JavaScript syntax validation, and
  zero Pyright findings.

- D087 terminal gallery return: an accepted Download cell now ends with one explicit **Return to
  gallery** action, a carriage-return mark, and an original local four-frame Patchling sprite that
  runs into a cream/mint dust cloud on hover or keyboard focus. Reduced-motion preference keeps the
  first frame still. Accepted terminal workspaces now reopen from deterministic artifacts without
  loading an obsolete live-model snapshot; this makes an older direct-OpenAI result readable and
  downloadable while the current server uses Bedrock. Route acceptance verifies the link, PNG,
  provider-neutral terminal reload, model download, and evidence package. Browser acceptance on the
  completed Rugged Tablet workspace covers final placement, hover animation, and gallery navigation
  without changing the accepted workspace. The common gate passes with 206 tests, two opt-in live
  skips, lock validation, Ruff, formatting, JavaScript syntax validation, and zero Pyright findings.

- D086 target-engine help: the focused Unity/Unreal/Godot/Other clarification now places a compact
  question-mark control beside the agent's prompt. Its modal explains that the result remains GLB,
  identifies the consumer frames and target-specific handoff emphasis, covers a described custom
  destination, and explicitly avoids implying new rigging, animation, retopology, or proprietary
  conversion capabilities. Hosted-route, browser, and common-gate acceptance pass.

- D085 immediate model-working feedback: submitting Describe now appends a live Asset Shepherd
  message that explains it is reading the description and drafting a target, instead of hiding the
  form and appearing hung during the synchronous model call. Pollable Shepherd/Refine activity keeps
  its bounded tool labels but replaces the generic dashed spinner with an original four-frame
  Patchling sprite. A still first frame from the same locally served transparent sprite sheet sits in
  the persistent workspace header immediately left of the page title, and reduced-motion holds a
  still frame while retaining all status text. A desktop rail preview uses a right-pointing chevron
  to pin itself; a persistent rail uses the matching left-pointing hide chevron. Static-route,
  browser, and common-gate acceptance pass.

- D084 adjustable workspace chrome: the desktop evidence column now has a persisted drag and
  keyboard separator that grows the 3D scene without allowing the conversation below 500 px. The
  workflow rail collapses persistently, peeks from a double-line edge target on fine pointers, and
  restores from an explicit arrow control on touch devices. Responsive one-column layouts retain a
  full-width scene and hide the inapplicable separator. Browser acceptance on the completed Giant
  Aria workspace confirms collapse, reclaimed notebook width, temporary edge-peek, and pinned
  restoration. The user also reports that the same live run correctly normalized the character from
  roughly 100 m to roughly 1.5 m; this is useful real-world evidence but remains separate from the
  layout acceptance. Focused web acceptance and the common quality gate pass.

- D083 active-turn timeline: completed notebook cells are now read-only except for an explicit
  **Rewind…** boundary on Upload and Describe. Each disclosure explains that valid upstream edits
  recalculate dependent target and repair work while the saved version remains intact until
  validation. Submitting any active command makes every prior cell inert and removes its action
  surface; only the appended working cell owns the turn. Accepted repair cells become complete and
  Download becomes the sole current cell. The exact completed Bipedal Woman workspace
  `147bb61536204af0aa852aa460e9412d` reconstructs after a clean server restart with a combined
  **Uploaded model and Candidate** viewport even after transient execution outcome state is absent.
  Current-turn bootstrap no longer eagerly swaps that comparison for the upload-only scene before
  anchor positioning settles. Focused hosted/runtime and web acceptance pass; the common gate passes
  with 206 tests, two opt-in live skips, lock validation, Ruff, formatting, JavaScript syntax
  validation, and zero Pyright findings.

- D082 conversational notebook: Upload, Describe, Shepherd, and Refine now read as one alternating
  transcript with user messages on the right and Asset Shepherd messages on the left. One sticky
  right evidence column keeps the active immutable 3D state visible; scroll proximity swaps its
  scene without moving or duplicating the renderer. Pending plans no longer expose a raw composer:
  **Apply recommendations** is immediate, structured changes become **Send selected changes**, and
  **Add comment…** reveals the only text area and **Send feedback** action. Target and result states
  similarly expose **Start shepherding** / **Change target…** and **Use this version** / **Refine…**.
  Prompt v15 distinguishes interface-only transitions from typed `PLAN_REVISION` and
  `RESULT_REFINEMENT` turns, keeps the selected iteration authoritative, and routes fresh sensing,
  tools, approval, and stop behavior. Browser acceptance on workspace
  `49384ee553284bd4b5bfc9bdc3b79bdd` confirms the readable desktop transcript, sticky component
  evidence, and hidden-until-requested feedback composer. The common gate passes with 206 tests,
  two opt-in live skips, lock validation, Ruff, formatting, JavaScript syntax validation, and zero
  Pyright findings.

- D081 live-activity correction: confirming Describe no longer replaces the notebook with a
  standalone progress checklist. The completed Upload and Describe cells remain in the vertical
  conversation, while the bounded tool trace is appended as the current **3 Shepherd** cell. Other
  long-running turns keep their trace inside the current notebook cell rather than hiding prior
  history. Focused hosted/web acceptance passes with 51 tests; the full gate passes with 205 tests,
  two opt-in live skips, lock validation, Ruff, formatting, and zero Pyright findings. The main
  local Luna server has been restarted on port 8010 with the corrected assets.

- D081 full-lifecycle notebook: Upload and its parse result, Describe and confirmed target,
  Shepherd, every Refine iteration, and Download now render as one chronological workspace instead
  of page-replacement steps. Upload and Describe expose scoped edits; invalid replacement uploads
  preserve the prior staged asset, while a valid replacement restarts dependent work from Describe.
  The exact saved workspace `4bb293f48f86476a9ae08fdadee4fb1b` reconstructs Upload, Describe,
  Shepherd, and Refine 4.1 in order with three lazy scene slots and exactly one live 3D viewer.
  Acceptance reveals a separate appended Download cell without a page reload. The full gate passes
  with 205 tests, two opt-in live skips, lock validation, Ruff, formatting, and zero Pyright findings.

- D080 append-only notebook and bounded completion recovery: the exact successful Kimi riding-crop
  run `91b21e479f914f80888c266d473b06d4` ended after recording a positive candidate reassessment but
  before calling deterministic verification/package. The recovered turn independently verifies and
  packages on reload without another model call because its decisions, executed outcome, provenance,
  and required visual reassessment are all present; incomplete or interrupted turns remain fail-closed.
  The workspace now keeps description, proposal, user decision, outcome, and model state together in
  scroll order instead of replacing its contents after approval. Browser acceptance on the exact run
  shows no failure banner and one live 3D viewer; a saved two-iteration run exposes both chronological
  scene slots and rail navigation while maintaining exactly one `<model-viewer>`. The full gate passes
  with 204 tests, two opt-in live skips, lock validation, Ruff, formatting, and zero Pyright findings.

- D079 shared-scene notebook: completed turns now render as ordered Asset Shepherd outcome,
  hash-bound 3D state, and user reply cells. The turn nearest the viewport center receives the only
  live scene; historical GLBs resolve against `conversation.json` `output_sha256`, load only on
  demand, and are replaced when another turn takes over. Shepherd/Refine rail links navigate and
  highlight the active state. Browser acceptance on the saved two-iteration Riding Crop swaps from
  `/turns/0/model.glb` to the current model and back while keeping exactly one `<model-viewer>` and
  producing no console errors. Focused route/store tests cover lazy scene HTML and fail-closed hash
  mismatch behavior. The full gate passes with 204 tests, two opt-in live skips, lock validation,
  Ruff, formatting, and zero Pyright findings.

- Luna access recheck on 2026-08-30: the model-access API still reports authorization, entitlement,
  and `us-east-1` region availability, but `agreementAvailability.status` remains `NOT_AVAILABLE`.
  A bounded call to the documented Bedrock Runtime Responses endpoint returns HTTP 403 stating that
  `openai.gpt-5.6-luna` is unavailable for this account. This rules out the application adapter and
  ordinary runtime-role IAM as the current blocker; Kimi remains the working recommended provider.

- D079 atomic approval turn: the exact three-component riding-crop run was not a detector failure;
  the agent explicitly classified the three bodies as intentional handle/shaft/paddle parts. The UI
  now keeps that recommendation as the default while exposing every deterministically safe C1/C2/C3
  Keep/Remove choice. Structured choices and one wide whole-turn comment submit together; any
  change becomes **Send revision**, archives the old proposal, and resumes the agent without
  mutation. Prompt v14 preserves the agent/deterministic authority boundary, and focused component,
  prompt, and hosted-workflow tests pass. Browser acceptance on the exact saved workspace confirms
  three Keep/Remove controls, one whole-turn composer, the dynamic revision contract, one live 3D
  viewer, and the readable stacked layout at the in-app viewport width. The common gate passes with
  202 tests, two opt-in live skips, lock validation, Ruff, formatting, and zero Pyright findings.
  This is the approval/composer slice of the now-complete shared-scene notebook presentation.

- D078 Claude Haiku 4.5 evaluation: the accepted AWS Marketplace agreement exposed the active US
  inference profile `us.anthropic.claude-haiku-4-5-20251001-v1:0`; direct on-demand invocation was
  correctly rejected, so the product registers the working profile rather than the foundation-model
  ID. The `AssetShepherdBedrockRuntime` role received only `InvokeModel` and
  `InvokeModelWithResponseStream` on that exact profile and its three routed foundation-model ARNs.
  A runtime-profile smoke call and both opt-in typed-intake/full-Strands tests pass; the full test
  includes image evidence, tools, approval, mutation, verification, and packaging in 58.13 seconds.
  Haiku is exposed as an experimental speed/quality/cost comparison, not a replacement for the
  recommended Kimi model. The same runtime role now successfully invokes all five visible choices.

- D077 model-neutral Converse provider: Upload now exposes one compact, server-side allowlist with
  Kimi K2.5 recommended, experimental Mistral Large 3 and Qwen3 VL alternatives, and Nova 2 Lite as
  a lower-cost diagnostic. The selected provider/model is persisted through staged upload, durable
  workspace, restart, and Refine; arbitrary model IDs fail closed. One capability registry owns
  output limits, Nova-only reasoning controls, user hints, and the proven Bedrock layout difference
  that requires Kimi/Mistral/Qwen render images to sit beside rather than inside tool results.
  Kimi passed the live typed-intake test and complete Strands approval-through-package workflow in
  66.71 seconds with image evidence, seven successful workflow tools, one native interrupt, prompt
  v13, and a verified candidate. Browser inspection confirmed the four choices and hints and carried
  Kimi from Upload into Describe; the hosted intake retry then encountered an expired bootstrap AWS
  login token, not a model or application validation error. The login was renewed and exact runtime-
  role resources now pass Kimi/Mistral/Qwen/Haiku/Nova smoke calls. D094 later replaces ad hoc
  smoke comparison with the fixed eight-case Kimi release gate. The common gate passes with 201
  tests, two opt-in live skips,
  lock validation, Ruff, formatting, PowerShell parsing, and zero Pyright findings; both Kimi live
  tests pass when explicitly enabled.

- D076 Grok 4.6 access diagnostic: AWS's model-access API reports `xai.grok-4.6` agreement,
  authorization, entitlement, and region availability as available/authorized, and both the US and
  global inference profiles are active. Nevertheless, bounded calls through both the documented
  Bedrock Responses endpoint and native Converse return `AccessDeniedException` stating that Grok
  4.6 is unavailable for this account. The same result occurs with the administrator profile, which
  has `AdministratorAccess`, so ordinary IAM expansion, profile choice, API choice, and inference
  profile choice are ruled out. No inference executed. Asset Shepherd will not add a fourth
  maintained provider path until AWS accepts a direct smoke call; the existing generic Responses
  bridge would then need only a narrow xAI profile-validation change before behavioral testing.

- D075 historical remote topology: App Runner was selected before implementation and before AWS
  closed it to new customers. D093 supersedes only that host choice with ECS Express Mode; the
  separate private AgentCore, S3 artifact/session, conditional DynamoDB command-state, local-launcher,
  browser-permission, and disposable-compute boundaries remain intact. No resource from either
  proposed topology has yet been deployed.

- D074 Nova diagnostic provider: `bedrock-nova` now runs Amazon Nova 2 Lite through native Bedrock
  Converse while preserving `bedrock` as the Luna/xhigh Responses baseline. Nova semantic intake
  forces the same single typed submission, normalizes only the provider-facing tool schema, and
  retains strict Pydantic validation. Medium reasoning, temperature zero, and 4,096/8,192 output
  limits keep the trial deterministic and bounded; unsupported `high`/`xhigh` settings fail closed.
  The runtime role received a separate exact-resource Nova policy. Live evidence includes a
  63-token connectivity call, a correct Computer Chip intake proposal, and a complete Strands
  approval-through-package test in 113.83 seconds. A separate browser run then exercised upload,
  typed intake, sensing, retry, user correction, structured approval, mutation, visual
  reassessment, independent verification, and packaging. Medium reasoning first exhausted the
  8,192-token output limit; low reasoning resumed but initially repaired names only. After the user
  explicitly identified the ignored scale defect, Nova proposed an approval-gated proportional fit
  and produced a verified `1.22376 x 0.820321 x 0.268958 m` candidate grounded at `Y=0`, with only
  the pre-existing material-budget warning. Nova is therefore usable as a diagnostic/fallback but
  is not the default parity model: first-turn completeness and multi-minute correction latency need
  more evaluation. This removes account/IAM/Strands as the Luna blocker but does not complete Luna
  parity or the representative browser matrix. The current common gate
  passes with 191 tests, two opt-in live skips, lock validation, Ruff, formatting, PowerShell
  parsing, and zero Pyright findings; both Nova opt-in tests also pass when run explicitly.

- D073 Bedrock Responses implementation: semantic intake now forces one exact
  `submit_target_intake` tool submission through Bedrock-hosted Luna/xhigh and preserves the existing
  Pydantic/confidence boundary. The Strands workflow now uses the same regional Responses endpoint,
  complete-response bridge, sequential tools, stateful IDs, and request-scoped IAM-derived bearer
  token instead of Converse. Bedrock launcher mode requires explicit model/region settings, removes
  inherited `OPENAI_API_KEY`, and does not fall back to OpenAI. Unit acceptance covers malformed and
  repeated intake calls, runtime URL/model provenance, token safety, workflow tool events, and
  launcher separation. The common gate passes with 187 tests, two opt-in live skips, lock
  validation, Ruff, formatting, and zero Pyright findings. The verified least-privilege role minted
  a short-term token. The first
  bounded request reached the selected `us-east-1` endpoint, but AWS rejected inference with the
  documented new-account verification HTTP 403; no behavioral parity is claimed yet.

- D072 official-rules compliance audit: the 2026-08-29 Devpost rules snapshot confirms that the
  Bedrock-hosted OpenAI Luna choice is eligible because the contest requires genuine Strands
  orchestration, not a particular foundation-model vendor or Bedrock API. The implementation is a
  compliant local Strands agent and began during the submission period, but the finished submission
  is not yet compliant in all respects: the GitHub repository remains private, free remote judge
  access through October 8 is absent, and final architecture, public video, Builder ID, release
  scans, disclosures, and entrant attestations remain open. `docs/CONTEST_COMPLIANCE_PLAN.md` turns
  the live rules into six mandatory release gates and two rules-day rechecks. The obsolete literal
  `#AgentsforHumans` requirement is corrected while retaining the safer plain event name in post
  titles. The common gate passes with 177 tests, one opt-in skip, lock validation, Ruff, formatting,
  and zero Pyright findings.

- D071 Bedrock model parity choice: the user selected the same workflow baseline that produced the
  successful local runs—OpenAI GPT-5.6 Luna at `xhigh` reasoning—but served by Amazon Bedrock rather
  than the direct OpenAI API. Read-only account inspection in `us-east-1` confirms the active
  `openai.gpt-5.6-luna` model accepts text and images and exposes the active
  `us.openai.gpt-5.6-luna` geographic inference profile across three US regions. The parity gate
  will use Bedrock's OpenAI-compatible Responses endpoint, short-term AWS-derived bearer tokens,
  sequential custom tool calls, and the unchanged typed server boundary. Bedrock does not advertise
  native structured output for this model, so semantic intake will use a constrained typed tool and
  retain the existing Pydantic/confidence failures. The budget alert and separate least-privilege
  `asset-shepherd` role/profile are confirmed. The first bounded inference request reached Bedrock
  but was rejected before execution by AWS's new-account verification hold.

- D070 deployment procedure: `docs/BEDROCK_DEPLOYMENT_RUNBOOK.md` separates the M9 move into a local
  Bedrock provider gate, cloud-portability gate, and remote-product gate. It preserves
  `workspace_id` as the per-asset session authority, selects Strands S3 snapshots plus private S3
  artifacts and conditional DynamoDB workflow state, keeps the interactive web app separate from
  AgentCore, and makes the local Blender visual-sensing dependency an explicit portability gate.
  Step 1 begins with credential-free workstation inspection; paid calls and resource creation still
  require identity, model/region, budget, and cost checkpoints.
- D070 Step 1.1 preflight: WinGet reports a per-user AWS CLI v2.36.34 installation and the executable
  runs successfully by absolute path. The current Codex process inherited an older PATH and cannot
  resolve `aws`; a fresh terminal should. No AWS config or credentials file exists yet, so no caller
  identity, region, model access, or budget assertion has been made.

- D069 comparison-control consolidation: comparison viewers now replace the passive square glyph
  and separate Both/Before/After buttons with one square **Cycle viewpoint** action. It advances
  Both → Before → After → Both through the existing smoothly interpolated fit path and updates its
  hover and accessible text with the current and next view. Source-only viewers retain one direct
  fit-to-window button. Live browser acceptance on the completed Humanoid Woman workspace exercised
  all three transitions and returned to Both with no console errors. That real run also reduced a
  76.6 × 97.8 × 26.3 m source to a proportionally fitted 0.787 × 1.01 × 0.271 m candidate while
  preserving appearance, pose, grounding, resources, and protected topology seams. The common gate
  passes with 177 tests, one opt-in skip, lock validation, Ruff, formatting, and zero Pyright
  findings.

- D068 refinement interaction correction: the generic disclosure widget has been removed. The
  blocked result initially presents one standard, center-aligned **Refine…** button. Activating it
  removes that button, focuses one full-width 148 px multiline editor, and places **Start refining**
  in the original action position beside the secondary diagnostics and Gallery controls. The field
  retains an accessible label without adding another visible title. Live browser inspection of the
  persisted riding-crop workspace confirms the pre-click and post-click DOM states and the expanded
  visual layout. The common gate passes with 177 tests, one opt-in skip, lock validation, Ruff,
  formatting, and zero Pyright findings.

- D068 safe component-selection recovery: a persisted riding-crop pass measured three exact,
  safely removable components but the agent treated uncertainty about the intended survivor as an
  unsupported repair. Prompt v13 now directs the agent to use all four views, propose plausible
  exact component IDs with reduced confidence, and defer the consequential choice to the existing
  per-component review. Component selection precedes normalization so stray-body bounds do not
  defeat the useful first repair. The saved workspace now says the pass stopped before choosing
  labeled forms, distinguishes this from a truly unsupported GLB layout, and exposes **Refine
  current iteration** over the preserved input. Browser inspection on port 8011 confirms the
  corrected Asset Shepherd message, inspection action, and recovery control. No mutation was
  automatically submitted. The common gate passes with 177 tests, one opt-in skip, lock
  validation, Ruff, formatting, and zero Pyright findings.

- D067 pending-origin preview: approval pages no longer imply that an unexecuted pivot repair has
  already happened. The current iteration retains a labeled **Current origin** marker, while the
  typed normalization payload supplies a distinct **Proposed origin** marker at its exact
  source-space target. The Asset Shepherd sentence is explicitly prospective until approval. On
  the live Equestrian Riding Crop workspace, browser inspection confirms the proposed marker at
  `(-0.0332031623, 0.6083984673, 0.0) m`, visually centered in the surviving component's bounds,
  with the authored origin still shown below it. The common gate passes with 176 tests, one opt-in
  skip, lock validation, Ruff, formatting, and zero Pyright findings.

- D066 incomplete-planning recovery: the live Responses trace for the failed Equestrian Riding
  Crop run showed a valid return-to-creation conclusion trapped by an empty optional pivot ID and
  report-only screenshot citations, then repeated until the 12-call bound. The deterministic
  boundary now treats a blank optional ID as absent and validates any cited source views regardless
  of disposition. A pre-approval failure preserves the measured job and offers **Retry Shepherd**
  through a fresh bounded invocation; post-action recovery remains **Finish this iteration**. The
  original workspace was recovered from the model's recorded proposal without another mutation or
  user re-entry and now packages a BLOCKED diagnostic result with no error. Browser inspection on
  port 8011 shows the Asset Shepherd explanation, check table, diagnostics download, and Gallery
  action instead of the generic Stopped alert. Targeted agent, hosted-state, and web coverage passes
  with 72 tests and one opt-in skip. The full common gate passes with 176 tests, one opt-in skip,
  lock validation, Ruff, formatting, and zero Pyright findings.

- D064/D065 pivot and speaker checkpoint: a new read-only sensing tool returns source-hash-bound
  origin candidates for authored origin, bounds centers/corners, surface centroid, long-axis end
  regions, and a uniform-volume centroid only for topology proven closed and consistently wound.
  The live agent can select only one registered ID after citing all four coordinate views; the
  deterministic planner resolves coordinates, previews the exact root translation, requires
  approval, and independently verifies the measured point at origin. The surviving riding-crop
  candidate produces distinct Z-min and Z-max end-region centers, addressing the prior
  handle-center capability gap without arbitrary XYZ. Prompt v12, schemas, and regression tests
  cover the boundary. Agent-authored workflow prose now uses one consistent Asset Shepherd speech
  bubble on Upload, Describe, target confirmation, approval, completion, and refusal screens.
  Browser inspection confirms the speaker treatment, border, background, and bubble tail. The
  common gate passes with 175 tests, one opt-in skip, lock validation, Ruff, formatting, and zero
  Pyright findings.

- D063 Refine-loop checkpoint: the first Shepherd result now offers an explicit survivor choice
  between its input and candidate. The selected immutable GLB becomes Iteration 1; subsequent
  passes appear as 4.1, 4.2, and later Refine sub-items and record selection plus source hash in the
  append-only turn chain. The hosted source route and viewer use that selected iteration rather
  than the original upload. Indexed world bounds now ignore deleted-but-unreferenced tuples while
  retaining them as a separate cleanup finding. Trimesh verification independently measures only
  face-referenced geometry, so exact component removal verifies without conflating retained binary
  payload with renderable bounds. Prompt v11 makes post-deletion bounds and origin evidence stale,
  requires candidate-relative reassessment, and reserves any pivot correction for a fresh approved
  Refine proposal. A stable per-workspace agent ID restores interrupts across candidate filename
  changes, and an interrupted post-action pass exposes a non-mutating Finish-this-iteration recovery
  action. Browser acceptance on the persisted riding crop shows one component, a 35.4 × 27.1 ×
  97.5 cm box, the still-independent origin, and Step 4.1 Iteration 1. The interrupted approved
  cleanup then finished without repeating mutation, independently verified, packaged, and rendered
  an Iteration 1/Iteration 2 comparison containing only the surviving crop. Blender comparison
  framing now refreshes translated world matrices before camera fitting, eliminating the clipped
  evidence that had blocked recovery. The common gate passes with 173 tests, one opt-in skip, lock
  validation, Ruff, formatting, and zero Pyright findings.

- D062 component-review presentation follow-up: the source viewport now keeps every detected
  component's live wireframe bounds and C-label visible by default, so the C1/C2/C3 choices map
  directly to the model without hover. A stable six-color palette now gives each action item and its
  corresponding 3D box the same color; hovering or focusing one choice strengthens both together
  while every other labeled box stays visible. Chrome acceptance on the persisted three-part
  riding-crop workspace confirms cyan C1, gold C2, and magenta C3 correspondence, synchronized C3
  focus, and no console errors. Upload also includes one collapsed `What about FBX?` note that keeps
  GLB primary while answering the predictable format question without another heading. The common
  gate passes with 170 tests, one opt-in skip, lock validation, Ruff, formatting, and zero Pyright
  findings.

- D062 bounded component-selection checkpoint: static indexed triangle primitives now expose stable
  exact position-projected bodies rather than guessing semantic pieces from node or primitive
  counts. Scale-relative near-contact probes can group bodies separated by tiny gaps, but remain
  read-only hints and never alter exact IDs or authorize a repair. The workflow agent must cite four
  source views and select exact IDs; the single topology row shows all bodies, highlights their live
  world-space wireframe bounds, and lets the user keep, remove, or comment on each selection. A
  changed selection returns to the same agent without mutation. Approval filters only the selected
  index triples in proven-safe, unskinned, one-instance layouts; it refuses unknown IDs, total
  deletion, morphs, compression, sparse/extended accessors, malformed data, and pending degenerate
  cleanup. Independent verification proves the exact triangle delta and retained component count.
  Synthetic three-body removal and near-gap false-positive coverage pass. A live browser run with
  three separated tetrahedra completed upload → description → agent sensing → exact component
  proposal → per-body approval → removal → independent visual reassessment: the agent retained C1,
  removed C2/C3 (eight triangles), and verified one remaining four-triangle body. Per-view
  orthographic evidence fitting prevents long, thin layouts from becoming invisible in side views;
  the regenerated right view spans 71.5% of the frame instead of a few pixels. The common gate
  passes with 170 tests, one opt-in skip, lock validation, Ruff, formatting, and zero Pyright
  findings. Broader corpus acceptance remains in the D062 follow-up gate.

- D061 degenerate-geometry cleanup checkpoint: objective inspection now distinguishes a safely
  cleanable indexed triangle-list layout from an unsupported topology layout. A live agent may
  request one separate consequential action that removes only proven zero-area triangle triples and
  compacts only complete vertex tuples no surviving triangle references. The exact affected
  primitive and before/after counts are approval-bound; execution retains the source binary as an
  immutable prefix and remaps every aligned attribute together. Independent verification compares
  all surviving expanded corners, confirms the exact triangle/vertex deltas, and requires zero
  remaining degenerate or unused records. The checked-in failure fixture moves from 12 triangles / 24
  positions to 11 / 23 when approved; rejection preserves the original bytes and both findings. The
  single inspection table now exposes those defects and the exact action instead of hiding them
  behind generic topology counts; completed summaries retain unresolved warnings. Browser
  acceptance verifies the persisted warning case. The common gate passes with 165 tests, one
  opt-in skip, lock validation, Ruff, formatting, and zero Pyright findings.

- Geometry-failure and pivot-visibility checkpoint: two reproducible, parseable synthetic GLBs now
  exercise distinct post-upload failure behavior. `degenerate_triangle.glb` reports objective
  degenerate/unused geometry and remains otherwise eligible;
  `malformed_attributes.glb` exposes a POSITION/NORMAL cardinality violation and blocks repair.
  Adjacent typed manifests freeze their hashes and expected findings, and regeneration is covered
  byte-for-byte. The shared source/comparison viewport now projects a minimal `ORIGIN` crosshair at
  the GLB coordinate origin (and separate before/after origins after a repair), using the same live
  hotspot/HUD update path as the rotating 3D bounds. This completes the visible part of D053: the
  agent still selects Preserve, bounds-center, or footprint-center-bottom from intended use; the
  user accepts, rejects, or comments on that Size and pose proposal; no automatic center default or
  options menu was introduced. Browser inspection confirms the marker and 12-edge bounds render
  together. The common gate passes with 162 tests, one opt-in skip, lock validation, Ruff,
  formatting, and zero Pyright findings.

- Idle-orbit HUD registration: while the source viewer auto-orbits during active Shepherd work, one
  animation-frame loop now reprojects the complete SVG HUD from the viewer's live hotspot positions.
  The measured 3D bounds, dimension label, optional metric axes, banana target box, and banana leader
  therefore remain registered with their 3D targets instead of waiting for a user-generated
  `camera-change` event. The loop runs only while `auto-rotate` is active, stops for hidden or
  disconnected views, respects reduced-motion behavior, and retains event-driven rendering when
  idle. Targeted viewer coverage, Ruff, formatting, and Pyright pass.

- D060 unsupported-repair presentation: the persisted three-form riding-crop case now presents the
  agent's `RETURN_TO_CREATION_TOOL` disposition as a red blocked sentence and inspection lane. The
  table exposes the objective/semantic mismatch—three disconnected forms versus one expected
  piece—and states that no supported action can remove them. It no longer offers a continuation
  control when no candidate GLB exists; diagnostics and Gallery remain available. Name findings no
  longer render beside a contradictory “need no change” sentence. A focused regression and browser
  acceptance exercise the actual saved workspace. Geometry deletion remains deferred as a future,
  exact-component, explicit-approval repair domain under D060; its proposed sensor, component IDs,
  UI, mutation boundary, verification, and post-MVP acceptance cases are captured in
  `docs/FUTURE_COMPONENT_HANDLING.md`. The common gate passes with 157 tests, one opt-in skip, lock
  validation, Ruff, formatting, and zero Pyright findings.

- D059 gallery status checkpoint: every persisted asset card now shows one plain-language workflow
  state with a visible dot and text, rather than exposing the internal phase enum. Pending
  description is `Step 2 · Describe`; approval is `Step 3 · Review`; verified completion is `Step 3
  · Ready`; unresolved work is `Step 3 · Blocked`; and runtime failure is `Step 3 · Failed`.
  Neutral, amber, green, and red treatments supplement rather than replace the words. A file rejected
  during Upload does not create a project card or consume one of the seven slots; its concise error
  remains on Step 1. Route and mapping coverage exercise every durable state, and browser acceptance
  confirms the status remains readable without adding another panel or heading. The common gate
  passes with 156 tests, one opt-in skip, lock validation, Ruff, formatting, and zero Pyright
  findings.

- D058 working source and upload-preflight checkpoint: the source-only 3D viewer remains visible
  beside observable tool activity throughout Shepherd work and orbits slowly unless the user prefers
  reduced motion. With no candidate present it removes the redundant `Before` leader, retains the
  measured 12-edge world-space wireframe bounds, and labels that box with adaptive metric X/Y/Z
  dimensions. Objective preflight now rejects non-positive extents and world bounds whose largest
  extent exceeds the smallest by more than 10,000:1 before intake or agent work. Four sub-kilobyte
  fixtures exercise gibberish, truncation, malformed GLB JSON, and an FBX-shaped upload: every case
  stays on Upload, creates no workspace source, and exposes no parser internals. FBX remains outside
  the GLB-only submission scope. Browser acceptance confirms the source-only dimensions, 12-edge
  bounds, absent leader, and idle orbit state. The common gate passes with 151 tests, one opt-in
  skip, lock validation, Ruff, formatting, and zero Pyright findings.

- D057 navigation and source-context checkpoint: Gallery and Workflow are now separate high-level
  rail choices. Gallery is not numbered; a selected asset exposes only **1 Upload, 2 Describe, 3
  Shepherd**. The staged immutable GLB appears from Describe onward in the existing local viewer,
  with optional metric axes and banana reference. Its eight measured world-space AABB corners are
  joined as 12 projected wireframe edges that track camera motion instead of a flat HUD bracket.
  Desktop and 375 px browser checks show no horizontal overflow; the axes and banana toggles work,
  and the wireframe path retains 12 segments after rotation. A separate real Tripo-to-Unreal asset
  was reported usable without game-developer complaints; this remains informal field evidence. The
  common gate passes with 148 tests, one opt-in skip, lock validation, Ruff, formatting, and zero
  Pyright findings.

- D056 phase-aware action report: the shared five-lane inspection table now labels its final column
  `Proposed action` before authorization and `Action taken` after execution. Executed repairs become
  `!→✓` only when independent verification confirms their postcondition; the hover explanation
  identifies them as addressed and names the applied action. Rejected, report-only, unresolved, and
  verification-failed work retains attention styling and plainly records that no verified correction
  occurred. Route coverage exercises both a successful candidate and a forced verification failure;
  browser acceptance confirms the final table and hover explanation without horizontal overflow.
  The common gate passes with 148 tests, one opt-in skip, lock validation, Ruff, formatting, and zero
  Pyright findings.

- D055 proposal feedback and working-state checkpoint: each active repair lane now offers
  Accept/Reject/Comment before execution. All accepted lanes retain one exact `Approve`; any
  rejection or comment produces one `Revise plan` action, archives the pending plan and assessment,
  records typed feedback, performs no mutation, and resumes the same workspace-scoped Strands
  conversation. Pass and report-only rows have no controls. While that agent request is in flight,
  stale questions and response controls are hidden and only observable tool activity remains. A
  live browser check exercised the Size and pose comment field and button transition; the agent
  honored “keep the present scale” and formed a names-only replacement plan. Display-name-only
  candidates now use exact independent payload/inventory verification without a meaningless visual
  gate, while physical and topology mutations still require before/after reassessment. Regression
  coverage proves no candidate GLB exists during revision. The common gate passes with 148 tests,
  one opt-in skip, lock validation, Ruff, formatting, and zero Pyright findings.

- D054 multi-turn and observability checkpoint: a later repair now composes its delta into the exact
  immediately proven Asset Shepherd normalization root instead of adding another wrapper. Lineage
  requires the prior candidate hash, archived plan/provenance, active-root structure, identity, and
  matrix to agree; the plan records before/after matrices and independent verification permits only
  that mutation. A two-consequential-turn regression preserves node count and exactly one
  normalization root.
- Standardized source, candidate, and shared-scale renders now include object masks and fail closed
  unless every PNG decodes, contains useful foreground, has adequate projected span, stays below
  the maximum frame fill, and retains a clear margin. A real Blender fixture run measured 3.4–7.1%
  foreground, 43–44% projected span, and 26–27% minimum margin. The workflow model receives these
  quality metrics with all three render sets rather than trusting file existence.
- Hosted agent transitions now show the current and two most recent observable Strands tool actions
  instead of `Working…`. The per-workspace no-store activity record deliberately excludes reasoning
  tokens and model prose. Approval-table text is approximately 17 px with tighter spacing; 3D HUD
  labels are 13 px desktop and 11 px compact. Browser inspection confirms one title and one table.
  The common gate passes with 146 tests, one opt-in skip, Ruff, formatting, lock validation, and zero
  Pyright findings.

- D053 pivot placement: objective sensing now reports the asset origin, world-bounds center,
  footprint center-bottom, and root world origins without choosing a target. Prompt version 7 lets
  the workflow agent preserve the authored pivot or request one of two bounded center targets based
  on confirmed use and rendered/measured evidence. The deterministic planner derives the exact
  translation, rejects bounds-center plus grounding, records pivot and grounding separately, and
  independently reloads the written candidate to verify the requested anchor at the origin. Pivot
  remains part of the one grouped Size and pose approval lane. The stable live prompt is about 9.3K
  characters before job context; future specialist guidance may be delivered just in time without
  making authority or safety rules optional. The common gate passes with 143 tests, one opt-in skip,
  Ruff, formatting, lock validation, and zero Pyright findings.

- D052 persistent gallery home: Assets is now a clear header and workflow-rail destination during
  every hosted step. Returning does not mutate the active workspace, and each gallery card resumes
  the exact persisted phase. Uploads awaiting description are gallery-visible and survive an
  application restart. Redo reuses the original GLB and prior description while preserving the
  saved run until the replacement workspace is successfully created. Route tests prove a new
  workspace ID and byte-identical source; browser review confirms the seven-card gallery remains
  compact and readable.

- D051 single approval surface: the approval screen now has one semantic table with one row for
  each of five check lanes and columns for the finding, status, and proposed action. The duplicate
  repair list and synthetic `Repair plan` lane are gone. Attention icons retain hover/focus
  explanations, adaptive metric units make small targets readable, and the Computer Chip topology
  row explicitly says that no weld is proposed because 5,312 coincident positions preserve
  `TEXCOORD_0` seams. Desktop and 390 px browser checks show one table with no horizontal overflow
  or console errors. Local OpenAI Responses calls now consume a complete response inside the client
  context, eliminating the observed non-fatal stream-finalization warning while retaining response
  IDs and tool calls.

- D050 proportional box fit and transparent weld disposition: unequal X/Y/Z targets now resolve to
  the geometric mean of their per-axis ratios, the scale-invariant least-squares optimum in log
  space. One uniform transform still preserves proportions, while prompt version 6 forbids treating
  an expected residual as a failed exact-axis requirement. The supplied Computer Chip candidate's
  SHA matches the rejected run; fresh inspection measures 5.000 × 4.452 × 1.732 cm and confirms no
  weld occurred because all 5,312 coincident positions cross `TEXCOORD_0`. Topology hover evidence
  now says when welding is unavailable, and an actual safe compaction appears in the visible repair
  list. Endpoint clarification uses one sentence and product-neutral animated engine glyphs because
  third-party logo animation is not assumed to be licensed.

- D049 concise task screens and intake reliability: the Describe textarea no longer carries a
  visible `Model description` caption; its accessible name remains intact. The controlling contract
  now forbids visible subtitles or field captions that simply rename the only task or control.
  Low-confidence model output that leaves a field null while explaining its absence is normalized
  at the provider boundary, so the reproduced Computer Chip response advances with only `endpoint`
  missing instead of returning HTTP 400. Contradictory high-confidence nulls still fail validation.
  The exact description succeeds against configured Luna, desktop browser review confirms the
  caption is absent, and the common gate passes with 136 tests, one opt-in skip, Ruff, formatting,
  and zero Pyright findings.

- D048 attribute-seam presentation: protected UV, normal, tangent, color, and skinning splits are
  now described as expected glTF representation rather than defects or user repair decisions. The
  agent is instructed to ignore those counts when deciding whether the asset needs work and instead
  assess the residual position-projection boundary, non-manifold, and winding evidence. On-demand
  job details and the Markdown inspection report show those concepts separately. Position-only
  welding remains unavailable and the exact complete-tuple compaction gate is unchanged. Prompt
  version 5, route coverage, and schema provenance are current; browser review passed, and the
  common gate passes with 135 tests, one opt-in skip, Ruff, formatting, and zero Pyright findings.

- D047 seam-aware duplicate positions: every triangle primitive now records exact coincident-position
  groups, a position-only virtual-weld topology projection, complete-tuple mergeability, and the
  attributes that prevent a merge. The Computer Chip reproduces the independent Blender probe:
  5,312 coincident positions; virtual topology moves from 7,735 boundary plus 8 true non-manifold
  edges to 91 plus 50; all 5,312 remain protected by `TEXCOORD_0`, so no chip weld is registered.
  The live agent may explicitly request lossless compaction only when every vertex attribute is
  byte-identical. Append-only GLB rewriting and expanded per-corner verification prove a synthetic
  five-to-four vertex repair preserves triangles, bounds, attributes, and resources. Approximate
  target X/Y/Z boxes originally resolved to one median uniform factor with residuals recorded; D050
  supersedes that metric with a whole-box log-space optimum. Non-uniform scaling remains forbidden.
  Ruff, Pyright, 135 tests, schema regeneration, and browser review pass.

- D046 intake reliability and examples: the model-facing X/Y/Z shape now uses a closed object rather
  than a fixed tuple that emitted unsupported `prefixItems`; the deterministic target contract still
  freezes the canonical three-value tuple. Canonical Unity, Unreal, and Godot responses discard
  redundant endpoint detail before semantic validation. Provider diagnostics remain server-side and
  public failures use concise retry language. A configured live OpenAI request advanced a Unity
  humanoid description to its durable workspace. The description screen replaces the ambiguous
  question-mark control with one text link and a larger modal that leads with what to include and why,
  followed by exactly three examples. Targeted analyzer/route tests and desktop browser review pass.

- D045 endpoint, bounds, and candidate handoff: semantic intake now freezes Unity, Unreal, Godot, or
  a described Other endpoint and tight final-pose X/Y/Z bounds. Uniform scaling remains the only
  supported scale mutation. Source and candidate visual sensing now records isolated renders plus a
  shared-scale comparison; local Blender evidence derives camera clipping from asset bounds, while
  Blender remains excluded from the hosted runtime. The rejected 1 cm Computer Chip candidate is
  visible in its isolated render, retains all deterministic preservation passes, and remains
  downloadable before human acceptance as `computer-chip-candidate.glb`; its topology warning and
  rejected verification state are preserved.

- D044 capabilities and yaw: a brain-icon **What it does** page reduces the worker-facing scope to
  import, appearance, and shipping practicality, with one sentence and three groups. Standardized
  visual evidence now carries a versioned glTF source-axis contract: +Y up, +Z forward, and -X
  right; front/right/back/left camera positions are +Z/-X/-Z/+X. Prompt version 4 requires the agent
  to infer front from semantic cues across all four views, while deterministic registration rejects
  a Y-axis yaw decision that omits any labeled view. Ambiguous or symmetric fronts remain unchanged.
  Browser review at the default viewport and 390 × 844 confirms one page title, exactly three
  capability groups, no horizontal overflow, and no console warnings.

- D043 semantic assembly and mesh health: the intake agent now freezes an expected semantic piece
  count and evidence, defaulting to one unless the description clearly names a pair or set. The UI
  no longer couples assembly intent to a redundant GLB-validity message. Deterministic triangle
  diagnostics expose non-manifold and inconsistently wound edges, edge-connected face components,
  unused/coincident positions, vertex reuse, and FIFO-16 ACMR. Objective defects and narrow
  performance risks are report-only; ambiguous topology facts remain evidence for agent judgment,
  and no geometry rewrite or optimization action was added. Textareas submit on Ctrl+Enter while
  plain Enter remains a line break. Comparison fits now interpolate, the banana twirls in and melts
  out with reduced-motion support, and public GLB/ZIP attachments use the agent-assigned asset name.
- D042 upload-first hierarchy: the authoritative public rail is now **Assets → Upload → Describe →
  Shepherd**, and `/` redirects to its seven-slot gallery. A GLB must pass bounded container
  validation and objective preflight before the separate description screen. Target agreement and
  inspection are one Shepherd stage. Start screens have one global title plus at most one agent
  sentence; route tests reject subordinate heading stacks. The historical form-led deep intake now
  has one sentence, one upload control, and one collapsed rules disclosure instead of its nested
  substeps and nine title-like texts. Refusal removes the temporary staged GLB; replacement remains
  destructive only after the new durable workspace succeeds.
- D041 approval simplification: approval has one title,
  one six-row checklist, one exact three-group change list, and Reject/Approve. Attention rows are
  color-highlighted and their icons explain the condition on hover or keyboard focus. The duplicate
  result table, completed count, context bar, hidden plan details, and recorded-evidence question are
  removed. Live browser review of Polar Robot Puppy shows the exact 0.463 m → 1.500 m scale change
  and both automatic name mappings before approval.
- D040 named-asset workspace: the first intake turn now assigns a concise asset name used in the
  gallery, page title, and workspace context. `/workspace` shows up to seven source previews that
  resume the exact durable phase. An eighth upload requires an explicit replacement choice. Each
  `workspace_id` continues to own its existing `strands_state` session directory. The completion
  view is reduced to one agent-authored sentence; **Job details** opens the full structured contract
  on demand instead of occupying a permanent right column. Live browser review rendered all seven
  GLB previews, resumed a pending approval, exercised the modal, and confirmed the same-URL Yes →
  download transition.
- D039 hosted handoff: **Shepherd this asset** replaces the sensor-centric entry label. The
  conversation route now reuses the six-row structured inspection checklist and its checking-to-
  result replay instead of skipping directly from target confirmation to approval or completion.
  **Yes** persists acceptance through a progressively enhanced POST and changes the existing panel
  in place to **Ready to download**, with a direct fixed-GLB action and secondary evidence package;
  the redirect fallback remains. Live desktop and 390 x 844 checks confirmed an unchanged URL, no
  horizontal overflow, and no browser warnings or errors.
- D038 bounded conversation loop: form-led and durable hosted results now ask **Did we get it
  right?** Yes records durable acceptance; No opens one 1,000-character feedback field and begins a
  fresh agent turn. There is no hard-coded second attempt. The per-job limit is frozen from
  `ASSET_SHEPHERD_MAX_TURNS` (default 5; range 1–50). Completed outputs, assessments, and source/
  candidate renders move to `turns/turn-NNN/`; `conversation.json`, runtime state, hosted events,
  and current packaged provenance link the ordered turns. A three-turn regression proves the
  candidate/source transition, contiguous provenance, and remaining-limit calculation. Restart
  reconstruction restores the exact current GLB and frozen limit.
- D038 live continuation: the hosted OpenAI Responses workspace completed turn 0 on
  `clean_robot.glb`, accepted **No** plus feedback, archived the complete turn-0 output and four
  source renders, promoted the verified candidate to turn 1, and completed a fresh agent inspection
  and package. Turn-1 provenance records `conversation_turn_index: 1` and one prior turn with its
  source/output hashes, assessment/plan IDs, verification state, result-ZIP hash, and continuation
  feedback. Desktop and 390 x 844 browser checks expose one compact Yes/No review, reveal one
  feedback field only after No, have no horizontal overflow, and emit no browser warning or error.
- `docs/AGENT_LOOP_FLOW.md` diagrams intake → observe → assess → preview → approve → mutate →
  re-observe → verify → user feedback, including both loops, required resources, agent-visible
  tools, exact mutation boundary, durable artifacts, and stop/usage conditions.
- D037 live first-action loop: OpenAI Responses with `gpt-5.6-luna`/xhigh inspected the generated
  standing-robot fixture, requested source renders, identified source Y as semantic height, left
  rotation at zero, and requested scale, grounding, and index-preserving names. After approval it
  requested four candidate renders, recorded a 0.99-confidence source/candidate comparison, then
  independently verified and packaged `PASSED_WITH_REMAINING_WARNINGS`. Packaged provenance records
  planning tool call `call_nMY8tRPv1OATd9D2ZdQGTr2Y`, reassessment tool call
  `call_dKE85X4neVQgtd12pwNQxoPd`, both typed assessments, the approval, exact actions, and the
  `AGENT_VISUAL_REASSESSMENT` verification check. The seven-file ZIP contract remains unchanged.
- Long-bodied quadruped regression: a fresh browser run on source hash `fa757b02e150…` measured
  `0.471 × 0.463 × 0.998 m`, cited all four source views, identified Y as the 0.463 m semantic
  height and Z as body length, and produced a pure 7.5611814× scale preview for the confirmed 3.5 m
  target. Rotation is null/zero and grounding is false. The visible decision says **Normalize
  physical scale**, **Before height 0.46 m**, and **After height 3.50 m**.
- Agent-mode verification now checks exact approved preview bounds rather than dominant-axis policy
  heuristics, never invokes the legacy second planner, and requires a recorded visual candidate
  reassessment after executed actions. Agent assessment and candidate reassessment schemas are
  public; both are embedded in `provenance.json` with their initiating Strands tool-call IDs.
- Architecture diagnosis: the grasshopper-sized quadruped source measured
  `0.471 × 0.463 × 0.998 m` and was already grounded with minimum Y exactly `0`. The inspector
  nevertheless emitted `ORIENTATION_NOT_Y_UP` solely because Z was the longest extent, the planner
  rotated Z to Y, and verification passed by checking that same longest extent was now Y. Luna had
  inferred only `RIG_READY_CHARACTER` and a 5 cm proposal; `agent_result.json` identifies the repair
  runtime as `asset-shepherd-scripted-v1`. No workflow model viewed the source or comparison renders.
- D036 corrects the authority model. `docs/AGENT_ORCHESTRATED_WORKFLOW.md` now documents the complete
  understand → sense → assess → choose disposition → preview action → approve → execute → re-observe
  → verify → package loop. The agent chooses sensors and repairs; deterministic tools return facts,
  calculate exact consequences, enforce constraints, mutate only on an agent call, and prove
  invariants. `docs/AGENT_OPERATING_CONTRACT.md` now defines the corresponding model behavior and
  live acceptance cases.
- Contract version 1.5 explicitly deprecates dominant-extent semantic inference, removes
  deterministic variable planning from the target architecture, makes standardized renders eligible
  sensing evidence, and adds the D036 gate to M9. D037 implements the first action/reassessment
  slice; the remaining gate is still tracked explicitly.
- Comparison-viewer recovery: the pinned `model-viewer` extension requires plain numeric
  `extra-model` offsets and enters a bad camera state when given the former unbounded
  `min-camera-orbit`/`max-camera-orbit` values. Both attributes are removed, initial and dynamic
  offsets are unitless, and the one shared WebGL scene now visibly renders source, repaired, and
  optional banana GLBs. Browser acceptance exercised Both/Before/After fits, metric axes, banana,
  desktop, and 390 × 844 layouts with no warning or error.
- Approval presentation now asks one compact question and immediately lists the exact physical and
  automatic display-name changes before Reject/Approve. The redundant source-file reassurance,
  duplicate metric tiles, hidden component disclosure, second checklist table, and recorded-evidence
  selector are removed.
- Agent operating contract: prompt version 2 now defines the user's goal, evidence and authorization
  boundaries, concise technical-art voice, structured-control versus free-text explanation split,
  bounded tool workflow, stop conditions, prompt-injection handling, on-topic behavior, and private
  content limits. The confirmed target and complete frozen policy are appended as delimited JSON job
  data. Tool descriptions now state prerequisites, important returns, and failure behavior. The
  interim Luna intake shares the same private topic/content boundary. New `agent_result.json` records
  use prompt version 2 while version-1 records remain valid. D034 and focused zero-network tests cover
  the contract; representative live-model conversational evaluation remains open.
- Derived normalization postconditions: grounding is now calculated from the bounds produced by
  the proposed scale-and-orientation matrix. A grounded Z-up regression proves the grouped plan
  includes scale, orientation, and newly required grounding; the repaired asset is Y-up, 3.5 m
  tall, grounded at Y=0, and produces an empty second plan.
- Exact failure reproduction: the persisted elephant-scale quadruped originally passed 30
  preservation/readiness checks but failed `SECOND_PLAN_EMPTY` because its rotated candidate
  extended to -1.75 m on Y. Re-running that exact source and frozen profile with the corrected
  planner completes `PASSED_PROJECT_READY`, passes grounding within tolerance, and leaves no
  second-plan candidate.
- Failed-result presentation: verification failure no longer masquerades as inspection-only or a
  successful package. The workspace shows what passed, the exact post-repair finding and failed
  assertion, and the fresh-approval boundary. The ZIP is labeled diagnostics. The rejected GLB is
  view-only and explicitly marked **candidate not ready** in the shared before/candidate viewer;
  fit modes, HUD targets, metric axes, and banana remain available for diagnosis.
- Bounded agent correction: Strands still orchestrates the typed deterministic tools, while Python
  owns measurement, planning, mutation, verification, and packaging. The former same-matrix retry
  is replaced by one fresh deterministic reinspection and plan derivation. It does not mutate the
  candidate or reuse prior approval; a newly proposed physical correction requires a new approval
  turn and versioned provenance before execution.
- Provider-neutral conversation state: Luna currently uses the Responses API for one
  non-persistent structured intake call only; it is not the full workflow conversation. Durable
  coherence lives in the Job Contract, artifacts, minimized events, exact approval state, and
  Strands snapshots. Both scripted and Bedrock agent factories now accept the same required
  session ID plus isolated storage contract, so a provider swap can retain state across turns and
  restarts.
- Spatial repair comparison: completed jobs with executed repairs now load source and candidate in
  one locally served 3D scene at their real relative scales. One camera supplies orbit, pan, zoom,
  and Both/Before/After fit modes. Projected AABB corners drive minimal HUD target boxes, labels,
  and leader lines on every camera change; a model below 18% of its counterpart's longest dimension
  receives an explicit **model here** callout. Optional metric axes use five 1/2/5-spaced meter
  ticks for the selected fit bounds. A toggleable generated banana measures approximately 20 cm
  along its curve. The unchanged Apache-licensed `<model-viewer>` 4.3.1 distribution is now local,
  eliminating the runtime CDN dependency. D031 route and browser evidence covers the 182-meter
  source versus 1.8-meter result, focused fit, meter-axis retargeting, and banana overlay.
- User-oriented help: **How it works** now contains three actions only—describe and upload,
  review what was found, and download the result—followed by one start action. Public release
  numbers, implementation scope inventory, internal tool/provenance terms, and generic caveats are
  removed. Active-rule and finding copy also describe the user-visible fact rather than the
  prototype version; durable versioned policy and artifact metadata are unchanged. D030 route and
  browser evidence covers the exact three-step budget, desktop/mobile layout, and removed terms.
- Simplified inspection review: the former three-column evidence dashboard is replaced by one
  progressive six-check log, one structured summary with at most three attention groups, and one
  **Do these issues look fixable?** acknowledgement before Decide. Complete measurements,
  expectations, findings, rule provenance, plan candidates, stages, preview, and frozen policy are
  retained in a closed 48-row **More details** table. The Inspect view no longer repeats the target
  story, a second workflow rail, or public implementation-boundary copy. Direct Decide navigation
  and submission remain gated until acknowledgement.
- Upload and intake boundary: both upload surfaces share **Choose or drop your GLB** behavior.
  Click-to-choose remains functional; Explorer drop accepts exactly one `.glb`, updates the visible
  filename, and reports invalid drops in place. A structured intake decline stores no description or
  GLB and renders only a concise response without policy commentary.
- D029 browser evidence: the broken fixture replay visibly transitions from **Checking …** rows to
  pass/attention markers. At 1366 × 900 the summary and fixability question share the working view;
  at 390 × 844 the three areas remain ordered with no page overflow, and opened tabular detail
  scrolls inside its own container. Browser console warnings and errors are empty.
- Tests: `uv run pytest` — 128 passed and the opt-in live-provider test skipped. D019–D044 acceptance
  covers objective preflight, derived/custom policy validation, narrowed goals, clean no-mutation
  control, application/runtime restart at approval, chat non-authorization, duplicate decision
  replay, verification, and exact ZIP output.
- Check authority: every finding and verification assertion now identifies frozen project policy,
  universal invariant, objective source diagnostic, or external-consumer evidence. Policy findings
  cite exact parameter values and `CONFIRMED_INTENT`, `DERIVED_INTENT`, `FAMILY_DEFAULT`, or
  `USER_OVERRIDE`; the earlier target-intake artifact separately preserves whether a proposal came
  from model inference, explicit user text, or user clarification. Model conclusions cannot waive
  validity, authorization, source-preservation, or verification invariants.
- Strengthened inspection: direct accessor analysis covers cardinality, finite data, unit normals,
  tangent handedness, index ranges, and degenerate triangles. Active-scene/resource diagnostics
  cover empty and unreachable nodes, unused resources, apparent duplicate materials/textures, root
  origins, and a ground-center reference. Newly exposed unsupported domains remain report-only;
  malformed glTF-validity conditions block repair.
- Strengthened verification: accessors, buffer views/buffers, materials, textures, images,
  samplers, animations, skins, cameras, primitives, original node references, extensions/extras,
  and the complete binary payload must remain semantically unchanged. A deliberately parseable
  material mutation fails the universal preservation gate.
- Official validation: the pinned Khronos glTF Validator 2.0.0-dev.3.10 reports zero errors for the
  clean fixture and two `ACCESSOR_MIN_MISMATCH` errors for each untouched Tripo asset. The
  strengthened Shader Lantern run added no errors, passed verification, and explicitly retained the
  source errors plus its generated-tangent warning instead of claiming zero-error conformance.
- Render evidence: the typed four-view comparison reproduces maximum raw-versus-Shepherd MAE of
  0.081863/255 and Shepherd-versus-Blender-re-export MAE of 0.000334/255. The tool reports numeric
  external evidence only and does not replace human appearance adjudication.
- Semantic target intake: ordinary intake begins with one description. The authorized interim
  OpenAI Luna/xhigh provider proposes supported use and plausible semantic height through strict
  structured output; server validation and the 0.8 confidence gate ask only genuinely unresolved
  fields. The user can adjust and must confirm once. Both paths retain provider/model/evidence in
  `target_intake.json`; hosted adjustments survive restart and are exactly once. Mock transport
  covers the paid request contract; the live probe did not run because `OPENAI_API_KEY` was absent.
- Expectation-led intake and inspection: intended use is now visibly context and a support-boundary
  check, not a selectable preset. Confirmation and clarification contain no target-use dropdown;
  corrections are natural-language reinterpretations. The UI lists target-specific assumptions
  separately from universal invariants, then presents deterministic GLB observations and the
  bounded action plan. The intake agent records a semantic piece-count expectation while inspection
  keeps roots/nodes/meshes/primitives as separate structural facts; blocked jobs direct users back
  to the creation/export tool with recorded reasons.
- Asset-in-hand entry language: both entry points now use one short instruction: describe the model
  you are working on. Use and scale guidance stays in the example inside the full-width input. The
  primary surface contains no implementation notes, workflow comparison links, or repeated
  explanatory sentence, and fingerprinted static URLs prevent stale layout CSS after an update.
- Local key handling: two one-line PowerShell entry points save the key through a hidden prompt as
  Windows current-user protected ciphertext outside the repository, then unlock it only around the
  web command and restore process state on exit. Windows PowerShell 5.1 parser, DPAPI round-trip,
  real server startup/shutdown, and static security acceptance pass; the scripts never contain or
  echo a key.
- Target confirmation presentation: the proposal uses the wider workspace, a restrained headline,
  and human-readable metric units. Six assumptions and five invariants are compressed into three
  collapsed groups—Purpose, Scale and pose, and Structure—with no more than three facts per expanded group. The only decision is whether
  the agent got it right; its controls are simply **Yes** and **No**. **No** reveals one prefilled
  description for another attempt, using the same 16-pixel regular-weight field styling as entry
  and clarification. A shared workflow-stage renderer, description-field renderer, and
  confirmation-decision renderer now own those repeated display areas across the form-led and
  hosted routes; acceptance rejects duplicate textarea or decision markup outside that component.
  Full-page browser comparison at 1366 × 768 and 390 × 844 confirms identical panel bounds,
  heading typography/position, and active description-field geometry and styling; mobile has no
  horizontal overflow, hosted entry uses the shared field, browser diagnostics are empty, and
  stable scrollbar space prevents width shifts between steps.
- Shared feedback: `/feedback` accepts context from any workflow surface, offers four bounded
  reasons and an optional 1,000-character note, and records a local atomic JSON artifact without an
  external service. Confirmation links include their intent or workspace reference and return path.
- Lint: `uv run ruff check .` and `uv run ruff format --check .` — passed.
- Type checking: `uv run pyright` — 0 errors, 0 warnings, 0 informations.
- Local-consumer evidence: Blender 5.1.2 imported and re-exported the clean fixture with its source
  hash unchanged; Unreal 5.8 generated the isolated comparison map and imported three isolated arms
  with 15 static meshes and 4 materials each.
- Patchling evidence: raw SHA-256 `dc2f03ae8ed368f46c2a4ac9e2ebb71f23e980b0c9e6913c685d011e273f418d`;
  26,135 vertices; 18,727 triangles; one packed 4096² base-color image; 0.998 m height; no rig,
  animation, morph, negative scale, or grounding issue. Name-only repair verifies project-ready.
- Blender imports Patchling raw and repaired outputs with identical bounds, geometry, material, and
  packed-image counts and no missing image.
- Provenance registration passed with identical before/after raw hashes. The user confirmed paid
  Tripo commercial rights; Smart Mesh P1.0/Fast, 25k quad target, workspace item ID, and the GLB/4K
  export panel values are recorded.
- Patchling is accepted as the visual hero and preservation case. Its one-material limitation is
  disclosed and is not treated as an in-scope repair; D005 assigns richer PBR coverage to RW2.
- Patchling's rights-confirmed 4.86 MB raw GLB is the first tracked real-world demo input. D007 keeps
  generated results ignored and preserves the registered SHA-256 as the reproducibility anchor.
- The one-batch Shader Lantern card freezes the exact contracted prompt, 3-candidate request,
  untouched GLB/4K export settings, destination path, and transparency/emissive selection criteria.
- Intent-first web acceptance: invalid descriptions, target uses, and heights fail before job
  creation; policy and upload remain unavailable until explicit agreement; non-static intent shows
  the rigging/skinning/animation boundary; former role routes redirect to the new entry point.
- Frozen intent evidence: each agreed story records an opaque ID, exact description and target,
  timestamp, schema version, and canonical SHA-256 in job `intent.json` and packaged provenance.
  Canonical reproduction passes and tampering fails closed. A changed intent creates a new job.
- Target-state derivation: the user supplies desired height once, not a scale factor or baseline.
  D021 resolves one versioned policy family into a validated job profile. Height comes from the
  confirmed story; bounded height/ground tolerances scale with intended height; explicit
  standing/hanging/hovering language may set grounding; and unspecified rules retain family
  defaults. Advanced values remain schema-validated and changing intent or any rule creates a
  separate inspection/job.
- Existing web workflow acceptance remains: broken-fixture refresh/approve/resume/download; clean
  no-approval completion twice from independent app starts; invalid GLB rejection; unsupported
  inspection-only packaging; exact ZIP audit; source preservation; trusted family baseline; 50 MB
  and GLB magic boundaries; finding-level rule provenance.
- Single-step evidence: the authoritative left pane orients **Assets → Upload → Describe →
  Shepherd**. Agreement, inspection, decision, verification, and continuation stay inside Shepherd.
  The internal M8 harness remains covered without being the public entry. Every server-rendered
  state retains one `data-focus-area`.
- Workflow help: a large persistent `?` action sits immediately below **New asset** in both rail
  variants and opens `/how-it-works`. The page uses one agent sentence, three concise actions, and a
  start action without changing the workflow. Browser
  acceptance at the default viewport and 390 × 844 confirms action order, active state, one focus
  area, no horizontal overflow, and no console warning or error.
- Browser review at 1440 × 900 confirms that Describe, confirmation, and agreed intake use the full
  workspace without horizontal overflow. The full agreed story appears at confirmation and becomes
  a collapsed disclosure during intake so policy controls stay near the fold. At 390 × 844 the left
  workflow rail remains visible, content uses one column, horizontal overflow is absent, and browser
  diagnostics contain no warnings or errors.
- D027–D029 browser review confirms the three-group confirmation, simplified inspection, and shared feedback page at the
  default desktop viewport and 390 × 844. The compact document width is 375 pixels within the
  390-pixel viewport, all decisions and the feedback link remain visible, navigation starts at the
  top, and browser diagnostics contain no warnings or errors.
- Versioned policy intake remains intact: historical repository profiles stay byte-for-byte
  immutable for CLI and evidence reproduction, while new conversational jobs use the immutable
  `unreal-static-game-asset-family-v1` family. `Review all active rules` and `Why these rules?`
  expose the agent proposal progressively; `Adjust supported rules` exposes only enforced
  target-state and report-only budget fields. Frozen/family IDs, explicit differences, per-rule
  sources, version, canonical hash, and finding rule citations remain preserved.
- Web design handoff: `docs/WEB_DESIGN_AND_FLOW.md` records the intent-first information
  architecture, target-story contract, policy derivation, single-step workflow, Bedrock boundary,
  evidence, and limitations. D018 supersedes the primary audience-selector modality while retaining
  the established layout, disclosure, authorization, and deterministic invariant decisions.
- Product inflection review: `docs/INFLECTION_POINT.md` is the single current-versus-envisioned
  handoff. It preserves the existing form-led product as the executable baseline, defines the
  proposed persistent Bedrock/Strands asset conversation, fixes the authority boundary, surfaces ten
  pre-M9 decisions, and proposes a staged transition. ChatGPT Pro completed the requested review and
  recommended a conversation-led, contract-anchored workspace rather than a chat-only product. The
  recorded outcome calls for objective preflight before target confirmation, a visible structured
  Job Contract, derived frozen policy for ordinary users, exact non-chat authorization, durable
  resume, structured provenance, and the unchanged repair pipeline. The direction is accepted in
  D019. Contract version 1.4 now controls objective preflight, visible Job Contract, semantic target
  intake, derived frozen policies, exact structured authorization, durable resume, and minimized
  hosted conversation provenance without authorizing AWS work or additional repair domains.
- D020–D023 local hosted reference: `/workspace` presents one conversation beside a persistent Job
  Contract. Profile-free `PreflightResult` records source identity, structure, bounds, transforms,
  counts, eligibility, and declared material metadata before any policy finding or plan exists.
  Target confirmation separates original intent, requested use, supported job goal, support status,
  and external handoff; resolves the one trusted family from confirmed intent; validates supported
  advanced overrides; and freezes policy identity, family, explicit differences, rule sources,
  version, and canonical hash.
- Durable-resume evidence: private atomic workspace state, structured event/tool ledger, command
  idempotency records, retention/deletion status, deterministic runtime state, and Strands native
  snapshots reconstruct the exact pending interrupt in a new store and a new FastAPI application.
  Replaying the same decision command leaves repaired GLB and result ZIP bytes unchanged. Chat
  evidence questions cannot clear the interrupt.
- Rendered browser acceptance: start, preflight, approval, and completion retain two primary work
  areas (conversation and Job Contract); policy/finding detail stays collapsed; source and candidate
  model previews render after verification; browser diagnostics contain no warnings or errors. The
  Chrome extension needs its optional file-URL permission for browser-driven fixture selection,
  while server upload and route acceptance pass independently.
- D021 browser acceptance: a 1.2 m hanging-lantern story renders one concise agent-resolved proposal,
  correctly removes ground contact, keeps complete rules/reasons/advanced values collapsed, shows
  confirmed height without a second input, prefills bounded advanced values, and advances to upload
  with no named baseline, raw transform, browser warning, or error.
- D022 browser acceptance: initial intake renders only the description; a static-lantern description
  without size renders only the height question; the 1.2 m answer advances to an exact
  confirmation. Desktop and compact views keep one focus area, no horizontal overflow, and no
  browser warning or error.
- D023 browser acceptance: the entry screen contains one question, one text area, one disclosure,
  and one action. The low-confidence offline fallback for “a mountain of goop” renders one concise
  question with only the two missing controls; a complete target renders one large proposal, one
  confirmation action, and collapsed adjustment. At the inspected 2844-pixel viewport, content has
  no horizontal overflow. Semantic proposal routing is covered with an injected model analyzer.
- Distribution audit: `uv build --wheel` succeeded with target-intake, intent, and policy-resolution
  modules, canonical policy-family JSON, clarification/confirmation/intake templates, workflow rail,
  CSS, JavaScript, favicon, and existing deterministic runtime assets included in the wheel. The
  checked-in public target-intake, intent, and provenance schemas remain repository contract
  artifacts alongside the other exported schemas.
- Shader Lantern evidence: raw SHA-256
  `be2c9cab8d4e51f7a948c7c54db7a10c932f24faf69bc3166ff724ccc00c49b9`; 77,545 vertices;
  101,564 triangles; one material; three readable embedded 4096² base-color,
  roughness/metallic, and normal images; 99.908905 m represented height; grounded and Y-up; no rig,
  animation, morph target, negative scale, or non-uniform scale.
- The user approved Shader Lantern's selected Tripo design, intended 1.2-meter height, and exact
  reversible `normalize-root-v1` transform. The two safe display-name repairs and
  `0.0120109414×` uniform root scale executed; independent verification passed with a second empty
  plan and only `TRIANGLE_BUDGET_EXCEEDED` unresolved.
- Shader Lantern's repaired SHA-256 is
  `718722d6203dd0f0d62f86f42f0999e0d44c168f6f29767eee204d7d5631eebd`. Vertex, triangle,
  material, and texture counts remain 77,545, 101,564, 1, and 3. The result ZIP passed CRC and exact
  seven-artifact byte-for-byte audit.
- Blender 5.1.2 imports raw and repaired files with matching geometry/resources and no missing
  images, measures the repaired candidate at 1.2 meters, and re-exports it successfully. Four-view
  rendered MAE is 0.055–0.082/255; the re-export control differs from the delivered candidate by
  0.00028–0.00033/255 MAE.
- Unreal 5.8 imports raw, repaired, and Blender-control arms with one mesh, one material, and three
  textures each, zero errors, and the same non-fatal `FB_ngon_encoding` warning on raw/repaired.
  The visual pass preserves silhouette, material coverage, textures, colors, normals, opacity, and
  non-emissive behavior. The source GLB is opaque/non-emissive, so preview-only glass/glow cannot be
  claimed as exported content.
- Generated fixture evidence stays below ignored `build/validation/`; only reproducible scripts,
  schemas, templates, and typed records are committed.

## Blockers

RW2 requires untouched Debug Beetle and Cloudforge Workbench exports. The least-privilege
`asset-shepherd` AWS runtime profile, exact Kimi resource access, `us-east-1`, budget alert, and live
8/8 Kimi gate are confirmed. Luna remains unavailable behind its account agreement but no longer
blocks the recommended Kimi path. The public ECS/SQS/Lambda/AgentCore path now passes one clean
acceptance-through-download run, forced web-task replacement, and immutable Guardrail acceptance.
M9 still requires a Step 7 multi-user access choice and the complete Step 8 remote case matrix.
The submission also remains
blocked on the public-repository, free judge-access, video, disclosure, release-scan, and
entrant-attestation gates in
`docs/CONTEST_COMPLIANCE_PLAN.md`. A human-cleaned reference and manual-time record remain required
for the full RW4 comparison gate.

## Next action

Deploy D111 and verify cookie-free denial before inviting any additional demo users. Complete the
owner's Cognito sign-in/download acceptance. Invited users share the existing gallery; per-user
isolation and external OpenAI/Meta key enablement remain separate, uncompleted work.
Choose and implement the free judge-access identity boundary before the complete Step 8 browser
matrix. Alarm notification acceptance is complete. Do not run injection-attempt tests.
Preserve the current mutation scope, exact authorization, durability, and invariant checks; do not
restore deterministic target-dependent planning or create a second conversational authority.

RW2 registration resumes when the user supplies Debug Beetle. Paid Bedrock invocation is limited to
the bounded runbook matrix; broader AWS resource creation still follows its explicit gates.
Local OpenAI validation uses only the explicitly configured interim provider.
