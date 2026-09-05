# Asset Shepherd Cognito branding

The classic Cognito app client uses `cognito-classic.css` and `login-logo.png`.
The static logo is a browser-rendered lockup of the existing first mascot sprite frame and
the Asset Shepherd wordmark. `login-logo.html` is its editable source; no new mascot was generated
and neither the original sprite nor the application header was changed.

## Publish

From the repository root:

```powershell
uv run python scripts/publish_login_branding.py
uv run python scripts/publish_login_branding.py --apply
```

The first command previews hashes and checks the existing auth stack/domain. The second updates
only that stack's existing Cognito app-client CSS and image. It does not retrieve secrets, modify
OAuth clients, change service tiers, invite users, or deploy containers. CSS and the image must be
sent together. This app-client customization is applied through the Cognito API, not CloudFormation;
reapply after intentionally replacing the app client. Allow about one minute for propagation.

To revise the logo, render `login-logo.html` with headless Chromium at a 350×178 CSS viewport and
device scale factor 2, using a fresh temporary browser profile. The resulting PNG is 700×356 and
38,440 bytes, under Cognito's 100 KB logo limit. CSS is below its 3 KB limit. Keep the mascot static.
The source uses ordinary system typography and the existing sprite as a CSS background.

## Acceptance, 2026-09-05

- Applied client CSS version `20260905065315` and verified API readback matches both local assets.
- Inspected an actual hosted desktop login screenshot. Verified 320 px/390 px layouts and reset
  contrast with fetched hosted markup/styles in isolated, correctly sized preview frames; scripts
  were stripped and no forms were submitted. Initial CDP captures timed out and are not evidence.
- The fixed Cognito classic outer gray background/layout is unchanged; the supported card,
  wordmark, mascot, fields, labels, focus state, buttons, links, and reset text are branded.
- No password reset email, invitation, model call, authenticated workflow, or owner-browser
  attachment was performed. Common gate: 285 passed, 3 skipped; lock, Ruff, format, Pyright clean.
- Ignored screenshots: `build/validation/login-branding/`.

Reference: [AWS classic branding documentation](https://docs.aws.amazon.com/cognito/latest/developerguide/hosted-ui-classic-branding.html).
