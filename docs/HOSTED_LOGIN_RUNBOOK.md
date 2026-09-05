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
- The web task role may retrieve only the exact session-signing secret ARN. The value is generated
  in Secrets Manager, retrieved into server memory, and never passed through CloudFormation values,
  images, browser code, model prompts, or logs. Authorized AWS administrators can retrieve it;
  encryption is not a claim that a compromised administrator/runtime cannot steal a secret.
- The `__Host-` session cookie is signed, Secure, HttpOnly, SameSite=Lax, and host-only. It contains
  only the verified subject and fixed expiry after login, not OIDC access/refresh/ID tokens or
  provider API keys. Signed cookies are tamper-resistant, not encrypted. Transient OAuth state,
  nonce, and PKCE verifier are kept in that secure cookie during login and cleared at callback.
- Sessions expire within one hour, without silently refreshing. Cognito account disabling blocks
  new login but does not immediately revoke an already-issued application cookie. Emergency global
  sign-out requires rotating the session signer and restarting all web tasks. Signing out clears
  this browser's application cookie and then signs it out of Cognito.
- All workspace, download, activity, upload, feedback, command, and OpenAPI routes require a session.
  Only static assets, login/callback/signed-out pages, and `/healthz` remain public. Authenticated
  unsafe HTTP methods require the exact configured Origin. Responses with private data and OAuth
  callbacks are `no-store`; app access logging is disabled to avoid recording authorization codes.
- Incomplete required login configuration or secret retrieval fails startup closed. Local offline
  development remains usable without Cognito when no login configuration is supplied.
- OpenAI/Meta production keys are still not configured. Their future Secrets Manager retrieval
  must remain separate from the session signer. Bedrock/Kimi remains the deployed model default.

## Deployment

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
