# Asset Shepherd

Asset Shepherd is an autonomous 3D-asset intake, inspection, repair-planning, and
verification agent for game developers.

> [!NOTE]
> This repository is an early hackathon work in progress.

## Project control

- [Project contract](docs/PROJECT_CONTRACT.md)
- [Real-world validation plan](docs/REAL_WORLD_VALIDATION_PLAN.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Decision log](docs/DECISIONS.md)
- [Web design and flow](docs/WEB_DESIGN_AND_FLOW.md)

## Real-world validation

The [validation workspace](validation/README.md) preserves immutable raw provenance, controlled
mutation ground truth, Blender evidence, and an isolated Unreal comparison harness. Patchling
Courier is the current hero and preservation case. Shader Lantern is the second rights-confirmed
real-world corpus member. Its approved workflow normalized the 12.8 MB
[raw GLB](validation/corpus/shader_lantern_01/raw/asset.glb) to the intended 1.2-meter height, made
two safe display-name repairs, independently preserved its exported geometry and PBR resources in
Blender and Unreal, and left its triangle-budget warning unresolved. Exact evidence and limitations
are in the
[Shader Lantern checkpoint](validation/corpus/shader_lantern_01/checkpoint.md).
The rights-confirmed 4.86 MB
[Patchling raw GLB](validation/corpus/patchling_01/raw/asset.glb) is the repository's first
distributable real-world demo input. Generated GLBs and ZIPs remain reproducible and untracked.

## Local web product

```powershell
uv sync
uv run asset-shepherd web
```

Open `http://127.0.0.1:8000`. The flow starts by asking what the user was trying to make, its
intended use, and its real-world height. Asset Shepherd drafts one exact target story; the user must
agree to it before rules or upload are available. The frozen, canonically hashed intent is stored
with the job and in package provenance. Changing intent starts a new inspection.

The versioned D019 reference is at `http://127.0.0.1:8000/workspace`. It starts with a short asset
description plus the untouched GLB, performs profile-free objective preflight, and then asks the
user to confirm a typed target. A persistent Job Contract shows measured source facts, the derived
frozen policy, findings, registered plan, exact decision, verification, and package state beside the
conversation. Ordinary users never choose a named scale preset. Advanced customization is limited
to fields already enforced by `ProjectProfile`; safety and repair boundaries remain fixed.

The persistent left pane shows the shared **Describe -> Agree -> Inspect -> Decide -> Download**
workflow. Intake presents **Rules -> Upload** one step at a time, and each job presents only its
current Inspect, Decide, or Download view. The default local implementation uses a zero-network
scripted provider over the real Strands loop. The `/workspace` path provides the bounded
conversation and evidence questions without a network request. A future Bedrock provider will make
the questions adaptive, but deterministic measurements, repairs, authorization, and verification
remain authoritative.

Repository profiles are immutable versioned policy presets. The web UI calls the two current
choices **Human-scale static mesh** and **Compact static mesh**; all non-height rules are currently
identical. The user's confirmed height controls the target, deriving a validated profile copy when
it differs from a preset default. Each preset keeps its concise summary and complete rule review
collapsed. An advanced **Customize a copy** control permits only supported target-state and
report-only budget overrides; safety policy and verification boundaries remain fixed. Upload
freezes the resolved policy into the new job, and provenance records its base preset, explicit
overrides, version, identifier, and canonical SHA-256. Changing rules starts a new inspection and
job.

The M8 form routes preserve jobs only while the process runs. The D019 `/workspace` path persists
structured state and the native Strands interrupt so refresh, application restart, and agent-runtime
restart resume the exact job without duplicate mutation or packaging. Local private workspace state
has a seven-day retention marker; production cleanup remains part of the AWS gate. The 3D preview
uses the pinned official `<model-viewer>` browser component; GLB files remain served from the local
Asset Shepherd origin.

## Deterministic CLI demo

```powershell
uv sync
uv run asset-shepherd run fixtures/broken_robot.glb `
  --profile profiles/unreal_indie_robot.json `
  --approvals examples/approve_normalization.json `
  --output demo-output
```

The command inspects, plans, applies policy-safe renames, consumes the explicit normalization
approval, repairs, independently verifies, and writes `demo-output/result.zip`. It does not invoke a
model or make a network request.

## Local Strands agent demo

The offline harness drives the real Strands agent loop and native interrupt/resume mechanism with a
scripted zero-network model:

```powershell
uv run asset-shepherd agent-run fixtures/broken_robot.glb `
  --profile profiles/unreal_indie_robot.json `
  --output agent-demo-output `
  --decision approve `
  --offline-scripted
```

The CLI prints the combined normalization approval card and its Strands interrupt ID before it
resumes. The deterministic seven-file ZIP remains unchanged; `agent_result.json` sits beside it and
contains the prompt version, user-facing summary, provider/model identity, token usage, tool
success/error/duration metrics, interrupt count, correction count, and final verification state.

Live model use is opt-in and has no hard-coded model ID. Copy `.env.example` into your environment,
set `ASSET_SHEPHERD_MODEL_ID` and region to values available in your account, and use the standard
`AWS_PROFILE`. The live integration test runs only when `ASSET_SHEPHERD_RUN_LIVE=1`; ordinary tests
never look up credentials or make network requests.
