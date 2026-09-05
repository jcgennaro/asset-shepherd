# Invite-only shared-demo login

This is an access gate, not per-user workspace isolation. Every invited user can see and use the
existing shared contest gallery, including its uploaded models and paid workflow actions. Do not
invite mutually untrusted customers or store their private assets here. Add real per-user ownership
before doing that. The website login is separate from AWS console/IAM login.

## Architecture and security boundary

- `asset-shepherd-auth` owns a Cognito Lite user pool, public OAuth client, classic hosted-login
  domain, and Secrets Manager session-signing secret. Public self-registration is disabled;
  administrators create invitations. Passwords are handled by Cognito, not our app.
- The web service uses Authlib's authorization-code/OIDC implementation with S256 PKCE, browser
  state, nonce, signature, issuer, audience, and expiration verification. Redirect destinations
  are deployment-owned fixed HTTPS URLs, never arbitrary browser parameters. The OAuth client
  has no shared client secret; PKCE binds code exchange to the initiating browser session.
- For authentication, the web task role may retrieve the exact session-signing secret ARN. The value is generated
  in Secrets Manager, retrieved into server memory, and never passed through CloudFormation values,
  images, browser code, model prompts, or logs. Authorized AWS administrators can retrieve it;
  encryption is not a claim that a compromised administrator/runtime cannot steal a secret.
- The `__Host-` session cookie is signed, Secure, HttpOnly, SameSite=Lax, and host-only. It contains
  only the verified subject and fixed expiry after login, not OIDC access/refresh/ID tokens or
  provider API keys. Signed cookies are tamper-resistant, not encrypted. Transient OAuth state,
  nonce, and PKCE verifier are kept in that secure cookie during login and cleared at callback.
- Sessions expire within 24 hours of sign-in, without sliding renewal or silent refresh. The app
  cookie has a 86,400-second maximum age and a fixed deadline capped by the verified ID token;
  Cognito ID tokens last 24 hours, while unused access tokens remain at one hour. Existing cookies
  keep their original deadline: sign in again after the D119 rollout to receive the longer session.
  Cognito account disabling blocks
  new login but does not immediately revoke an already-issued application cookie. Emergency global
  sign-out requires rotating the session signer and restarting all web tasks. Signing out clears
  this browser's application cookie and then signs it out of Cognito.
- All workspace, download, activity, upload, feedback, command, and OpenAPI routes require a session.
  Only static assets, login/callback/signed-out pages, and `/healthz` remain public. Authenticated
  unsafe HTTP methods require the exact configured Origin. Responses with private data and OAuth
  callbacks are `no-store`; app access logging is disabled to avoid recording authorization codes.
- D113 uses `Referrer-Policy: same-origin` on application responses so native form POSTs retain
  their origin, with no referrer sent to other sites. `/auth/` responses retain `no-referrer` to
  protect login/callback URLs. Applying `no-referrer` globally caused ordinary Redo submissions
  to send `Origin: null` and fail the unchanged exact-origin CSRF check. Missing/null/cross-origin
  writes remain rejected; there is no exception for Redo. After deployment, reload the Gallery
  before retrying so its document receives the corrected policy.
- Incomplete required login configuration or secret retrieval fails startup closed. Local offline
  development remains usable without Cognito when no login configuration is supplied.
- D112 adds an optional OpenAI provider key in a separate Secrets Manager secret, with a separate
  exact-ARN backend read grant; see `HOSTED_OPENAI_RUNBOOK.md`. Meta remains unconfigured.
  Bedrock/Kimi remains the deployed model default. The OpenAI rollout also corrects the Docker
  command to disable access logging; the earlier CLI-only setting did not cover that command.

## Deployment

### Twenty-four-hour sign-in sessions (D119)

The user requested a 24-hour expiry after a completed collar run encountered a final-click 401.
Change both the app's `SESSION_SECONDS` and the Cognito client's `IdTokenValidity`; changing only
the cookie would still leave the callback capped at the earlier ID-token expiry. Preserve the
callback's verified-expiry minimum, cookie protections, exact-origin CSRF checks, and token-free
cookie contents. Access-token validity remains one hour; no refresh token is retained or used.
This is an absolute session lifetime, not 24 hours since the last action. A stolen application
cookie could therefore remain usable for longer; shared-demo access and revocation limits below
still apply. Do not silently extend old cookies or rotate the signer during this rollout.

Local tests use verified-claim stubs and a simulated clock, not real credentials or model calls.
They check short-token caps, the 24-hour maximum, validity after one hour, exact-boundary expiry,
no sliding renewal, cookie flags, logout, and the existing authentication/CSRF failures.

### Signed-out page and explicit command submission (D115)

`templates/signed_out.html` supplies the public branded signed-out response, including the existing
static mascot and a normal `/auth/login` link. It uses no script, provider call, or external font;
no-referrer/no-store response policies and logout/session behavior are unchanged. Desktop and
320 px preview captures are in ignored `build/validation/signed-out/`.

The paired browser fix includes the actual clicked submitter when building remote FormData. Without
it, Apply recommendations omitted required `decision=approve` and received 422 before queueing.
Tests use actual app.js with a local typed endpoint; they do not approve or retry hosted assets.
Reload the workspace after deployment before retrying a rejected action so the new script loads.

CodeBuild `asset-shepherd-contest-web:5d1e3b7e-f80d-40d3-aab6-69ec0971851a` passed and published
`f459c9376886-web-actions-web`, deployed as web task revision 14. At 100% new-task traffic, the
public signed-out page matches the checked template exactly; deployed app.js matches committed
source after line-ending normalization and includes the submitter argument. Anonymous workspace,
source-download, and OpenAPI still return 401; health returns 200. Only the image parameter changed.
Runtime/model configuration and the existing pending approval were not modified by deployment.
Final ECS/CloudFormation rollout status is recorded in `PROJECT_STATUS.md`.

### Sign-in branding (D114)

The live classic hosted login now uses the existing static mascot and Asset Shepherd wordmark,
dark application colors, mint actions, and matching password-reset styling. Branding assets and
the exact-client publication procedure live in `infra/branding/README.md`. This uses Cognito's
existing Lite/classic customization API; it does not replace authentication or change the tier.

### Native-form correction (D113, 2026-09-05)

Code commit `3aad485` fixes the application/auth response-policy split without weakening the
exact-origin gate. Common quality checks pass (285 passed, 3 skipped; Ruff, formatting, Pyright,
and lock check clean). The regression suite includes a native form POST from a fresh headless
Chromium profile against a loopback-only fixture; it uses the policy returned by the login middleware.
It neither attaches to user tabs nor contacts a model or the hosted workflow.

CodeBuild `asset-shepherd-contest-web:49fe4779-dcaa-4e32-a2b8-04e9449c6f6b` passed and published
`3aad48575c31-form-origin-web`. The web update changes only `WebImageUri`, preserving the previous
template and all other parameters. At 100% traffic, `/healthz` returns 200 with `same-origin`,
`/auth/signed-out` returns 200 with `no-referrer`, and anonymous workspace, source-download,
OpenAPI, and Redo requests return 401. No real workspace was restarted for verification.
Final rollout status is recorded in `PROJECT_STATUS.md`. Reload the Gallery before retrying:
an already-open document retains its old referrer policy even after the server is updated.

### Initial setup

1. Read the existing web stack's `WebEndpoint`; use its canonical HTTPS origin.
2. Deploy `infra/cloudformation/auth.yaml` as `asset-shepherd-auth`, passing `PublicOrigin`.
3. Read `UserPoolId`, `ClientId`, `LoginDomain`, `SessionSecretArn`, and `PublicOrigin` outputs.
   These are references, not secret values. Do not call `get-secret-value` in a terminal for setup.
4. Build a committed web image including `web_auth.py`, Authlib, and ItsDangerous. The image does
   not contain any credential or signing key. AgentCore needs no auth-image change: its existing
   private IAM boundary and fixed trusted demo actor remain unchanged.
5. Update `web-express.yaml` with the accepted image and the five login references, retaining all
   other existing deployment parameters. `ASSET_SHEPHERD_AUTH_REQUIRED=1` is mandatory there.
6. Wait for all old unauthenticated web tasks to drain. Confirm cookie-free gallery navigation
   redirects to Cognito, cookie-free data/actions return 401, and `/healthz` remains 200.
7. Invite the owner through Cognito `AdminCreateUser` with EMAIL delivery. Let Cognito generate and
   deliver the temporary password. Never echo it, commit it, or paste it into agent context.
8. The owner changes the temporary password and signs in. Verify gallery access, an authenticated
   download, a browser workflow action, and sign-out. Invite judges individually only when the
   shared-gallery access is appropriate. Do not enable self-registration to simplify judging.

In the AWS console: **Amazon Cognito → User pools → asset-shepherd-contest → Users → Create user**.
The invitation subject and HTML body identify Asset Shepherd, link to its configured public origin,
and explain the shared demo and required first-login password change. The initial generic Cognito
invitation landed in the owner's spam folder; invitees should check spam and mark the expected
message as not spam. The sender is still Cognito's default `no-reply@verificationemail.com`.
A custom sender requires an SES-verified email/domain; branding alone cannot guarantee delivery.
Use `AdminCreateUser` with `MessageAction=RESEND` for an unactivated invitation when a replacement
is needed: Cognito delivers a new temporary password and invalidates the previous one. Do not
inspect or echo either password. Refer to the newest invitation, not an old email or screenshot.
Deleting the auth stack intentionally retains the user pool and signing secret. Do not roll the
website back to a pre-auth image while treating it as private; that would reopen anonymous access.

## Validation and remaining limits

2026-09-04 EDT deployment evidence:

- Auth stack creation and branded-template update pass. The web-only CodeBuild run
  `asset-shepherd-contest-web:55731896-a5ab-49b4-9665-e2a4f8d07326` succeeds. Its image
  `70f78cd-auth-web` is deployed as web task revision 11 with `AUTH_REQUIRED=1`; ECS reports
  SUCCESSFUL, 100% production traffic, one new task, and zero old tasks; the web CloudFormation stack
  is UPDATE_COMPLETE. AgentCore remains version 7
  with Kimi; this authentication rollout invokes no models and changes no provider credentials.
- A fresh cookie-free HTTP client gets 401 for workspace, activity, repaired GLB, evidence-download,
  OpenAPI, and an empty POST to `/intents` (rejected before application execution). HTML navigation
  gets 303 to `/auth/login`, then a Cognito authorization-code/S256 PKCE redirect. The Cognito login
  page returns 200 with a password field and no public signup link. Health remains 200.
- Live login-state cookie attributes are Secure/HttpOnly/SameSite=Lax with the `__Host-` name.
  Cookie values were not printed. ALB S3 access logging is disabled; app access logging is also
  disabled in required-auth mode, avoiding authorization-code query logging. All eight project
  operational alarms are OK.
- Common gate: 277 passed, 3 skipped; lock/Ruff/format/Pyright pass. The branded invitation was
  rendered and inspected at 680px and 375px using placeholder credentials, then sent to the owner
  as a replacement invitation. No new password was retrieved or displayed.
- **Open human checkpoint:** owner changes the temporary password, enters the gallery, downloads
  an existing model, and signs out. Do not claim this authenticated end-to-end check has passed yet.

No-network tests cover anonymous route/action denial, valid/expired/tampered sessions, same-origin
write enforcement, missing OAuth state, actual Authlib PKCE generation, token-free session contents,
logout, and fail-closed configuration. These are authentication unit tests, not prompt-injection
attempts or live model tests. A human sign-in remains required to close end-to-end acceptance.

This gate does not provide per-user budgets, tenant isolation, instant per-session revocation, or
comprehensive abuse protection. A trusted invited user can still incur model charges. Existing AWS
budget/operations alerts remain necessary, and app quotas are a separate hardening step.

References: [AWS administrator-created users](https://docs.aws.amazon.com/cognito/latest/developerguide/how-to-create-user-accounts.html),
[Cognito PKCE](https://docs.aws.amazon.com/cognito/latest/developerguide/using-pkce-in-authorization-code.html),
[Secrets Manager encryption](https://docs.aws.amazon.com/secretsmanager/latest/userguide/security-encryption.html).
[Cognito token validity units and one-day maximum](https://docs.aws.amazon.com/cognito-user-identity-pools/latest/APIReference/API_TokenValidityUnitsType.html).
