# Asset Shepherd — recording copy

Draft 1 · September 7, 2026 · Target duration 4:45

Read the paragraphs only. Timings are editing targets; rehearse before recording. See
[production script and shot inventory](VIDEO_SCRIPT.md) for evidence conditions, footage,
overlays, architecture reveals, and the rejected-candidate fallback. This is the main narration,
not permission to claim verification passed without the recorded result.

## 01 · 00:00–00:12 · The hook

I asked for gaming peripherals. I got this. But for my game, I only want the headphones. Getting a convincing model is one thing. Getting the right usable asset is another.

## 02 · 00:12–00:29 · Who needs this, and how large is the audience?

SlashData estimated 11.1 million game developers worldwide in early 2024. Our starting audience is narrower: solo developers and small teams preparing 3D props without a dedicated technical artist. They need usable assets, not another complicated cleanup workflow.

## 03 · 00:29–00:49 · Why we built it

Our background is engineering and product development, not digital art. Even with AI model generation, Blender, and game engines, getting a simple static prop from concept into a game was frustrating. Open-source repair tools existed. We needed help connecting the problem to the right tool.

## 04 · 00:49–01:05 · The promise

That is Asset Shepherd, built for Agents for Humans: supported asset repairs in one place, guided by a vision-capable language model. Upload a static GLB, explain what you need, and review the proposal. The agent reasons; bounded tools do the work.

## 05 · 01:05–01:22 · Upload the real example

Here is the original Tripo export. The headphones are mixed into a scene of peripherals, with many separate geometric parts. I upload the original file and describe the outcome: keep the headphones, remove the rest.

## 06 · 01:22–01:39 · Agree on the target

I confirm the destination, intended dimensions, and how closely the asset will be viewed. These are use-case choices, not a request for me to calculate a polygon budget. The agent works against that agreed target.

## 07 · 01:39–02:01 · Make the intelligence visible

Now the agent reads measurements and standardized screenshots. The difficult question isn't “which piece is biggest?” It's “which pieces together make the headphones?” It can inspect further before proposing what to keep. That is visual judgment, grounded in measured evidence.

## 08 · 02:01–02:21 · Keep the human in control

The proposal identifies the parts to retain and remove. I can disagree or request a revision. Only my explicit approval authorizes the removal. The agent cannot quietly turn a guess—or an ordinary chat message—into permission to delete geometry.

## 09 · 02:21–02:46 · Show the result and its checks

After the change, the tools reopen and measure the candidate, and the agent reviews fresh visual evidence. Here are the headphones separated from the original scene. I inspect the earcups, headband, and small details—and read any remaining warnings rather than treating “the tool ran” as proof of success.

## 10 · 02:46–03:00 · Deliver something real

I download the result and reopen the actual exported file. This is a changed 3D asset, not advice about changing one. The original and the recorded evidence remain available for review.

## 11 · 03:00–03:20 · Tease the rest without another full demo

Component selection is one capability. Asset Shepherd can also propose scale, pose and pivot corrections, clean up display names, and offer controlled mesh simplification for the intended viewing use. It preserves the original and reports limitations instead of promising to repair every possible mesh.

## 12 · 03:20–03:32 · Architecture reveal 1: the product core

We started with the core: a Strands agent, deterministic GLB tools, and a lightweight browser renderer. The model chooses the work; the tools constrain and verify it.

## 13 · 03:32–03:44 · Architecture reveal 2: put it on AWS

We hosted the website with ECS Express and moved the workflow into Amazon Bedrock AgentCore Runtime. A queue and a small Lambda dispatcher separate long-running agent work from web requests.

## 14 · 03:44–03:56 · Architecture reveal 3: remember the work

S3 retains asset files and evidence. DynamoDB records workspace state and queued-command progress. The browser polls for updates, so the workflow does not depend on keeping one web request open.

## 15 · 03:56–04:08 · Architecture reveal 4: protect and operate it

Cognito handles sign-in. IAM limits service permissions, and Secrets Manager holds the external model key. CloudWatch, alerts, and a shared spending ledger give us visibility and cost safeguards.

## 16 · 04:08–04:20 · Architecture reveal 5: model boundary

The same orchestration supports Bedrock models, or an approved external provider. Today's default is Luna xhigh through OpenAI. The application runs on AWS; the selected model call crosses that boundary over HTTPS.

## 17 · 04:20–04:40 · Why this model?

We choose models for completed-task value: visual decisions, reliable tool use, latency, and total cost—including retries. Luna has delivered strong results in our hands-on asset tests, so it is our current default. We retain a Bedrock alternative and measure outcomes rather than picking a model by its name alone.

## 18 · 04:40–04:45 · Close on the benefit

Asset Shepherd. Less asset cleanup. More time making your game.

