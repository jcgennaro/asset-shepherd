"""Bounded degenerate-triangle and unused-vertex cleanup acceptance tests."""

# pyright: reportPrivateUsage=false

from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from asset_shepherd.agent_job import AgentJob
from asset_shepherd.fixtures import fixture_profile
from asset_shepherd.glb import load_glb, save_glb
from asset_shepherd.inspector import inspect_asset
from asset_shepherd.models import (
    ActionClass,
    AgentDisposition,
    AgentRepairAssessment,
    DegenerateGeometryPayload,
)
from asset_shepherd.planner import plan_agent_repairs
from asset_shepherd.repair import apply_repairs, create_decisions
from asset_shepherd.verification import verify_repair
from asset_shepherd.web import _inspection_checks
from asset_shepherd.workflow import build_provenance

FIXTURE = Path("fixtures/geometry_failures/degenerate_triangle.glb")
PROFILE = Path("profiles/unreal_indie_robot.json")


def _assessment() -> AgentRepairAssessment:
    return AgentRepairAssessment(
        assessment_id="assessment-0123456789abcdef-v1",
        disposition=AgentDisposition.REPAIR,
        summary="One zero-area triangle and its unused vertex tuple can be removed exactly.",
        evidence=(
            "Inspection proves one degenerate triangle and one unused position in a safe layout.",
        ),
        confidence=1.0,
        clean_degenerate_geometry=True,
    )


def test_agent_requested_degenerate_cleanup_executes_and_verifies(tmp_path: Path) -> None:
    """An approved cleanup removes only proven redundant geometry and passes reinspection."""
    source = tmp_path / "source.glb"
    source.write_bytes(FIXTURE.read_bytes())
    source_before = source.read_bytes()
    candidate = tmp_path / "candidate.glb"
    profile = fixture_profile()
    original = inspect_asset(source, profile)
    assert original.diagnostics is not None
    primitive = original.diagnostics.primitives[0]
    assert primitive.degenerate_triangle_count == 1
    assert primitive.unused_position_count == 1
    assert primitive.degenerate_cleanup_safe

    assessment = _assessment()
    plan = plan_agent_repairs(
        original,
        profile,
        assessment,
        confirmed_target_height_m=1.0,
    )
    assert plan.approval_action_ids == ("clean-degenerate-geometry-v1",)
    payload = next(
        candidate_repair.payload
        for candidate_repair in plan.candidates
        if isinstance(candidate_repair.payload, DegenerateGeometryPayload)
    )
    assert payload.primitives[0].before_triangle_count == 12
    assert payload.primitives[0].after_triangle_count == 11
    assert payload.primitives[0].before_position_count == 24
    assert payload.primitives[0].after_position_count == 23
    job = AgentJob(
        source=source,
        profile_path=PROFILE,
        output_dir=tmp_path / "job",
        agent_orchestrated=True,
    )
    job.inspection = original
    job.agent_assessment = assessment
    job.selected_plan = plan
    topology_before = _inspection_checks(job)[2]
    assert topology_before.status_label == "Needs approval"
    assert topology_before.description.startswith("1 degenerate triangle · 1 unused vertex tuple")
    assert topology_before.action == (
        "Approval required — remove 1 zero-area triangle and compact 1 unreferenced vertex tuple."
    )
    assert topology_before.response_lane == "TOPOLOGY"
    card = job.approval_card()
    assert card is not None
    assert card.candidate_id == "clean-degenerate-geometry-v1"
    assert card.title == "Clean proven degenerate geometry"
    assert card.proposed_matrix is None

    decided_at = datetime(2026, 8, 27, tzinfo=UTC)
    decisions = create_decisions(
        plan,
        {"clean-degenerate-geometry-v1": True},
        decided_at=decided_at,
    )
    outcome = apply_repairs(source, candidate, plan, decisions)
    provenance = build_provenance(
        profile,
        plan,
        decisions,
        outcome,
        started_at=decided_at,
        completed_at=decided_at,
        agent_assessment=assessment,
    )
    verification = verify_repair(
        source,
        candidate,
        profile,
        original,
        plan,
        decisions,
        outcome,
        provenance,
    )
    output = inspect_asset(candidate, profile)

    assert source.read_bytes() == source_before
    assert sha256(source_before).hexdigest() == outcome.source_sha256
    assert outcome.executed_action_ids == ("clean-degenerate-geometry-v1",)
    assert output.geometry is not None
    assert output.geometry.vertex_count == 359
    assert output.geometry.triangle_count == 179
    assert output.diagnostics is not None
    assert output.diagnostics.primitives[0].position_count == 23
    assert output.diagnostics.primitives[0].degenerate_triangle_count == 0
    assert output.diagnostics.primitives[0].unused_position_count == 0
    assert not any(
        finding.code in {"DEGENERATE_TRIANGLES_DETECTED", "UNUSED_VERTEX_DATA_DETECTED"}
        for finding in output.findings
    )
    assert all(check.status != "FAIL" for check in verification.checks)
    assert any(
        check.code == "DEGENERATE_GEOMETRY_CLEANUP_CONFIRMED" and check.status == "PASS"
        for check in verification.checks
    )
    job.outcome = outcome
    job.last_verification = verification
    topology_after = _inspection_checks(job)[2]
    assert topology_after.status_label == "Addressed"
    assert topology_after.action.startswith("Applied — remove 1 zero-area triangle")


def test_rejected_degenerate_cleanup_is_recorded_without_mutation(tmp_path: Path) -> None:
    """Rejecting the exact cleanup preserves both bytes and unresolved findings."""
    source = tmp_path / "source.glb"
    source.write_bytes(FIXTURE.read_bytes())
    candidate = tmp_path / "candidate.glb"
    profile = fixture_profile()
    original = inspect_asset(source, profile)
    assessment = _assessment()
    plan = plan_agent_repairs(
        original,
        profile,
        assessment,
        confirmed_target_height_m=1.0,
    )
    decisions = create_decisions(
        plan,
        {"clean-degenerate-geometry-v1": False},
        decided_at=datetime(2026, 8, 27, tzinfo=UTC),
    )
    outcome = apply_repairs(source, candidate, plan, decisions)
    output = inspect_asset(candidate, profile)

    assert candidate.read_bytes() == source.read_bytes()
    assert outcome.executed_action_ids == ()
    assert outcome.rejected_action_ids == ("clean-degenerate-geometry-v1",)
    assert any(finding.code == "DEGENERATE_TRIANGLES_DETECTED" for finding in output.findings)
    assert any(finding.code == "UNUSED_VERTEX_DATA_DETECTED" for finding in output.findings)


def test_triangle_strip_degenerate_geometry_remains_report_only(tmp_path: Path) -> None:
    """An unsupported primitive mode never gains cleanup authority from the same finding."""
    source = tmp_path / "strip.glb"
    gltf = load_glb(FIXTURE)
    gltf.meshes[0].primitives[0].mode = 5
    save_glb(gltf, source)

    inspection = inspect_asset(source, fixture_profile())
    assert inspection.diagnostics is not None
    primitive = inspection.diagnostics.primitives[0]
    assert primitive.degenerate_triangle_count > 0
    assert not primitive.degenerate_cleanup_safe
    assert primitive.degenerate_cleanup_block_reason == (
        "cleanup requires an indexed TRIANGLES primitive"
    )
    finding = next(
        item for item in inspection.findings if item.code == "DEGENERATE_TRIANGLES_DETECTED"
    )
    assert finding.action_class is ActionClass.REPORT_ONLY
    assert finding.candidate_repairs == ()
