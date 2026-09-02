"""Use-case-driven, explicitly approved mesh simplification tests."""

# Trimesh does not publish complete PEP 561 metadata.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import trimesh

from asset_shepherd.fixtures import fixture_profile
from asset_shepherd.glb import load_glb, save_glb
from asset_shepherd.inspector import inspect_asset
from asset_shepherd.models import (
    AgentDisposition,
    AgentRepairAssessment,
    AssetTargetUse,
    AssetViewingUse,
    MeshSimplificationPayload,
)
from asset_shepherd.planner import plan_agent_repairs
from asset_shepherd.policy_resolution import VIEWING_USE_TRIANGLE_CAPS, resolve_policy_family
from asset_shepherd.repair import apply_repairs, create_decisions
from asset_shepherd.verification import verify_repair
from asset_shepherd.workflow import build_provenance


def _dense_sphere(path: Path) -> None:
    mesh = trimesh.creation.icosphere(subdivisions=5, radius=1.0)
    payload = cast(bytes, trimesh.Scene(mesh).export(file_type="glb"))
    path.write_bytes(payload)
    gltf = load_glb(path)
    gltf.meshes[0].name = "Mesh_000"
    gltf.nodes[0].name = "Node_000"
    save_glb(gltf, path)


def _assessment() -> AgentRepairAssessment:
    return AgentRepairAssessment(
        assessment_id="assessment-1122334455667788-v1",
        disposition=AgentDisposition.REPAIR,
        summary="The asset exceeds its confirmed normal-gameplay complexity cap.",
        evidence=("The measured triangle count is above the use-case-derived target.",),
        confidence=1.0,
        simplify_mesh=True,
        source_views_used=("source-front.png", "source-three-quarter.png"),
    )


def test_viewing_use_maps_to_the_three_product_triangle_caps() -> None:
    """A nontechnical viewing choice deterministically freezes the requested caps."""
    family = fixture_profile()
    for viewing_use, expected_cap in VIEWING_USE_TRIANGLE_CAPS.items():
        resolution = resolve_policy_family(
            family,
            description="A one metre static game asset for Unreal.",
            target_use=AssetTargetUse.STATIC_GAME_ASSET,
            target_height_cm=100.0,
            viewing_use=viewing_use,
        )
        assert resolution.profile.budgets.max_triangles == expected_cap
        assert resolution.provenance.rule_sources["budgets.max_triangles"] == ("CONFIRMED_INTENT")

    assert VIEWING_USE_TRIANGLE_CAPS == {
        AssetViewingUse.CLOSE_UP_SHOWCASE: 50_000,
        AssetViewingUse.NORMAL_GAMEPLAY: 15_000,
        AssetViewingUse.SMALL_DISTANT_REPEATED: 2_500,
    }


def test_approved_simplification_reduces_and_independently_verifies(tmp_path: Path) -> None:
    """The original stays immutable while an approved, reopenable candidate gets smaller."""
    source = tmp_path / "source.glb"
    candidate = tmp_path / "candidate.glb"
    _dense_sphere(source)
    source_bytes = source.read_bytes()
    profile = fixture_profile().model_copy(
        update={"budgets": fixture_profile().budgets.model_copy(update={"max_triangles": 15_000})}
    )
    original = inspect_asset(source, profile)
    assert original.geometry is not None
    assert original.geometry.triangle_count == 20_480
    assert original.diagnostics is not None
    assert original.diagnostics.primitives[0].mesh_simplification_safe

    assessment = _assessment()
    plan = plan_agent_repairs(
        original,
        profile,
        assessment,
        confirmed_target_height_m=1.0,
    )
    assert plan.approval_action_ids == ("simplify-mesh-v1",)
    payload = plan.candidates[0].payload
    assert isinstance(payload, MeshSimplificationPayload)
    assert payload.target_triangle_count == 15_000

    decided_at = datetime(2026, 9, 2, tzinfo=UTC)
    decisions = create_decisions(
        plan,
        {"simplify-mesh-v1": True},
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

    assert source.read_bytes() == source_bytes
    assert output.geometry is not None
    assert 0 < output.geometry.triangle_count <= 15_000
    assert candidate.stat().st_size < source.stat().st_size
    failed_checks = tuple(
        (check.code, check.description, check.expected, check.actual)
        for check in verification.checks
        if check.status == "FAIL"
    )
    assert not failed_checks, failed_checks
    assert any(
        check.code == "MESH_SIMPLIFICATION_REDUCED_TRIANGLES" and check.status == "PASS"
        for check in verification.checks
    )


def test_rejected_simplification_preserves_the_original_detail(tmp_path: Path) -> None:
    """The user can explicitly refuse the lossy recommendation without any mutation."""
    source = tmp_path / "source.glb"
    candidate = tmp_path / "candidate.glb"
    _dense_sphere(source)
    profile = fixture_profile().model_copy(
        update={"budgets": fixture_profile().budgets.model_copy(update={"max_triangles": 15_000})}
    )
    original = inspect_asset(source, profile)
    plan = plan_agent_repairs(
        original,
        profile,
        _assessment(),
        confirmed_target_height_m=1.0,
    )
    decisions = create_decisions(
        plan,
        {"simplify-mesh-v1": False},
        decided_at=datetime(2026, 9, 2, tzinfo=UTC),
    )

    outcome = apply_repairs(source, candidate, plan, decisions)

    assert candidate.read_bytes() == source.read_bytes()
    assert outcome.executed_action_ids == ()
    assert outcome.rejected_action_ids == ("simplify-mesh-v1",)
