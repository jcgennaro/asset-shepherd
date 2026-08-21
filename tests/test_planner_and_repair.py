"""M5 acceptance tests for planning, authorization, and repair."""

# pygltflib is typed internally but does not publish PEP 561 metadata.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

import re
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import cast

import numpy as np
import pytest
from pygltflib import GLTF2

from asset_shepherd.cli import run_cli
from asset_shepherd.glb import geometry_counts, load_glb, world_bounds
from asset_shepherd.inspector import inspect_asset
from asset_shepherd.models import (
    Decisions,
    DecisionSource,
    NormalizationPayload,
    ProjectProfile,
    RenamePayload,
    RepairPlan,
)
from asset_shepherd.planner import plan_repairs
from asset_shepherd.repair import (
    RepairAuthorizationError,
    RepairInvariantError,
    apply_repairs,
    create_decisions,
    validate_decisions,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = PROJECT_ROOT / "profiles" / "unreal_indie_robot.json"
BROKEN_PATH = PROJECT_ROOT / "fixtures" / "broken_robot.glb"
DECIDED_AT = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)


def _profile() -> ProjectProfile:
    return ProjectProfile.model_validate_json(PROFILE_PATH.read_text(encoding="utf-8"))


def _primitive_refs(
    gltf: GLTF2,
) -> tuple[tuple[object, object, int | None, int | None], ...]:
    return tuple(
        (
            cast(object, primitive.attributes.POSITION),
            cast(object, primitive.attributes.NORMAL),
            primitive.indices,
            primitive.material,
        )
        for mesh in gltf.meshes
        for primitive in mesh.primitives
    )


def test_plan_contains_only_registered_rename_and_normalization_candidates() -> None:
    """Broken-fixture findings become nine safe renames and one approval card."""
    profile = _profile()
    inspection = inspect_asset(BROKEN_PATH, profile)
    plan = plan_repairs(inspection, profile)
    assert not plan.blocked
    assert len(plan.auto_action_ids) == 9
    assert plan.approval_action_ids == ("normalize-root-v1",)
    assert len(plan.candidates) == 10
    assert all(candidate.finding_ids for candidate in plan.candidates)
    rename_payloads = [
        candidate.payload
        for candidate in plan.candidates
        if isinstance(candidate.payload, RenamePayload)
    ]
    assert len(rename_payloads) == 9
    assert {payload.before_name for payload in rename_payloads} >= {
        None,
        "robot root",
        "duplicate part",
        "bad mesh",
    }
    normalization = next(
        candidate.payload
        for candidate in plan.candidates
        if isinstance(candidate.payload, NormalizationPayload)
    )
    assert {component.component for component in normalization.components} == {
        "scale",
        "orientation",
        "grounding",
    }
    assert normalization.expected_after_bounds.dimensions_m[1] == pytest.approx(1.8)
    assert normalization.expected_after_bounds.minimum_m[1] == pytest.approx(0.0, abs=1e-9)


def test_missing_or_policy_forged_approval_is_rejected() -> None:
    """An approval-required action cannot run without an explicit user record."""
    profile = _profile()
    plan = plan_repairs(inspect_asset(BROKEN_PATH, profile), profile)
    with pytest.raises(RepairAuthorizationError, match="missing"):
        create_decisions(plan, {}, decided_at=DECIDED_AT)

    approved = create_decisions(
        plan,
        {"normalize-root-v1": True},
        decided_at=DECIDED_AT,
    )
    missing_user_record = Decisions(plan_id=plan.plan_id, records=approved.records[:-1])
    with pytest.raises(RepairAuthorizationError, match="Missing user decision"):
        validate_decisions(plan, missing_user_record)

    forged_records = list(approved.records)
    forged_records[-1] = forged_records[-1].model_copy(update={"source": DecisionSource.POLICY})
    forged = Decisions(plan_id=plan.plan_id, records=tuple(forged_records))
    with pytest.raises(RepairAuthorizationError, match="cannot come from policy"):
        validate_decisions(plan, forged)


def test_approved_repair_is_safe_verified_by_reinspection_and_idempotent(tmp_path: Path) -> None:
    """Approved repairs preserve content and make the second plan empty."""
    profile = _profile()
    inspection = inspect_asset(BROKEN_PATH, profile)
    plan = plan_repairs(inspection, profile)
    decisions = create_decisions(
        plan,
        {"normalize-root-v1": True},
        decided_at=DECIDED_AT,
    )
    first_output = tmp_path / "first.glb"
    second_output = tmp_path / "second.glb"
    source_before = BROKEN_PATH.read_bytes()
    source_gltf = load_glb(BROKEN_PATH)
    source_node_meshes = tuple(node.mesh for node in source_gltf.nodes)
    source_primitive_refs = _primitive_refs(source_gltf)

    first = apply_repairs(BROKEN_PATH, first_output, plan, decisions)
    second = apply_repairs(BROKEN_PATH, second_output, plan, decisions)
    assert first.output_sha256 == second.output_sha256
    assert first_output.read_bytes() == second_output.read_bytes()
    assert BROKEN_PATH.read_bytes() == source_before
    assert first.source_sha256 == sha256(source_before).hexdigest()
    assert len(first.executed_action_ids) == 10
    assert first.rejected_action_ids == ()

    repaired = load_glb(first_output)
    assert (
        tuple(node.mesh for node in repaired.nodes[: len(source_gltf.nodes)]) == source_node_meshes
    )
    repaired_primitive_refs = _primitive_refs(repaired)
    assert repaired_primitive_refs == source_primitive_refs
    assert geometry_counts(repaired) == geometry_counts(source_gltf)
    assert len(repaired.materials) == len(source_gltf.materials)
    assert len(repaired.textures) == len(source_gltf.textures)

    repaired_inspection = inspect_asset(first_output, profile)
    assert repaired_inspection.geometry is not None
    assert repaired_inspection.geometry.dominant_dimension_axis == "Y"
    assert repaired_inspection.geometry.ground_relationship == "GROUNDED"
    assert repaired_inspection.geometry.bounds.dimensions_m[1] == pytest.approx(1.8)
    assert {finding.code for finding in repaired_inspection.findings} == {
        "MATERIAL_BUDGET_EXCEEDED"
    }
    assert repaired_inspection.naming is not None
    names = [name for name in repaired_inspection.naming.node_names if name]
    mesh_names = [name for name in repaired_inspection.naming.mesh_names if name]
    pattern = re.compile(profile.naming.pattern)
    assert len(names) == len(set(names))
    assert len(mesh_names) == len(set(mesh_names))
    assert all(pattern.fullmatch(name) for name in [*names, *mesh_names])
    second_plan = plan_repairs(repaired_inspection, profile)
    assert second_plan.candidates == ()


def test_rejected_normalization_stays_rejected_while_safe_names_apply(tmp_path: Path) -> None:
    """Rejecting normalization leaves geometry unchanged while policy renames run."""
    profile = _profile()
    plan = plan_repairs(inspect_asset(BROKEN_PATH, profile), profile)
    decisions = create_decisions(
        plan,
        {"normalize-root-v1": False},
        decided_at=DECIDED_AT,
    )
    output = tmp_path / "rejected.glb"
    outcome = apply_repairs(BROKEN_PATH, output, plan, decisions)
    assert outcome.rejected_action_ids == ("normalize-root-v1",)
    before_bounds = world_bounds(load_glb(BROKEN_PATH))
    after_bounds = world_bounds(load_glb(output))
    np.testing.assert_allclose(after_bounds.minimum, before_bounds.minimum)
    np.testing.assert_allclose(after_bounds.maximum, before_bounds.maximum)
    inspection = inspect_asset(output, profile)
    assert inspection.naming is not None
    assert inspection.naming.proposed_replacements == {}
    assert {
        "HEIGHT_OUT_OF_RANGE",
        "ORIENTATION_NOT_Y_UP",
        "NOT_GROUNDED",
    } <= {finding.code for finding in inspection.findings}


def test_repair_refuses_source_overwrite(tmp_path: Path) -> None:
    """The source path can never be the repair output path."""
    profile = _profile()
    copied_source = tmp_path / "source.glb"
    copied_source.write_bytes(BROKEN_PATH.read_bytes())
    plan = plan_repairs(inspect_asset(copied_source, profile), profile)
    decisions = create_decisions(
        plan,
        {"normalize-root-v1": True},
        decided_at=DECIDED_AT,
    )
    with pytest.raises(RepairInvariantError, match="must not overwrite"):
        apply_repairs(copied_source, copied_source, plan, decisions)


def test_repair_cli_emits_plan_decisions_and_repaired_asset(tmp_path: Path) -> None:
    """The M5 CLI materializes the plan and authorization artifacts."""
    approvals_path = tmp_path / "approvals.json"
    approvals_path.write_text('{"normalize-root-v1": true}\n', encoding="utf-8")
    output = tmp_path / "output"
    exit_code = run_cli(
        [
            "repair",
            str(BROKEN_PATH),
            "--profile",
            str(PROFILE_PATH),
            "--approvals",
            str(approvals_path),
            "--output",
            str(output),
        ]
    )
    assert exit_code == 0
    assert {path.name for path in output.iterdir()} == {
        "decisions.json",
        "inspection.json",
        "repair_plan.json",
        "repaired.glb",
        "report.md",
    }
    plan = RepairPlan.model_validate_json((output / "repair_plan.json").read_text(encoding="utf-8"))
    decisions = Decisions.model_validate_json(
        (output / "decisions.json").read_text(encoding="utf-8")
    )
    validate_decisions(plan, decisions)
