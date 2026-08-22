"""M4 acceptance tests for deterministic GLB inspection."""

# pygltflib is typed internally but does not publish PEP 561 metadata.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from hashlib import sha256
from pathlib import Path
from struct import pack
from typing import cast

from pygltflib import Skin

from asset_shepherd.cli import run_cli
from asset_shepherd.glb import load_glb, save_glb
from asset_shepherd.inspector import inspect_asset, render_inspection_report
from asset_shepherd.models import (
    ActionClass,
    AssetTargetUse,
    CheckBasis,
    FixtureManifest,
    ProjectProfile,
    RepairEligibility,
    Severity,
)
from asset_shepherd.policy_resolution import resolve_policy_family

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = PROJECT_ROOT / "profiles" / "unreal_indie_robot.json"
CLEAN_PATH = PROJECT_ROOT / "fixtures" / "clean_robot.glb"
BROKEN_PATH = PROJECT_ROOT / "fixtures" / "broken_robot.glb"


def _profile() -> ProjectProfile:
    return ProjectProfile.model_validate_json(PROFILE_PATH.read_text(encoding="utf-8"))


def test_broken_fixture_inspection_matches_expected_defects() -> None:
    """Every encoded broken-fixture defect is found with structured evidence."""
    source_before = BROKEN_PATH.read_bytes()
    inspection = inspect_asset(BROKEN_PATH, _profile())
    manifest = FixtureManifest.model_validate_json(
        (PROJECT_ROOT / "fixtures" / "broken_robot.expected.json").read_text(encoding="utf-8")
    )
    assert inspection.repair_eligibility is RepairEligibility.ELIGIBLE_STATIC_MESH
    assert {finding.code for finding in inspection.findings} == set(manifest.expected_defect_codes)
    assert all(finding.evidence for finding in inspection.findings)
    assert inspection.geometry is not None
    assert inspection.geometry.dominant_dimension_axis == "X"
    assert inspection.geometry.ground_relationship == "FLOATS_ABOVE"
    assert inspection.naming is not None
    assert inspection.naming.proposed_replacements == {
        "mesh:0": "Mesh_000",
        "mesh:1": "Mesh_001",
        "mesh:2": "Mesh_002",
        "mesh:3": "Mesh_003",
        "node:0": "Node_000",
        "node:1": "Node_001",
        "node:2": "Node_002",
        "node:3": "Node_003",
        "node:4": "Node_004",
    }
    assert BROKEN_PATH.read_bytes() == source_before
    assert inspection.package.file_sha256 == sha256(source_before).hexdigest()


def test_clean_fixture_has_no_false_severe_or_automatic_findings() -> None:
    """The clean robot passes project rules without severe or auto-safe noise."""
    inspection = inspect_asset(CLEAN_PATH, _profile())
    assert inspection.repair_eligibility is RepairEligibility.ELIGIBLE_STATIC_MESH
    assert not [
        finding
        for finding in inspection.findings
        if finding.severity in {Severity.ERROR, Severity.BLOCKER}
        or finding.action_class is ActionClass.AUTO_SAFE
    ]
    assert inspection.geometry is not None
    assert inspection.geometry.dominant_dimension_axis == "Y"
    assert inspection.geometry.ground_relationship == "GROUNDED"
    assert inspection.diagnostics is not None
    assert all(not item.attribute_count_mismatches for item in inspection.diagnostics.primitives)
    assert all(item.non_finite_position_count == 0 for item in inspection.diagnostics.primitives)
    assert all(item.out_of_range_index_count == 0 for item in inspection.diagnostics.primitives)


def test_repeated_inspection_and_cli_artifacts_are_deterministic(tmp_path: Path) -> None:
    """Repeated inspection produces byte-identical JSON and report artifacts."""
    first = inspect_asset(BROKEN_PATH, _profile())
    second = inspect_asset(BROKEN_PATH, _profile())
    assert first.model_dump_json() == second.model_dump_json()
    assert render_inspection_report(first) == render_inspection_report(second)

    first_output = tmp_path / "first"
    second_output = tmp_path / "second"
    first_exit = run_cli(
        [
            "inspect",
            str(BROKEN_PATH),
            "--profile",
            str(PROFILE_PATH),
            "--output",
            str(first_output),
        ]
    )
    second_exit = run_cli(
        [
            "inspect",
            str(BROKEN_PATH),
            "--profile",
            str(PROFILE_PATH),
            "--output",
            str(second_output),
        ]
    )
    assert first_exit == second_exit == 0
    assert (first_output / "inspection.json").read_bytes() == (
        second_output / "inspection.json"
    ).read_bytes()
    assert (first_output / "report.md").read_bytes() == (second_output / "report.md").read_bytes()


def test_invalid_file_fails_closed_with_diagnostics(tmp_path: Path) -> None:
    """Invalid input is classified as unreadable rather than repairable."""
    invalid_path = tmp_path / "invalid.glb"
    invalid_path.write_bytes(b"not a GLB")
    inspection = inspect_asset(invalid_path, _profile())
    assert inspection.repair_eligibility is RepairEligibility.INVALID_OR_UNREADABLE
    assert not inspection.package.parse_success
    assert inspection.geometry is None
    assert len(inspection.findings) == 1
    assert inspection.findings[0].severity is Severity.BLOCKER
    assert inspection.findings[0].action_class is ActionClass.BLOCKED
    assert inspection.findings[0].basis is CheckBasis.UNIVERSAL_INVARIANT


def test_skin_presence_allows_inspection_but_blocks_repair(tmp_path: Path) -> None:
    """Unsupported structural features produce inspection-only eligibility."""
    skinned_path = tmp_path / "skinned.glb"
    gltf = load_glb(CLEAN_PATH)
    gltf.skins.append(Skin(name="UnsupportedSkin", joints=[]))
    save_glb(gltf, skinned_path)
    inspection = inspect_asset(skinned_path, _profile())
    assert inspection.package.parse_success
    assert inspection.geometry is not None
    assert inspection.repair_eligibility is RepairEligibility.INSPECTION_ONLY_UNSUPPORTED_FEATURES
    blocker = next(
        finding for finding in inspection.findings if finding.code == "UNSUPPORTED_REPAIR_FEATURES"
    )
    assert blocker.severity is Severity.BLOCKER
    assert blocker.action_class is ActionClass.BLOCKED
    assert blocker.basis is CheckBasis.UNIVERSAL_INVARIANT


def test_findings_distinguish_intent_policy_from_universal_rules() -> None:
    """LLM/user-derived targets cite their source without controlling safety invariants."""
    resolution = resolve_policy_family(
        _profile(),
        description="A standing static robot character for an Unreal game.",
        target_use=AssetTargetUse.STATIC_GAME_ASSET,
        target_height_cm=180.0,
    )
    inspection = inspect_asset(
        BROKEN_PATH,
        resolution.profile,
        policy=resolution.provenance,
    )
    ruled_findings = tuple(
        finding for finding in inspection.findings if finding.profile_rule is not None
    )
    assert ruled_findings
    assert all(finding.basis is CheckBasis.FROZEN_PROJECT_POLICY for finding in ruled_findings)
    assert all(
        finding.rule_provenance is not None and finding.rule_provenance.sources
        for finding in ruled_findings
    )
    by_code = {finding.code: finding for finding in ruled_findings}
    height_sources = by_code["HEIGHT_OUT_OF_RANGE"].rule_provenance
    assert height_sources is not None
    assert height_sources.sources == {
        "expected_height_cm.target": "CONFIRMED_INTENT",
        "expected_height_cm.tolerance": "DERIVED_INTENT",
    }
    grounding_sources = by_code["NOT_GROUNDED"].rule_provenance
    assert grounding_sources is not None
    assert grounding_sources.sources == {
        "orientation.require_ground_contact": "DERIVED_INTENT",
        "orientation.ground_tolerance_cm": "DERIVED_INTENT",
    }


def test_attribute_count_mismatch_is_a_universal_blocker(tmp_path: Path) -> None:
    """Malformed attribute cardinality blocks repair regardless of project intent."""
    malformed_path = tmp_path / "malformed-attributes.glb"
    gltf = load_glb(CLEAN_PATH)
    normal_accessor_index = cast(int | None, gltf.meshes[0].primitives[0].attributes.NORMAL)
    assert normal_accessor_index is not None
    gltf.accessors[normal_accessor_index].count -= 1
    save_glb(gltf, malformed_path)

    inspection = inspect_asset(malformed_path, _profile())

    finding = next(
        item for item in inspection.findings if item.code == "MALFORMED_GEOMETRY_ATTRIBUTES"
    )
    assert finding.basis is CheckBasis.UNIVERSAL_INVARIANT
    assert finding.action_class is ActionClass.BLOCKED
    assert finding.rule_provenance is None
    assert inspection.repair_eligibility is RepairEligibility.INSPECTION_ONLY_UNSUPPORTED_FEATURES


def test_degenerate_triangle_is_an_objective_report_only_diagnostic(tmp_path: Path) -> None:
    """Source topology defects are measured but do not invent an unsupported repair."""
    degenerate_path = tmp_path / "degenerate.glb"
    gltf = load_glb(CLEAN_PATH)
    primitive = gltf.meshes[0].primitives[0]
    assert primitive.indices is not None
    accessor = gltf.accessors[primitive.indices]
    assert accessor.componentType == 5123
    assert accessor.bufferView is not None
    buffer_view = gltf.bufferViews[accessor.bufferView]
    offset = (buffer_view.byteOffset or 0) + (accessor.byteOffset or 0)
    blob = bytearray(gltf.binary_blob() or b"")
    blob[offset : offset + 6] = pack("<HHH", 0, 0, 0)
    gltf.set_binary_blob(bytes(blob))
    save_glb(gltf, degenerate_path)

    inspection = inspect_asset(degenerate_path, _profile())

    finding = next(
        item for item in inspection.findings if item.code == "DEGENERATE_TRIANGLES_DETECTED"
    )
    assert finding.basis is CheckBasis.OBJECTIVE_SOURCE_DIAGNOSTIC
    assert finding.action_class is ActionClass.REPORT_ONLY
    assert finding.rule_provenance is None
    assert inspection.repair_eligibility is RepairEligibility.ELIGIBLE_STATIC_MESH
