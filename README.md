# Asset Shepherd

**Turn an unfamiliar 3D asset into something you can confidently bring into your game.**

Asset Shepherd helps game developers inspect, normalize, and cautiously repair static 3D assets.
Describe what an asset should be, review the agent's proposed changes, and download a verified
result—with the original preserved.

Built for the **Agents for Humans** hackathon, **Professional Agents** track.

## Try Asset Shepherd

[**Open the hosted testing site →**](https://as-73038a3f3e8d40819c72ccb90d068ec4.ecs.us-east-1.on.aws/workspace)

**Judges:** sign in using the shared credentials supplied in the submission's **private Devpost
testing instructions**. No individual invitation, AWS account, API key, installation, or payment
is required. If you cannot find the credentials or have trouble signing in, please contact me below.

The demo has a **shared Gallery**: other demo users can see uploaded assets and their history.
Please use nonconfidential assets that you have permission to upload.

## Why I made it

A model can look great in a preview and still be awkward to use: it might arrive the size of a
building, face the wrong direction, have an inconvenient pivot, contain disconnected fragments,
or carry far more geometry than its intended role needs.

For indie developers, inspecting and correcting these details interrupts the creative work.
I built Asset Shepherd to make that process conversational: explain the intended use, let the
agent investigate, and stay in control of changes that affect the asset.

## What it does

Asset Shepherd combines an AI agent's interpretation of **3D screenshots and measured geometry**
with bounded repair tools. It can:

- Inspect dimensions, pose, mesh structure, materials, textures, and display names.
- Propose scale, orientation, grounding, and pivot adjustments for your intended use.
- Review labeled disconnected components and propose selective removal when appropriate.
- Recommend mesh simplification for hero, normal-gameplay, or background/repeated use.
- Reopen and check repaired files, present before/after evidence, and package the result.

Consequential changes require your approval. You can reject simplification, refine a proposal,
or keep the original. If an operation cannot be verified, the app reports that limitation rather
than treating the agent's confidence as proof.

This prototype supports **static GLB assets**, not arbitrary 3D formats or a full replacement for
a modeling tool. Some findings are report-only, and preservation constraints may prevent an
optimized mesh from reaching the suggested triangle budget.

## Your first test

1. **Upload** a GLB from Gallery.
2. **Describe** what it represents and how you intend to use it. Confirm the destination engine,
   proposed dimensions, and whether it will be a hero, normal-gameplay, or background asset.
3. **Review** the agent's findings and proposed repairs, then approve only the changes you want.
4. **Compare** the candidate in the 3D viewport. Give refinement feedback if needed, or choose
   **Use this version** and download the shepherded GLB and evidence package.

Click the mascot in the top-left corner to return to Gallery. The in-app **FAQ** explains the
controls and can replay the short navigation tour. Complex assets may take several minutes.

### Need a sample?

These GLBs are included in the repository. Open a file below and use GitHub's **Download raw file**
button, or use the corresponding file from a clone:

- [Patchling — 4.9 MB](validation/corpus/patchling_01/raw/asset.glb)
- [Shader Lantern — 12.8 MB](validation/corpus/shader_lantern_01/raw/asset.glb)

For a concrete first experiment, try Shader Lantern with:

> A stylized lantern for a game, intended to be 1.2 meters tall.

Then select your target engine and viewing use. The agent's exact proposal can vary; inspect it
before approving. The [recorded Lantern case study](validation/corpus/shader_lantern_01/checkpoint.md)
documents an earlier validation run, not a guaranteed outcome for every model.

## How it works

The **Strands Agents SDK** drives the agent's inspection, tool use, approval pauses, and
reassessment. Deterministic geometry tools enforce the approved scope and independently verify
the result.

The hosted site runs on **Amazon ECS**, with the agent in **Amazon Bedrock AgentCore Runtime**.
S3 and DynamoDB preserve artifacts and workflow state; Cognito controls sign-in. The default
model for new uploads is **Luna xhigh through the OpenAI API**; **Kimi K2.5 through Amazon Bedrock**
remains selectable. Model access is provided by the demo, not by the judge.

## Learn more or get in touch

I'm the developer behind Asset Shepherd, and I'd be glad to answer questions, help with testing,
or discuss the design and its limitations.

**Questions or feedback?** [Open a GitHub issue](https://github.com/jcgennaro/asset-shepherd/issues).
Judges can also use the private contact details supplied with their testing instructions.

For a deeper look:

- [Technical setup and deployment guide](docs/TECHNICAL_GUIDE.md) — clone, local setup, providers,
  sample assets, and tests.
- [Agent workflow and safety boundaries](docs/AGENT_ORCHESTRATED_WORKFLOW.md) — what the agent,
  user, and deterministic tools each control.
- [Current project status](docs/PROJECT_STATUS.md) — validation evidence and remaining work.
- [License](LICENSE) — MIT.
