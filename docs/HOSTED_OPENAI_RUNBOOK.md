# Hosted OpenAI Luna comparator

D112 enables an explicitly selected OpenAI API provider in the existing AWS-hosted application.
It does not make an OpenAI API call a Bedrock invocation. ECS owns intake, AgentCore owns Strands
workflow execution, and both call OpenAI over HTTPS when that workspace selects `gpt-5.6-luna`.
Kimi workspaces keep Bedrock Converse. No existing workspace is migrated and no silent fallback is
introduced. Meta and Google are not enabled by this change.

D125 (2026-09-07) makes the enabled Luna xhigh option the default and recommended selection
for new uploads. Both the allowlist and deployment-owned secret reference remain required;
model choice display does not fetch the secret. Existing workspaces retain their chosen model.

## Access evidence

On 2026-09-05, the renewed administrator login reached Bedrock Runtime Responses at `us-east-1`
using `us.openai.gpt-5.6-luna`, xhigh, one bounded request, and SDK retries disabled. It returned
403 `access_denied`: `openai.gpt-5.6-luna is not available for this account.` This is a real invocation
denial, not merely a catalog state or an expired CLI login. No additional Bedrock model attempts
were made after that denial.

The existing Windows DPAPI-protected OpenAI key was published through an anonymous process pipe
to `asset-shepherd/contest/openai`. A small OpenAI Responses/xhigh call using that AWS-stored key
completed in 2.91 seconds with 11 input and 5 output tokens. This initial check ran on the developer
computer, not in AgentCore; it proves key/model access only. Cloud acceptance is recorded separately
in `PROJECT_STATUS.md` after deployment.

## Secret boundary

- `scripts/Publish-OpenAISecret.ps1` creates the provider secret from the current Windows user's
  protected key. It refuses to overwrite an existing secret. It never places plaintext in a file,
  command argument, image build, model prompt, source tree, or terminal output. Plaintext necessarily
  exists transiently in process memory and the anonymous local pipe. Secrets Manager encrypts stored
  values and transport uses TLS; this does not prevent authorized administrators/runtime code from
  retrieving them.
- Store JSON with the single field `api_key`. Keep this secret distinct from the Cognito session
  signer. Obtain its ARN with `describe-secret`, never print `get-secret-value` during setup.
- Web and AgentCore CloudFormation each take an optional `OpenAISecretArn`. When present, only their
  respective backend roles receive `GetSecretValue` for that exact ARN. The browser, Lambda
  dispatcher, and CodeBuild roles receive no new secret permission. No browser-supplied endpoint,
  secret ARN, provider key, or provider string is accepted.
- The model factory retrieves the secret only when constructing an explicitly allowlisted Luna
  client. It is not written to `os.environ`, durable workspace metadata, session configuration,
  telemetry, or public model choices. Each factory construction fetches the current secret version;
  existing in-flight clients keep their old key until replaced. Rotate with a new Secrets Manager
  version and replace running clients/tasks before revoking the old provider key.
- Public errors omit credential values and SDK response bodies. Intake HTTP failures log only the
  provider and HTTP status. During this review we found the Docker web command bypassed the prior
  CLI-only access-log setting; the container command now explicitly uses `--no-access-log` so OAuth
  callback codes are not captured in Uvicorn access logs. ALB access logging remains disabled.

## Enablement and testing

1. Validate the secret exists without retrieving its value into terminal output.
2. Pass its exact ARN to both runtime/web stacks and publish both tested images. Deploy the runtime
   first, then the web selector, so a new Luna workspace never reaches an old Bedrock-only runtime.
3. `gpt-5.6-luna` is enabled only with both the explicit allowlist entry and secret reference.
   The UI says **Luna xhigh — OpenAI API** and explains separate OpenAI billing. Both intake and
   workflow reasoning are pinned to xhigh. Existing Bedrock workspaces retain their original model.
4. Confirm a bounded saved-target probe from AgentCore reaches a real approval interrupt without
   mutation. Keep its source/target, run duration, and token ledger; never automatically approve it.
5. Recheck anonymous route denial after the web rollout. Have the owner select Luna on a new upload,
   confirm the proposed target, and explicitly approve any requested repair when testing the full
   browser path. A successful proposal is not evidence of a completed repaired output.

OpenAI tokens are billed to the OpenAI API account, not against AWS credits. AWS still bills hosting,
storage, Secrets Manager, and AgentCore. Cognito login and mutation authorization remain unchanged.
Per D107, external OpenAI uses the common application/prompt content boundary, not Bedrock's native
Guardrail. No injection-attempt tests are authorized or needed.

Rollback: remove the OpenAI choice/default from both stacks before removing its IAM grant. Existing
Luna workspaces then fail closed rather than silently changing models. Never roll web back to an
unauthenticated image. Do not delete the provider secret while active clients still require it.

Official model settings: [GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna).

## 2026-09-05 AgentCore acceptance

Both `f0fe26a-openai` images passed their CodeBuild gates. AgentCore runtime version 8 and its
DEFAULT endpoint reached READY, and its stack completed the update before the probe. IAM simulation
confirmed the runtime role's exact OpenAI-secret read permission; the real model invocation then
proved that retrieval and internet egress worked from AWS.

The probe used a new workspace, `b30b1eac4e894ef882baff23db7cd310`, with the saved Smartpad Tablet
source and confirmed target from the D110 case. The original workspace/source were not altered.
The call completed in 75.83 seconds including remote startup/state work; the Strands invocation
ledger measured 55.61 seconds and 47,230 input + 4,360 output = 51,590 total tokens. The initial
16-token connectivity request is separate. These are token counts, not dollar estimates.

Luna inspected once, rendered once, proposed once, and attempted the execution tool once. The final
call stopped at the native human-approval interrupt, before mutation. The SDK counts that interrupt
as one tool error; the workflow itself returned `ok=true`, phase `APPROVAL`, and `error=null`.
The model proposed uniform best-fit normalization, grounding, footprint-center-bottom pivot, and
missing-name cleanup. It correctly declined simplification for the 4,992-triangle normal-gameplay
asset and did not invent a yaw change when the screenshots did not establish a horizontal front.

This is a successful AWS-hosted proposal-stage test, **not** repaired-output or full browser
acceptance. No repair approval was sent. The captured source hash remained
`c4ed1944da0f21561fa15f96bbae734e9a8e92f7c90c20e506af1126ce657dea`.
Ignored local evidence: `build/validation/hosted-openai-luna-20260905-probe/`, including the hydrated
cloud result, assessment, command, and invocation ledger. A credential-marker scan of those
artifacts produced no matches. No injection-attempt tests were run.

Kimi remains the deployment default, including legacy workspaces without a persisted choice.
Select Luna explicitly for a new upload; enabling it does not change existing assets' providers.

## 2026-09-05 web deployment acceptance

Web task revision 12 (`f0fe26a-openai-web`) reached ECS SUCCESSFUL and CloudFormation
UPDATE_COMPLETE, with one healthy new task serving 100% traffic and zero old tasks. The web role's
exact-secret read simulation passes; the task environment contains the secret ARN, not the API key.
Authenticated Chrome displays the Kimi and Luna choices on upload and renders the probe's saved
proposal, approval controls, full notebook history, and interactive source preview. Nothing was
approved or submitted during these UI checks.

Fresh anonymous requests to workspace, activity, repaired-download, OpenAPI, and POST `/intents`
return 401. `/healthz` returns 200; HTML workspace navigation returns the expected login redirect.
These are deployment/access checks, not a new end-to-end repaired-output acceptance. The owner can
now select **Agent model → Luna xhigh — OpenAI API** on a new upload and run the normal workflow.
