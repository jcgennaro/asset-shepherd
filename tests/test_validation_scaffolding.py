"""RW0 acceptance tests for real-world corpus schemas and raw registration."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from asset_shepherd.inspector import inspect_asset
from asset_shepherd.models import ProjectProfile
from asset_shepherd.validation.models import (
    Adjudication,
    AssetProvenance,
    MutationManifest,
)
from asset_shepherd.validation.mutations import create_controlled_variant
from asset_shepherd.validation.register import RegistrationError, hash_file, register_raw_asset
from asset_shepherd.validation.report import render_validation_report
from asset_shepherd.validation.schema_export import (
    VALIDATION_SCHEMA_MODELS,
    export_validation_schemas,
)
from spike.test_glb_capability import make_spike_glb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PATCHLING_ROOT = PROJECT_ROOT / "validation" / "corpus" / "patchling_01"
SHADER_LANTERN_ROOT = PROJECT_ROOT / "validation" / "corpus" / "shader_lantern_01"


def test_validation_schemas_are_current_and_draft_2020_12(tmp_path: Path) -> None:
    """Checked-in addendum schemas regenerate exactly and validate structurally."""
    generated = export_validation_schemas(tmp_path)
    assert {path.name for path in generated} == set(VALIDATION_SCHEMA_MODELS)
    for generated_path in generated:
        checked_in = PROJECT_ROOT / "validation" / "schemas" / generated_path.name
        assert generated_path.read_bytes() == checked_in.read_bytes()
        Draft202012Validator.check_schema(json.loads(generated_path.read_text(encoding="utf-8")))


def test_patchling_registration_is_typed_and_prompt_is_frozen() -> None:
    """The registered Patchling record remains typed and keeps the approved prompt."""
    provenance = AssetProvenance.model_validate_json(
        (PATCHLING_ROOT / "provenance.json").read_text(encoding="utf-8")
    )
    Adjudication.model_validate_json(
        (PATCHLING_ROOT / "observed_real_world" / "adjudication.json").read_text(encoding="utf-8")
    )
    card = (PATCHLING_ROOT / "generation-card.md").read_text(encoding="utf-8")
    prompt_record = (PATCHLING_ROOT / "prompt.md").read_text(encoding="utf-8")
    assert provenance.asset_id == "patchling_01"
    assert provenance.prompt in card
    assert provenance.prompt in prompt_record
    assert len(provenance.raw_sha256) == 64
    assert provenance.public_use_confirmed
    assert provenance.registration_errors() == ()
    raw_asset = PATCHLING_ROOT / "raw" / "asset.glb"
    assert raw_asset.stat().st_size == 4_860_944
    assert hash_file(raw_asset) == provenance.raw_sha256
    assert (
        provenance.generation_settings["workspace_item_id"]
        == "853e8986-e0e3-4d8e-a977-439ac9155787"
    )


def test_shader_lantern_registration_and_approved_result_are_frozen() -> None:
    """The registered Lantern keeps its blind plan and approved verified outcome."""
    provenance = AssetProvenance.model_validate_json(
        (SHADER_LANTERN_ROOT / "provenance.json").read_text(encoding="utf-8")
    )
    adjudication = Adjudication.model_validate_json(
        (SHADER_LANTERN_ROOT / "observed_real_world" / "adjudication.json").read_text(
            encoding="utf-8"
        )
    )
    card = (SHADER_LANTERN_ROOT / "generation-card.md").read_text(encoding="utf-8")
    prompt_record = (SHADER_LANTERN_ROOT / "prompt.md").read_text(encoding="utf-8")
    assert provenance.asset_id == adjudication.asset_id == "shader_lantern_01"
    assert provenance.prompt in card
    assert provenance.prompt in prompt_record
    assert provenance.registration_errors() == ()
    assert provenance.public_use_confirmed
    raw_asset = SHADER_LANTERN_ROOT / "raw" / "asset.glb"
    assert raw_asset.stat().st_size == 12_813_168
    assert hash_file(raw_asset) == provenance.raw_sha256
    plan = json.loads(
        (SHADER_LANTERN_ROOT / "blind_asset_shepherd" / "repair_plan.json").read_text(
            encoding="utf-8"
        )
    )
    assert plan["source_sha256"] == provenance.raw_sha256
    assert plan["approval_action_ids"] == ["normalize-root-v1"]
    assert [candidate["id"] for candidate in plan["candidates"]] == [
        "rename-mesh-000",
        "rename-node-001",
        "normalize-root-v1",
    ]
    decisions = json.loads(
        (SHADER_LANTERN_ROOT / "blind_asset_shepherd" / "decisions.json").read_text(
            encoding="utf-8"
        )
    )
    assert [record["decision"] for record in decisions["records"]] == [
        "AUTO_AUTHORIZED",
        "AUTO_AUTHORIZED",
        "APPROVED",
    ]
    verification = json.loads(
        (SHADER_LANTERN_ROOT / "blind_asset_shepherd" / "verification.json").read_text(
            encoding="utf-8"
        )
    )
    assert verification["state"] == "PASSED_WITH_REMAINING_WARNINGS"
    assert verification["remaining_warnings"] == [
        "TRIANGLE_BUDGET_EXCEEDED: Triangle budget exceeded"
    ]


def test_small_stylized_profile_matches_addendum_height_range() -> None:
    """The general compact-asset profile expresses the contracted 0.9-1.5 m range."""
    profile = ProjectProfile.model_validate_json(
        (PROJECT_ROOT / "validation" / "profiles" / "small_stylized_static_mesh.json").read_text(
            encoding="utf-8"
        )
    )
    assert profile.profile_id == "small-stylized-static-mesh-v1"
    assert profile.expected_height_cm.target - profile.expected_height_cm.tolerance == 90.0
    assert profile.expected_height_cm.target + profile.expected_height_cm.tolerance == 150.0


def test_blender_evidence_script_is_valid_python() -> None:
    """The Blender-owned script is syntax checked without importing unavailable bpy."""
    blender_root = PROJECT_ROOT / "validation" / "blender"
    for filename in ("inspect_glb.py", "render_turntable.py"):
        script = blender_root / filename
        compile(script.read_text(encoding="utf-8"), str(script), "exec")
    turntable = (blender_root / "render_turntable.py").read_text(encoding="utf-8")
    assert '"front": Vector((0.0, -1.0, 0.0))' in turntable
    assert '"right": Vector((-1.0, 0.0, 0.0))' in turntable
    assert '"back": Vector((0.0, 1.0, 0.0))' in turntable
    assert '"left": Vector((1.0, 0.0, 0.0))' in turntable
    assert 'camera.data.type = "ORTHO"' in turntable
    assert "camera.data.ortho_scale = max(projected_width, projected_height" in turntable


def test_unreal_harness_is_syntax_checked_and_isolated() -> None:
    """Unreal-owned scripts compile and the project enables only validation plugins."""
    unreal_root = PROJECT_ROOT / "validation" / "unreal"
    for filename in ("setup_validation_project.py", "import_compare.py"):
        script = unreal_root / filename
        compile(script.read_text(encoding="utf-8"), str(script), "exec")
    project = json.loads(
        (unreal_root / "AssetShepherdValidation.uproject").read_text(encoding="utf-8")
    )
    assert project["EngineAssociation"] == "5.8"
    assert {plugin["Name"] for plugin in project["Plugins"]} == {
        "InterchangeEditor",
        "PythonScriptPlugin",
    }
    engine_config = (unreal_root / "Config" / "DefaultEngine.ini").read_text(encoding="utf-8")
    assert "DefaultGraphicsRHI=DefaultGraphicsRHI_DX12" in engine_config
    assert "+D3D12TargetedShaderFormats=PCD3D_SM6" in engine_config
    assert "SecurityToken" not in engine_config


def test_report_renderer_marks_missing_evidence_without_inventing_claims() -> None:
    """Draft records render explicit unknowns and the required case-study boundary."""
    registered = AssetProvenance.model_validate_json(
        (PATCHLING_ROOT / "provenance.json").read_text(encoding="utf-8")
    )
    provenance = registered.model_copy(
        update={
            "generation_date_utc": None,
            "model_or_mode": "",
            "raw_sha256": "",
            "selected_candidate_reason": "",
            "public_use_confirmed": False,
        }
    )
    recorded_adjudication = Adjudication.model_validate_json(
        (PATCHLING_ROOT / "observed_real_world" / "adjudication.json").read_text(encoding="utf-8")
    )
    adjudication = recorded_adjudication.model_copy(update={"visual_fidelity_assessment": ""})
    report = render_validation_report(provenance, adjudication)
    assert "Raw SHA-256: `NOT_REGISTERED`" in report
    assert "Model or mode: NOT_RECORDED" in report
    assert "REQUIRES_HUMAN_ADJUDICATION" in report
    assert "Unsafe automatic repairs: 0" in report
    assert "not an industry-wide accuracy claim" in report


def test_registration_refuses_incomplete_human_provenance(tmp_path: Path) -> None:
    """Blind registration cannot proceed before rights and generation facts are recorded."""
    asset = tmp_path / "asset.glb"
    asset.write_bytes((PROJECT_ROOT / "fixtures" / "clean_robot.glb").read_bytes())
    registered = AssetProvenance.model_validate_json(
        (PATCHLING_ROOT / "provenance.json").read_text(encoding="utf-8")
    )
    incomplete = registered.model_copy(
        update={
            "generation_date_utc": None,
            "model_or_mode": "",
            "raw_sha256": "",
            "selected_candidate_reason": "",
            "public_use_confirmed": False,
        }
    )
    provenance = tmp_path / "provenance.json"
    provenance.write_text(
        f"{json.dumps(incomplete.model_dump(mode='json'), indent=2, sort_keys=True)}\n",
        encoding="utf-8",
    )
    source_before = asset.read_bytes()
    with pytest.raises(RegistrationError, match="Provenance is incomplete"):
        register_raw_asset(asset, provenance)
    assert asset.read_bytes() == source_before


def test_registration_hashes_valid_glb_without_mutating_raw(tmp_path: Path) -> None:
    """Complete human facts allow structural validation and immutable SHA registration."""
    asset = tmp_path / "asset.glb"
    asset.write_bytes((PROJECT_ROOT / "fixtures" / "clean_robot.glb").read_bytes())
    draft = AssetProvenance.model_validate_json(
        (PATCHLING_ROOT / "provenance.json").read_text(encoding="utf-8")
    )
    complete = draft.model_copy(
        update={
            "generation_date_utc": datetime(2026, 8, 21, 22, 0, tzinfo=UTC),
            "model_or_mode": "test-mode",
            "raw_sha256": "",
            "selected_candidate_reason": "Test fixture for registration behavior.",
            "public_use_confirmed": True,
        }
    )
    provenance = tmp_path / "provenance.json"
    provenance.write_text(
        f"{json.dumps(complete.model_dump(mode='json'), indent=2, sort_keys=True)}\n",
        encoding="utf-8",
    )
    source_before = asset.read_bytes()
    registered = register_raw_asset(asset, provenance)
    assert registered.raw_sha256 == hash_file(asset)
    assert asset.read_bytes() == source_before
    assert AssetProvenance.model_validate_json(provenance.read_text(encoding="utf-8")) == registered


@pytest.mark.parametrize(
    ("variant", "required_codes"),
    [
        (
            "normalization_chaos",
            {
                "HEIGHT_OUT_OF_RANGE",
                "ORIENTATION_NOT_Y_UP",
                "NOT_GROUNDED",
                "NODE_NAME_INVALID",
            },
        ),
        ("hierarchy_trap", {"NEGATIVE_DETERMINANT_TRANSFORM"}),
    ],
)
def test_controlled_mutation_is_manifested_and_independently_detected(
    tmp_path: Path,
    variant: str,
    required_codes: set[str],
) -> None:
    """Mutations preserve the source and geometry while inspection confirms defects."""
    source = PROJECT_ROOT / "fixtures" / "clean_robot.glb"
    source_hash = hash_file(source)
    output = tmp_path / f"{variant}.glb"
    manifest_path = tmp_path / f"{variant}.json"
    created = create_controlled_variant(
        source,
        output,
        manifest_path,
        base_asset_id="clean_robot",
        variant=variant,
        created_at=datetime(2026, 8, 21, 22, 0, tzinfo=UTC),
    )
    checked_in_schema = json.loads(
        (PROJECT_ROOT / "validation" / "schemas" / "mutation_manifest.schema.json").read_text(
            encoding="utf-8"
        )
    )
    stored = MutationManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    Draft202012Validator(checked_in_schema).validate(  # pyright: ignore[reportUnknownMemberType]
        stored.model_dump(mode="json")
    )
    profile = ProjectProfile.model_validate_json(
        (PROJECT_ROOT / "profiles" / "unreal_indie_robot.json").read_text(encoding="utf-8")
    )
    actual_codes = {finding.code for finding in inspect_asset(output, profile).findings}
    expected_codes = {
        code for operation in stored.operations for code in operation.expected_finding_codes
    }
    assert stored == created
    assert required_codes <= expected_codes <= actual_codes
    assert stored.source_sha256 == source_hash == hash_file(source)
    assert stored.source_unchanged_verified
    assert stored.variant_parse_verified
    assert stored.geometry_preserved
    assert stored.materials_preserved
    assert stored.textures_preserved


def test_material_texture_bloat_preserves_embedded_source_resources(tmp_path: Path) -> None:
    """The resource-budget variant adds records without changing source texture data."""
    source = tmp_path / "textured_source.glb"
    make_spike_glb(source)
    source_hash = hash_file(source)
    output = tmp_path / "material_texture_bloat.glb"
    manifest_path = tmp_path / "material_texture_bloat.json"
    manifest = create_controlled_variant(
        source,
        output,
        manifest_path,
        base_asset_id="textured_source",
        variant="material_texture_bloat",
        created_at=datetime(2026, 8, 21, 22, 0, tzinfo=UTC),
    )
    profile = ProjectProfile.model_validate_json(
        (PROJECT_ROOT / "profiles" / "unreal_indie_robot.json").read_text(encoding="utf-8")
    )
    actual_codes = {finding.code for finding in inspect_asset(output, profile).findings}
    assert {"MATERIAL_BUDGET_EXCEEDED", "TEXTURE_BUDGET_EXCEEDED"} <= actual_codes
    assert hash_file(source) == source_hash
    assert manifest.source_unchanged_verified
    assert manifest.geometry_preserved
    assert manifest.materials_preserved
    assert manifest.textures_preserved
    assert manifest.operations[0].affected_elements[0] == "material:1"
    assert manifest.operations[1].affected_elements[0] == "texture:1"
