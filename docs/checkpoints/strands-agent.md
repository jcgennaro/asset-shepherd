# Strands-agent checkpoint

**Date:** 2026-08-21

**Scope:** M7 local Strands inspect → plan → approve/reject → repair → verify → package

**Deterministic baseline:** `a077077ca94c44b9693893672a7208d84d1f05b8`

## Exact commands

The reviewed approve and reject runs used the real Strands `Agent` event loop and native tool
interrupt/resume with a zero-network scripted model harness:

```powershell
uv run asset-shepherd agent-run fixtures/broken_robot.glb --profile profiles/unreal_indie_robot.json --output build/checkpoints/strands-agent/approve-smoke-2 --decision approve --offline-scripted

uv run asset-shepherd agent-run fixtures/broken_robot.glb --profile profiles/unreal_indie_robot.json --output build/checkpoints/strands-agent/reject --decision reject --offline-scripted

uv run pytest tests/test_agent.py -q

uv lock --check
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

Output directories must not already exist. The environment-configured live-provider test remains
explicitly opt-in:

```powershell
$env:ASSET_SHEPHERD_MODEL_PROVIDER = 'bedrock'
$env:ASSET_SHEPHERD_MODEL_ID = '<model available in the configured account and region>'
$env:ASSET_SHEPHERD_AWS_REGION = '<configured region>'
$env:AWS_PROFILE = 'asset-shepherd'
$env:ASSET_SHEPHERD_RUN_LIVE = '1'
uv run pytest tests/test_agent.py -m live -q
```

That paid-provider command was not executed at this checkpoint because no model, region, AWS
profile, credentials, or AWS CLI are configured in the workspace. Ordinary and offline-agent tests
do not inspect credentials or access the network.

## Agent and tool boundary

One primary Strands agent receives six narrow tools bound to one trusted job workspace:

1. `inspect_asset_for_job`
2. `list_repair_candidates`
3. `select_repair_candidates`
4. `execute_selected_repairs`
5. `verify_and_package`
6. `retry_once_after_verification_failure`

> Update (2026-08-23): D032 supersedes the historical sixth-tool behavior. The current tool is
> `reassess_candidate_after_verification_failure`; it reinspects the failed candidate and derives
> a fresh plan without reapplying the old matrix or reusing its approval.

The model never supplies filesystem paths, transform matrices, binary content, or unregistered
repair definitions. The deterministic core owns those values. The version-1 system prompt enforces
the stage order, one combined approval, deterministic verification authority, and at most one
same-plan correction attempt.

## Interrupt and authorization results

- Both reviewed runs stopped once with `AgentResult.stop_reason == "interrupt"`.
- The JSON-serializable reason was one `ApprovalCard` for `normalize-root-v1`, combining measured
  scale, orientation, and grounding evidence, before/expected bounds, the proposed 4×4 matrix,
  consequences, and approve/reject options.
- The interrupt ID was
  `v1:tool_call:asset-shepherd-scripted-04:c78ad72b-0d6a-5ce0-bb66-568dd22348df`.
- Resume used a Strands `interruptResponse` carrying that exact ID. A mismatched ID is rejected
  before the agent resumes.
- `decisions.json` records the same interrupt ID, `USER_INTERACTIVE`, and either `APPROVED` or
  `REJECTED`.
- Direct execution without an interrupt-bound decision fails before `candidate.glb` exists.
- The rejected run executes the nine policy-safe renames but not normalization; scale,
  orientation, and grounding warnings remain explicit.

## Verification and package results

- Approved: 16 verification checks, all `PASS`; second plan candidate count 0; final state
  `PASSED_WITH_REMAINING_WARNINGS` only because material budget is report-only.
- Rejected: 14 verification checks, all `PASS`; second plan candidate count 0; final state
  `PASSED_WITH_REMAINING_WARNINGS` with unresolved scale, orientation, grounding, and material
  budget warnings.
- The approved agent `repaired.glb` SHA-256 is
  `be1c920ffe92d869226061da8ce63a02baa3053f23ccbb76eeb71ab47ca6e535`, byte-identical to the
  deterministic-core approved output.
- Both ZIPs contain exactly the seven contracted artifacts.
- A controlled injected verification failure proves the agent calls the bounded retry tool once,
  re-verifies, and refuses a second correction attempt.

## Artifact tree

`agent_result.json` and `job_result.json` remain outside the unchanged contracted ZIP.

```text
build/checkpoints/strands-agent/
├── approve-smoke-2/
│   ├── agent_result.json
│   ├── decisions.json
│   ├── inspection.json
│   ├── job_result.json
│   ├── provenance.json
│   ├── repair_plan.json
│   ├── repaired.glb
│   ├── report.md
│   ├── result.zip
│   │   ├── decisions.json
│   │   ├── inspection.json
│   │   ├── provenance.json
│   │   ├── repair_plan.json
│   │   ├── repaired.glb
│   │   ├── report.md
│   │   └── verification.json
│   └── verification.json
└── reject/
    └── (same ten job files and seven ZIP members)
```

## Measured scripted-run metrics

The reviewed approved run reported 0.206 seconds of agent invocation time, 48 input tokens, 12
output tokens, 60 total tokens, one interrupt, zero correction attempts, and the final verification
state. Every tool includes call, success, error, and duration totals in `agent_result.json`.

Strands records the first call to `execute_selected_repairs` as an error when its interrupt pauses
execution, then records the resumed call as a success. The approved run therefore transparently
reports two calls, one success, and one error for that tool; this is native SDK accounting rather
than a failed repair.

## Known limitations

- The reviewed end-to-end runs use the scripted zero-network model harness. They prove genuine
  Strands orchestration, tool dispatch, metrics, interrupt, and resume without proving behavior or
  cost for a paid foundation model.
- A Bedrock provider is configurable entirely through environment variables and has an opt-in live
  test, but it was not invoked because the user-owned account configuration is absent. No obsolete
  model ID is embedded in code.
- Interrupt state is resumed on the same in-process agent instance. Durable cross-process/web
  session persistence belongs to M8 and has not been added early.
- The provider-reported scripted token counts exercise the metrics path; paid-provider token values
  will depend on that provider's response metadata.
