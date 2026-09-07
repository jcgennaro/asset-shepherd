"""Regression coverage for agent-authored, unsupported repair dispositions."""

# pyright: reportPrivateUsage=false

from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from asset_shepherd.agent_job import AgentJob
from asset_shepherd.hosted_workspace import HostedWorkspace
from asset_shepherd.inspector import inspect_asset
from asset_shepherd.models import (
    AgentDisposition,
    AgentRepairAssessment,
    AssetIntentProvenance,
    AssetTargetUse,
    JobResult,
    JobState,
    VerificationState,
)
from asset_shepherd.web import (
    _completion_sentence,
    _has_next_turn_candidate,
    _inspection_checks,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = PROJECT_ROOT / "fixtures" / "broken_robot.glb"
PROFILE_PATH = PROJECT_ROOT / "profiles" / "unreal_indie_robot.json"


def test_unsupported_component_mismatch_is_an_explicit_blocker(tmp_path: Path) -> None:
    """A correct return-to-creation-tool decision cannot look like structural success."""
    intent = AssetIntentProvenance(
        intent_id="1" * 32,
        original_description="One riding crop intended as a static game prop.",
        target_use=AssetTargetUse.STATIC_GAME_ASSET,
        target_height_cm=70.0,
        expected_piece_count=1,
        expected_piece_count_evidence="The description requests one riding crop.",
        confirmed_story="One riding crop intended as a 70 cm static game prop.",
        confirmed_at=datetime(2026, 8, 27, tzinfo=UTC),
        canonical_sha256="2" * 64,
    )
    job = AgentJob(
        source=SOURCE_PATH,
        profile_path=PROFILE_PATH,
        output_dir=tmp_path / "output",
        asset_intent=intent,
        agent_orchestrated=True,
    )
    inspection = inspect_asset(SOURCE_PATH, job.profile, policy=job.profile_policy)
    assert inspection.diagnostics is not None
    base_component = inspection.diagnostics.primitives[0].disconnected_components[0]
    components = tuple(
        base_component.model_copy(
            update={
                "component_id": f"component-m000-p000-c{index:03d}-{index + 1:08x}",
                "ordinal": index,
                "triangle_fraction": 1 / 3,
            }
        )
        for index in range(3)
    )
    primitive = inspection.diagnostics.primitives[0].model_copy(
        update={
            "virtual_weld_connected_component_count": 3,
            "disconnected_components": components,
            "component_removal_safe": False,
            "component_removal_block_reason": "unsupported test layout",
        }
    )
    job.inspection = inspection.model_copy(
        update={
            "diagnostics": inspection.diagnostics.model_copy(update={"primitives": (primitive,)})
        }
    )
    job.agent_assessment = AgentRepairAssessment(
        assessment_id="assessment-0123456789abcdef-v1",
        disposition=AgentDisposition.RETURN_TO_CREATION_TOOL,
        summary=(
            "Return the asset to the creation tool because the target is one riding crop, "
            "but the source contains three visible forms."
        ),
        evidence=(
            "The source views show three distinct forms and inspection reports 3 connected "
            "components.",
        ),
        confidence=0.99,
    )
    job.result = JobResult(
        job_id="blocked-component-mismatch",
        state=JobState.BLOCKED,
        verification_state=VerificationState.BLOCKED,
        ready_candidate=False,
        artifact_names=(),
        result_zip=None,
        message="No supported repair path.",
    )

    structure = _inspection_checks(job)[0]
    assert structure.status == "blocked"
    assert structure.status_label == "Cannot repair"
    assert structure.description == "3 disconnected forms detected; target 1 semantic piece."
    assert structure.action == (
        "Cannot repair — this GLB layout is not eligible for component removal."
    )
    assert _completion_sentence(cast(HostedWorkspace, None), job) == (
        "I can't repair this asset — return the asset to the creation tool because the target "
        "is one riding crop, but the source contains three visible forms."
    )
    assert not _has_next_turn_candidate(job)


def test_safe_component_mismatch_reports_an_unselected_supported_path(tmp_path: Path) -> None:
    """A stopped agent pass cannot falsely claim the supported remover is unavailable."""
    intent = AssetIntentProvenance(
        intent_id="3" * 32,
        original_description="One riding crop intended as a static game prop.",
        target_use=AssetTargetUse.STATIC_GAME_ASSET,
        target_height_cm=70.0,
        expected_piece_count=1,
        expected_piece_count_evidence="The description requests one riding crop.",
        confirmed_story="One riding crop intended as a 70 cm static game prop.",
        confirmed_at=datetime(2026, 8, 28, tzinfo=UTC),
        canonical_sha256="4" * 64,
    )
    job = AgentJob(
        source=SOURCE_PATH,
        profile_path=PROFILE_PATH,
        output_dir=tmp_path / "output",
        asset_intent=intent,
        agent_orchestrated=True,
    )
    inspection = inspect_asset(SOURCE_PATH, job.profile, policy=job.profile_policy)
    assert inspection.diagnostics is not None
    base_component = inspection.diagnostics.primitives[0].disconnected_components[0]
    components = tuple(
        base_component.model_copy(
            update={
                "component_id": f"component-m000-p000-c{index:03d}-{index + 10:08x}",
                "ordinal": index,
                "triangle_fraction": 1 / 3,
            }
        )
        for index in range(3)
    )
    primitive = inspection.diagnostics.primitives[0].model_copy(
        update={
            "virtual_weld_connected_component_count": 3,
            "disconnected_components": components,
            "component_removal_safe": True,
            "component_removal_block_reason": None,
        }
    )
    job.inspection = inspection.model_copy(
        update={
            "diagnostics": inspection.diagnostics.model_copy(update={"primitives": (primitive,)})
        }
    )
    job.agent_assessment = AgentRepairAssessment(
        assessment_id="assessment-fedcba9876543210-v1",
        disposition=AgentDisposition.RETURN_TO_CREATION_TOOL,
        summary="The previous pass stopped before selecting a surviving riding-crop form.",
        evidence=(
            "The source views show three separate forms and inspection reports 3 connected "
            "components.",
        ),
        confidence=0.7,
    )
    job.result = JobResult(
        job_id="recoverable-component-mismatch",
        state=JobState.BLOCKED,
        verification_state=VerificationState.BLOCKED,
        ready_candidate=False,
        artifact_names=(),
        result_zip=None,
        message="The pass stopped before selecting labeled components.",
    )

    structure = _inspection_checks(job)[0]
    assert structure.status == "attention"
    assert structure.status_label == "Agent stopped"
    assert structure.action == (
        "No labeled components were selected in this pass — refine the current iteration to "
        "review a removal proposal."
    )
    topology = next(check for check in _inspection_checks(job) if check.label == "Topology")
    assert len(topology.component_proposals) == 3
    for component in topology.component_proposals:
        assert component.detail.endswith("triangles · 33.3%")
        assert "of this primitive" not in component.detail
    assert _completion_sentence(cast(HostedWorkspace, None), job) == (
        "I stopped this pass before choosing which labeled forms to keep. Refine the current "
        "iteration to review a component-removal proposal."
    )
