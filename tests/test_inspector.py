"""M4 acceptance tests for deterministic GLB inspection."""

# pygltflib is typed internally but does not publish PEP 561 metadata.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from hashlib import sha256
from pathlib import Path

from pygltflib import Skin

from asset_shepherd.cli import run_cli
from asset_shepherd.glb import load_glb, save_glb
from asset_shepherd.inspector import inspect_asset, render_inspection_report
from asset_shepherd.models import (
    ActionClass,
    FixtureManifest,
    ProjectProfile,
    RepairEligibility,
    Severity,
)

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
