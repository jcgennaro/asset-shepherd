# Video cards — September 11, 2026

For recording, use NARRATION.md: headings and spoken text only, without production notes.

Open index.html. Left/right arrow keys move through market, roles, toolkit, four cumulative
architecture frames, and models. All PNGs are 1920x1080. Import them directly into the editor; use identical
scale/position for architecture frames and a short dissolve (roughly 0.3 seconds).
The architecture frames are opaque cumulative cards, not transparent overlay layers.

The shared footer credits Joey Gennaro (and Codex), identifies Agents for Humans, and records
September 11, 2026 plus the package version 0.1.0 from pyproject.toml. This is the app version,
not a claim that every future deployment will have this source revision.
roles.png distinguishes intent/approval, model judgment, and typed deterministic execution.
toolkit.png lists supported operations and selected open-source credits, checked against
pyproject.toml, cli.py, models.py and the implementation. Khronos validation is optional;
Blender is the external export check, not a hosted repair dependency.

Suggested holds and narration (adjust to the recorded delivery):

- market.png — 20–25 seconds: “SlashData estimated 11.1 million game developers worldwide in
  early 2024. Our preliminary estimate is that two to five million creators work in the broader
  imported-asset workflow. Not all need help. We focus on solo developers and small teams without
  a dedicated technical artist.” The second estimate is an unvalidated user-supplied hypothesis,
  not a published count or measured demand. Do not present it as a result of SlashData research.
- architecture-1.png — 15 seconds: “ECS hosts the website. SQS and Lambda dispatch long-running
  work to AgentCore, where a Strands agent uses bounded geometry tools and rendered evidence.
  The user approves changes.”
- architecture-2.png — 10 seconds: “S3 stores models and evidence. DynamoDB tracks workflow
  progress. The browser polls for updates, so work isn't tied to one open web request.”
- architecture-3.png — 10 seconds: “Cognito handles sign-in, IAM scopes service access, and
  Secrets Manager holds the external API key. Alerts and application spending safeguards support operations.”
- architecture-4.png — 12 seconds: “The application runs on AWS. Both intake and workflow can
  call the selected provider: OpenAI Luna by default, or Kimi through Amazon Bedrock.”
- models.png — 20 seconds: “We tried Luna, Kimi, Muse and Gemini on real asset workflows.
  Luna's visual selection and multi-step results made it our current choice. We judge value by
  the finished asset, including latency, cost and retries—not just token price.”

Research: https://www.slashdata.co/post/there-are-11-1-million-game-developers-in-the-world
Verified September 11, 2026: Q1 2024 estimate includes professionals, hobbyists and students.
No creator counts are added together, and no revenue calculation is included.

Architecture source: deployed revision documented in docs/PROJECT_STATUS.md (1131bee),
infra/cloudformation templates and docs/HOSTED_OPENAI_RUNBOOK.md. This is a simplified video
diagram, not a complete infrastructure inventory. Neutral boxes are not official AWS icons.
Storage band is shared by web and runtime; arrows do not imply exclusive database ownership.

Model evidence: docs/PROJECT_STATUS.md D094–D096 and owner-reviewed Luna runs. Coverage differs
between providers; no universal performance ranking, current pricing or quantified success-rate
claim is made. Other named models received earlier screening rather than equal full evaluations.

Render with `uv run python demo-output/pitch/slides/render.py`. No model calls are made.
Keep the final video under five minutes including every title and tail.
