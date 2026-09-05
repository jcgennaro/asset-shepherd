"""No-network regression for a provider repeatedly hitting an unavailable sensor."""

import json
from pathlib import Path
from typing import cast

import pytest
from strands import Agent
from strands.hooks import AfterToolsEvent

from asset_shepherd.agent_job import AgentJob, AgentWorkflowError
from asset_shepherd.agent_runtime import AssetShepherdAgent, ScriptedWorkflowModel
from asset_shepherd.tool_failure_guard import VisualSensingFailureGuard

ROOT = Path(__file__).resolve().parents[1]


def test_repeated_visual_failure_stops_and_keeps_usage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A real Strands loop stops after two failures and records both without a paid call."""
    job = AgentJob(
        ROOT / "fixtures/clean_robot.glb",
        ROOT / "profiles/unreal_indie_robot.json",
        tmp_path / "output",
        agent_orchestrated=True,
    )
    model = ScriptedWorkflowModel(job)

    def next_action() -> tuple[str, dict[str, object]]:
        return (
            "inspect_asset_for_job" if job.inspection is None else "render_source_views_for_job",
            {},
        )

    monkeypatch.setattr(
        model,
        "_next_action",
        next_action,
    )

    def fail_render() -> tuple[Path, ...]:
        raise AgentWorkflowError("Standardized visual sensing rejected back.png: asset is clipped")

    monkeypatch.setattr(job, "render_source_views", fail_render)
    runtime = AssetShepherdAgent(job, model, provider="scripted", model_id="test")
    with pytest.raises(AgentWorkflowError, match="Repeated visual sensing failure"):
        runtime.start()
    ledger = json.loads((tmp_path / "output/agent_invocations.json").read_text())
    invocation = ledger["invocations"][0]
    assert invocation["stop_reason"] == "end_turn"
    assert "token_usage" in invocation
    calls = {row["name"]: row for row in invocation["tool_calls"]}
    assert calls["render_source_views_for_job"]["error_count"] == 2
    assert calls["inspect_asset_for_job"]["call_count"] == 1
    assert job.outcome is None
    assert job.agent_assessment is None


def test_visual_failure_counter_crosses_tools_but_resets_for_new_invocation() -> None:
    """Changing plan arguments cannot loop around the same failed rendering prerequisite."""
    guard = VisualSensingFailureGuard()

    def event(tool_id: str, message: str) -> AfterToolsEvent:
        return AfterToolsEvent(
            agent=cast(Agent, object()),
            invocation_state={},
            message={
                "role": "user",
                "content": [
                    {
                        "toolResult": {
                            "toolUseId": tool_id,
                            "status": "error",
                            "content": [{"text": message}],
                        }
                    }
                ],
            },
        )

    ordinary_error = event("plan", "Invalid optional argument")
    guard.after_tools(ordinary_error)
    guard.after_tools(ordinary_error)
    assert not ordinary_error.end_turn
    failure = "Standardized visual sensing rejected back.png: asset is clipped"
    first = event("render", failure)
    guard.after_tools(first)
    assert not first.end_turn
    second = event("plan", failure)
    guard.after_tools(second)
    assert second.end_turn
    assert guard.stop_error is not None
    guard.reset()
    retry = event("render", failure)
    guard.after_tools(retry)
    assert not retry.end_turn
    assert guard.stop_error is None
