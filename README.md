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

Open `http://127.0.0.1:8000`. A persistent left navigation pane keeps five presentation modes
available:

- `/stories/game-developer` asks whether the asset is ready for a game.
- `/stories/artist` asks what will change in the artist's work.
- `/stories/technical-artist` asks whether the asset meets project policy.
- `/` helps a user choose among those three explanations.
- `/stories/advanced` goes directly to the supported policy controls.

Every route uses the same trusted profiles, bounded GLB upload, native Strands interrupt/resume,
deterministic repair engine, interactive previews, independent verification, and contracted result
ZIP. The workspace shows only one step at a time: **Rules -> Upload** during intake, then **Inspect
-> Decide -> Download** for the job. Each server-rendered state has one primary focus area; the seven
named execution stages, policy parameters, finding evidence, checks, and metrics remain available
through focused disclosures instead of competing with the current action. No
model or network request is needed for the agent workflow; the default uses the zero-network
scripted provider over the real Strands loop.

Repository profiles are immutable versioned policy presets. The web UI calls the two current
choices **Human-scale static mesh** (1.7-1.9 m accepted) and **Compact static mesh** (0.9-1.5 m
accepted); all other enforced rules are currently identical. Each preset keeps its concise summary
and complete rule review collapsed. An advanced **Customize a copy** control permits only supported
target-state and report-only budget overrides; safety policy and verification boundaries remain
fixed. Upload freezes the resolved policy into the new job, and provenance records its base preset,
explicit overrides, version, identifier, and canonical SHA-256. Changing rules starts a new
inspection and job.

Browser refresh preserves the current job while the server process remains running. A server restart
ends the in-memory approval session, while completed artifacts stay under `build/web/jobs/`. The 3D
preview uses the pinned official `<model-viewer>` browser component; GLB files remain served from the
local Asset Shepherd origin.

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
