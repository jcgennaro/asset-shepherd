"""M3 acceptance tests for typed schemas and deterministic fixtures."""

# pygltflib and parts of Trimesh do not publish complete PEP 561 metadata.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

import json
from pathlib import Path

import numpy as np
import pytest
import trimesh
from jsonschema import Draft202012Validator

from asset_shepherd.fixtures import generate_fixtures, generate_geometry_failure_fixtures
from asset_shepherd.glb import geometry_counts, load_glb, validate_loaded_glb, world_bounds
from asset_shepherd.inspector import inspect_asset
from asset_shepherd.models import FixtureManifest, ProjectProfile, RepairEligibility
from asset_shepherd.schema_export import SCHEMA_MODELS, export_schemas

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_exported_schemas_are_current_and_valid(tmp_path: Path) -> None:
    """Checked-in schemas reproduce exactly and conform to Draft 2020-12."""
    generated = export_schemas(tmp_path)
    assert {path.name for path in generated} == set(SCHEMA_MODELS)
    for generated_path in generated:
        checked_in = PROJECT_ROOT / "schemas" / generated_path.name
        assert generated_path.read_bytes() == checked_in.read_bytes()
        schema = json.loads(generated_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)


def test_fixture_artifacts_regenerate_byte_for_byte(tmp_path: Path) -> None:
    """A clean checkout can reproduce every fixture artifact exactly."""
    fixture_dir = tmp_path / "fixtures"
    profile_dir = tmp_path / "profiles"
    generated = generate_fixtures(fixture_dir, profile_dir)
    for generated_path in generated:
        relative_root = "profiles" if generated_path.parent == profile_dir else "fixtures"
        checked_in = PROJECT_ROOT / relative_root / generated_path.name
        assert generated_path.read_bytes() == checked_in.read_bytes()


def test_geometry_failure_fixtures_regenerate_byte_for_byte(tmp_path: Path) -> None:
    """Parseable geometry-failure examples remain deterministic and documented."""
    generated = generate_geometry_failure_fixtures(
        PROJECT_ROOT / "fixtures" / "clean_robot.glb",
        tmp_path / "geometry_failures",
    )
    for generated_path in generated:
        checked_in = PROJECT_ROOT / "fixtures" / "geometry_failures" / generated_path.name
        assert generated_path.read_bytes() == checked_in.read_bytes()


@pytest.mark.parametrize(
    ("fixture_name", "expected_code", "expected_eligibility"),
    [
        (
            "degenerate_triangle.glb",
            "DEGENERATE_TRIANGLES_DETECTED",
            RepairEligibility.ELIGIBLE_STATIC_MESH,
        ),
        (
            "malformed_attributes.glb",
            "MALFORMED_GEOMETRY_ATTRIBUTES",
            RepairEligibility.INSPECTION_ONLY_UNSUPPORTED_FEATURES,
        ),
    ],
)
def test_geometry_failure_fixtures_exercise_distinct_outcomes(
    fixture_name: str,
    expected_code: str,
    expected_eligibility: RepairEligibility,
) -> None:
    """One geometry defect is report-only while malformed attributes block repair."""
    inspection = inspect_asset(
        PROJECT_ROOT / "fixtures" / "geometry_failures" / fixture_name,
        ProjectProfile.model_validate_json(
            (PROJECT_ROOT / "profiles" / "unreal_indie_robot.json").read_text(encoding="utf-8")
        ),
    )
    assert expected_code in {finding.code for finding in inspection.findings}
    assert inspection.repair_eligibility is expected_eligibility


@pytest.mark.parametrize(
    ("fixture_dir", "fixture_id"),
    [
        ("fixtures", "clean_robot"),
        ("fixtures", "broken_robot"),
        ("fixtures/geometry_failures", "degenerate_triangle"),
        ("fixtures/geometry_failures", "malformed_attributes"),
    ],
)
def test_fixture_json_validates_against_models_and_schemas(
    fixture_dir: str, fixture_id: str
) -> None:
    """Generated profiles and manifests validate as models and public JSON Schema."""
    profile_json = (PROJECT_ROOT / "profiles" / "unreal_indie_robot.json").read_text(
        encoding="utf-8"
    )
    manifest_json = (PROJECT_ROOT / fixture_dir / f"{fixture_id}.expected.json").read_text(
        encoding="utf-8"
    )
    profile_data = json.loads(profile_json)
    manifest_data = json.loads(manifest_json)
    ProjectProfile.model_validate_json(profile_json)
    FixtureManifest.model_validate_json(manifest_json)
    profile_schema = json.loads(
        (PROJECT_ROOT / "schemas" / "profile.schema.json").read_text(encoding="utf-8")
    )
    manifest_schema = json.loads(
        (PROJECT_ROOT / "schemas" / "fixture_manifest.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(profile_schema).validate(profile_data)
    Draft202012Validator(manifest_schema).validate(manifest_data)


def test_clean_and_broken_fixtures_have_contracted_geometry() -> None:
    """Fixtures are valid, original, visually distinct, and encode known defects."""
    clean_path = PROJECT_ROOT / "fixtures" / "clean_robot.glb"
    broken_path = PROJECT_ROOT / "fixtures" / "broken_robot.glb"
    clean = load_glb(clean_path)
    broken = load_glb(broken_path)
    validate_loaded_glb(clean)
    validate_loaded_glb(broken)

    clean_manifest = FixtureManifest.model_validate_json(
        (PROJECT_ROOT / "fixtures" / "clean_robot.expected.json").read_text(encoding="utf-8")
    )
    broken_manifest = FixtureManifest.model_validate_json(
        (PROJECT_ROOT / "fixtures" / "broken_robot.expected.json").read_text(encoding="utf-8")
    )
    clean_bounds = world_bounds(clean)
    broken_bounds = world_bounds(broken)
    assert geometry_counts(clean).vertices == clean_manifest.expected_vertex_count
    assert geometry_counts(clean).triangles == clean_manifest.expected_triangle_count
    assert geometry_counts(broken) == geometry_counts(clean)
    assert clean_manifest.original_asset and broken_manifest.original_asset
    assert clean_manifest.expected_defect_codes == ()
    assert broken_manifest.expected_defect_codes
    assert np.argmax(clean_bounds.dimensions) == 1
    assert np.argmax(broken_bounds.dimensions) == 0
    assert clean_bounds.minimum[1] == pytest.approx(0.0, abs=1e-7)
    assert clean_bounds.dimensions[1] == pytest.approx(1.82, abs=1e-5)
    assert broken_bounds.dimensions[0] / clean_bounds.dimensions[1] == pytest.approx(100.0)
    assert broken_bounds.minimum[1] > 1.0
    assert len(clean.materials) == 4
    assert len(broken.materials) == 9
    assert broken.nodes[1].name == broken.nodes[2].name
    assert broken.nodes[3].name is None
    assert broken.meshes[0].name == broken.meshes[1].name
    assert broken.meshes[2].name is None

    clean_scene = trimesh.load_scene(clean_path, process=False)
    broken_scene = trimesh.load_scene(broken_path, process=False)
    assert clean_scene.bounds is not None
    assert broken_scene.bounds is not None
    np.testing.assert_allclose(clean_scene.bounds, [clean_bounds.minimum, clean_bounds.maximum])
    np.testing.assert_allclose(broken_scene.bounds, [broken_bounds.minimum, broken_bounds.maximum])
