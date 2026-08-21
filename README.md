# Asset Shepherd

Asset Shepherd is an autonomous 3D-asset intake, inspection, repair-planning, and
verification agent for game developers.

> [!NOTE]
> This repository is an early hackathon work in progress.

## Project control

- [Project contract](docs/PROJECT_CONTRACT.md)
- [Project status](docs/PROJECT_STATUS.md)
- [Decision log](docs/DECISIONS.md)

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
