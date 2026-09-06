# Private judge testing instructions — template

This file contains no credentials. Replace the placeholders **only in Devpost's private
testing-instructions field**, never in the public README, video, repository, or screenshots.

## Text for Devpost

Open [Asset Shepherd](https://as-73038a3f3e8d40819c72ccb90d068ec4.ecs.us-east-1.on.aws/workspace).

Sign-in email: **[dedicated shared judge email]**  
Password: **[permanent judge password from the owner's password manager]**

Use these provided credentials; no registration or individual email invitation is needed.
Access is free during judging. This is an Asset Shepherd demo account, not an AWS account.

Upload a GLB and describe what it should be. Confirm the proposed destination, dimensions,
and use case. Asset Shepherd inspects the model and proposes repairs. Review the proposal
before applying it, compare the result in the 3D view, then accept and download it. You can
refine a result with feedback. Clicking the top-left mascot returns to the Gallery.

The demo uses a shared Gallery. Use non-confidential demonstration assets; other demo
users can see its assets and history. No personal provider API key or payment is required.
If a model is busy or analysis is temporarily paused, your saved work remains available.

## Owner checklist before sharing

- Open the app in a private browser window and use the emailed temporary judge password.
- Set a permanent password, complete any email verification requested by Cognito, and
  save the password in a password manager. Do not paste it into an assistant conversation.
- Sign out, then verify a fresh sign-in with the **permanent** credentials. Judges must not
  receive a first-login password-change challenge or an expired temporary password.
- Run the judge path through upload, explicit repair approval, result review, and download.
- Ensure the shared Gallery has practical room for judging and contains no confidential assets.
- Insert credentials only in the private testing field, then recheck the public submission
  for accidental credential disclosure. This template is not a submitted Devpost entry.
- Keep the account and service available through October 8, 2026; monitor the existing
  operations notifications. The $10/day model safety ceiling is an emergency control,
  not a normal shared judge quota. See `MODEL_SPENDING_RUNBOOK.md`.
