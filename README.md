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

## Real-world validation

The [validation workspace](validation/README.md) preserves immutable raw provenance, controlled
mutation ground truth, Blender evidence, and an isolated Unreal comparison harness. Patchling
Courier is registered as the current hero and preservation case. Shader Lantern is the next
one-batch human-generated asset; its exact prompt, selection criteria, export settings, destination,
and untouched-file rules are in the
[Shader Lantern generation card](validation/corpus/shader_lantern_01/generation-card.md).
The rights-confirmed 4.86 MB
[Patchling raw GLB](validation/corpus/patchling_01/raw/asset.glb) is the repository's first
distributable real-world demo input; generated outputs remain reproducible and untracked.

## Local web product

```powershell
uv sync
uv run asset-shepherd web
```

Open `http://127.0.0.1:8000`. The local web product provides trusted profile selection, bounded GLB
upload, named progress stages, severity-grouped findings, a single normalization approval card,
native Strands interrupt/resume, interactive before/after previews, independent verification, and a
downloadable contracted result ZIP. No model or network request is needed for the agent workflow;
the default uses the zero-network scripted provider over the real Strands loop.

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
