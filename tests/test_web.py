"""M8 acceptance tests for the local upload-to-download web product."""

# pygltflib is typed internally but does not publish PEP 561 metadata.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

import re
from pathlib import Path
from urllib.parse import urlparse
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from pygltflib import Skin

from asset_shepherd.glb import load_glb, save_glb
from asset_shepherd.models import (
    Decisions,
    DecisionValue,
    InspectionResult,
    ProjectProfile,
    Provenance,
)
from asset_shepherd.profile_policy import canonical_profile_sha256
from asset_shepherd.web import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BROKEN_PATH = PROJECT_ROOT / "fixtures" / "broken_robot.glb"
CLEAN_PATH = PROJECT_ROOT / "fixtures" / "clean_robot.glb"
PROFILE_ID = "unreal-indie-robot-v1"
STORY_EXPECTATIONS = (
    (
        "game-developer",
        "Is this asset ready for my game?",
        "Import-ready candidate",
        "Ready-to-import proof",
    ),
    ("artist", "What will change in my work?", "Verified delivery copy", "Preservation checks"),
    (
        "technical-artist",
        "Does this asset meet project policy?",
        "Verified artifact",
        "Invariant audit",
    ),
)
PACKAGE_NAMES = {
    "decisions.json",
    "inspection.json",
    "provenance.json",
    "repair_plan.json",
    "report.md",
    "repaired.glb",
    "verification.json",
}
CUSTOM_PROFILE_DATA = {
    "profile_mode": "custom",
    "custom_height_target_cm": "182",
    "custom_height_tolerance_cm": "1",
    "custom_require_y_up": "true",
    "custom_require_ground_contact": "true",
    "custom_ground_tolerance_cm": "1",
    "custom_naming_pattern": "^[A-Z][A-Za-z0-9_]*$",
    "custom_max_triangles": "100000",
    "custom_max_materials": "8",
    "custom_max_textures": "16",
    "custom_max_texture_dimension": "4096",
}


def _upload(
    client: TestClient,
    source: Path,
    profile_id: str = PROFILE_ID,
    story_slug: str = "game-developer",
    policy_data: dict[str, str] | None = None,
) -> str:
    """Upload one fixture and return its redirected local job path."""
    response = client.post(
        f"/stories/{story_slug}/jobs",
        data={"profile_id": profile_id, **(policy_data or {})},
        files={"asset": (source.name, source.read_bytes(), "model/gltf-binary")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    location = response.headers["location"]
    return urlparse(location).path


def _interrupt_id(html: str) -> str:
    """Extract the opaque interrupt ID emitted into the exact decision form."""
    match = re.search(r'name="interrupt_id" value="([^"]+)"', html)
    assert match is not None
    return match.group(1)


def _assert_focus_area_budget(html: str, expected: int) -> None:
    """Keep every visible state inside the user-mandated three-area attention budget."""
    focus_areas = re.findall(r'data-focus-area="([^"]+)"', html)
    assert len(focus_areas) == expected, focus_areas
    assert len(focus_areas) <= 3


def test_web_story_chooser_explains_three_equivalent_flows(tmp_path: Path) -> None:
    """The entry page asks one question and offers three concise role choices."""
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))
    response = client.get("/")

    assert response.status_code == 200
    assert "Which best describes you?" in response.text
    assert "No feature differences between concepts" not in response.text
    _assert_focus_area_budget(response.text, expected=2)
    for story_slug, _, _, _ in STORY_EXPECTATIONS:
        assert f"/stories/{story_slug}" in response.text


def test_web_profiles_are_versioned_presets_with_collapsed_rules_and_safe_customization(
    tmp_path: Path,
) -> None:
    """Preset summaries and advanced copies expose policy, not raw repair operations."""
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))
    response = client.get("/stories/game-developer")

    assert response.status_code == 200
    assert response.text.count("immutable preset v1") == 2
    assert response.text.count("Review rules") == 2
    assert "Target height" in response.text
    assert "Require Y-up geometry" in response.text
    assert "Name pattern" in response.text
    assert "Maximum triangles" in response.text
    assert "Approval for physical normalization" in response.text
    assert "Customize a copy" in response.text
    assert "supported target-state rules only" in response.text
    assert "Fixed safety boundary" in response.text
    assert "transform matrix" not in response.text.lower()
    _assert_focus_area_budget(response.text, expected=2)


@pytest.mark.parametrize(
    ("story_slug", "landing_question", "candidate_label", "verification_heading"),
    STORY_EXPECTATIONS,
)
def test_web_broken_fixture_flow_is_equivalent_for_each_story(
    tmp_path: Path,
    story_slug: str,
    landing_question: str,
    candidate_label: str,
    verification_heading: str,
) -> None:
    """A browser can refresh, approve by interrupt ID, preview, and download the result."""
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))
    landing = client.get(f"/stories/{story_slug}")
    assert landing.status_code == 200
    assert landing_question in landing.text
    assert f"/stories/{story_slug}/jobs" in landing.text
    assert "Inspect" in landing.text
    assert "Decide" in landing.text
    assert "Download" in landing.text
    assert "Both are required" in landing.text
    assert "Choose validation rules" in landing.text
    assert "This does not choose a model" in landing.text
    assert "Upload the GLB you want checked" in landing.text
    assert "Choose your GLB file" in landing.text
    assert "Project target" not in landing.text
    assert landing.text.count('name="profile_id"') == 2
    _assert_focus_area_budget(landing.text, expected=2)

    job_path = _upload(client, BROKEN_PATH, story_slug=story_slug)

    pending = client.get(job_path)
    assert pending.status_code == 200
    assert "Approval needed" in pending.text
    assert "Normalize physical scale, upright orientation, and grounding" in pending.text
    assert "Policy rule" in pending.text
    assert "Height target 180.0 cm ± 10.0 cm" in pending.text
    _assert_focus_area_budget(pending.text, expected=3)
    interrupt_id = _interrupt_id(pending.text)
    pending_output = tmp_path / "jobs" / job_path.rsplit("/", 1)[-1] / "output"
    inspection = InspectionResult.model_validate_json(
        (pending_output / "inspection.json").read_text(encoding="utf-8")
    )
    ruled_findings = tuple(
        finding for finding in inspection.findings if finding.profile_rule is not None
    )
    assert ruled_findings
    assert all(finding.rule_provenance is not None for finding in ruled_findings)
    assert all(
        finding.rule_provenance is not None and finding.rule_provenance.profile_id == PROFILE_ID
        for finding in ruled_findings
    )
    assert not (pending_output / "candidate.glb").exists()

    refreshed = client.get(job_path)
    assert refreshed.status_code == 200
    assert _interrupt_id(refreshed.text) == interrupt_id
    source_response = client.get(f"{job_path}/source.glb")
    assert source_response.status_code == 200
    assert source_response.content == BROKEN_PATH.read_bytes()

    decision = client.post(
        f"{job_path}/decision",
        data={"interrupt_id": interrupt_id, "decision": "approve"},
        follow_redirects=False,
    )
    assert decision.status_code == 303
    completed = client.get(job_path)
    assert completed.status_code == 200
    assert candidate_label in completed.text
    assert verification_heading in completed.text
    assert "PASSED_WITH_REMAINING_WARNINGS" in completed.text
    assert "Download result ZIP" in completed.text
    _assert_focus_area_budget(completed.text, expected=3)
    assert client.get(f"{job_path}/repaired.glb").status_code == 200

    archive_response = client.get(f"{job_path}/download")
    assert archive_response.status_code == 200
    archive_path = tmp_path / "result.zip"
    archive_path.write_bytes(archive_response.content)
    with ZipFile(archive_path) as archive:
        assert set(archive.namelist()) == PACKAGE_NAMES

    job_id = job_path.rsplit("/", 1)[-1]
    decisions = Decisions.model_validate_json(
        (tmp_path / "jobs" / job_id / "output" / "decisions.json").read_text(encoding="utf-8")
    )
    normalization = next(
        record for record in decisions.records if record.candidate_id == "normalize-root-v1"
    )
    assert normalization.decision is DecisionValue.APPROVED
    assert normalization.interrupt_id == interrupt_id
    provenance = Provenance.model_validate_json(
        (pending_output / "provenance.json").read_text(encoding="utf-8")
    )
    assert provenance.profile_policy is not None
    assert provenance.profile_policy.frozen_profile_id == PROFILE_ID
    assert provenance.profile_policy.base_preset_id == PROFILE_ID
    assert provenance.profile_policy.explicit_overrides == {}
    assert re.fullmatch(r"[0-9a-f]{64}", provenance.profile_policy.canonical_sha256)


def test_web_custom_profile_is_validated_frozen_and_recorded_without_mutating_preset(
    tmp_path: Path,
) -> None:
    """A supported custom copy gets an immutable job snapshot and complete provenance."""
    preset_path = PROJECT_ROOT / "profiles" / "unreal_indie_robot.json"
    preset_before = preset_path.read_bytes()
    work_root = tmp_path / "jobs"
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))

    job_path = _upload(
        client,
        CLEAN_PATH,
        story_slug="technical-artist",
        policy_data=CUSTOM_PROFILE_DATA,
    )
    completed = client.get(job_path)
    assert completed.status_code == 200
    assert "PASSED_PROJECT_READY" in completed.text
    assert "Approval needed" not in completed.text
    assert "custom copy" in completed.text

    job_root = work_root / job_path.rsplit("/", 1)[-1]
    frozen_profile = ProjectProfile.model_validate_json(
        (job_root / "profile.json").read_text(encoding="utf-8")
    )
    provenance = Provenance.model_validate_json(
        (job_root / "output" / "provenance.json").read_text(encoding="utf-8")
    )
    assert frozen_profile.profile_id.startswith(f"{PROFILE_ID}-custom-")
    assert provenance.profile_id == frozen_profile.profile_id
    assert provenance.profile_policy is not None
    assert provenance.profile_policy.frozen_profile_id == frozen_profile.profile_id
    assert provenance.profile_policy.base_preset_id == PROFILE_ID
    assert provenance.profile_policy.profile_version == 1
    assert provenance.profile_policy.explicit_overrides == {
        "expected_height_cm.target": 182.0,
        "expected_height_cm.tolerance": 1.0,
    }
    assert provenance.profile_policy.canonical_sha256 == canonical_profile_sha256(frozen_profile)
    assert preset_path.read_bytes() == preset_before


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("custom_height_target_cm", "-1", "expected_height_cm.target"),
        ("custom_naming_pattern", "[", "naming pattern must use"),
        ("custom_max_texture_dimension", "0", "budgets.max_texture_dimension"),
    ),
)
def test_web_rejects_invalid_custom_profile_before_creating_job(
    tmp_path: Path,
    field: str,
    value: str,
    message: str,
) -> None:
    """Server-side ProjectProfile validation fails closed before upload isolation."""
    work_root = tmp_path / "jobs"
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))
    policy_data = {**CUSTOM_PROFILE_DATA, field: value}

    response = client.post(
        "/stories/game-developer/jobs",
        data={"profile_id": PROFILE_ID, **policy_data},
        files={"asset": (CLEAN_PATH.name, CLEAN_PATH.read_bytes(), "model/gltf-binary")},
    )

    assert response.status_code == 400
    assert message in response.text
    assert not work_root.exists() or not tuple(work_root.iterdir())


def test_web_rule_change_after_upload_creates_a_distinct_job_and_inspection(
    tmp_path: Path,
) -> None:
    """A frozen job is never reinterpreted when the user submits different rules."""
    work_root = tmp_path / "jobs"
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))
    first_path = _upload(client, CLEAN_PATH, policy_data=CUSTOM_PROFILE_DATA)
    second_policy = {
        **CUSTOM_PROFILE_DATA,
        "custom_height_target_cm": "181",
        "custom_height_tolerance_cm": "2",
    }
    second_path = _upload(client, CLEAN_PATH, policy_data=second_policy)

    assert first_path != second_path
    first_root = work_root / first_path.rsplit("/", 1)[-1]
    second_root = work_root / second_path.rsplit("/", 1)[-1]
    first_inspection = InspectionResult.model_validate_json(
        (first_root / "output" / "inspection.json").read_text(encoding="utf-8")
    )
    second_inspection = InspectionResult.model_validate_json(
        (second_root / "output" / "inspection.json").read_text(encoding="utf-8")
    )
    assert first_inspection.profile_id != second_inspection.profile_id
    assert first_inspection.profile_id.startswith(f"{PROFILE_ID}-custom-")
    assert second_inspection.profile_id.startswith(f"{PROFILE_ID}-custom-")
    assert client.get(first_path).status_code == 200
    assert client.get(second_path).status_code == 200
    assert "changing rules starts a new inspection and job" in client.get(first_path).text


def test_web_clean_fixture_completes_twice_from_clean_app_starts(tmp_path: Path) -> None:
    """The clean no-approval path completes twice from independent application starts."""
    for run_number in range(2):
        work_root = tmp_path / f"clean-start-{run_number}"
        client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))
        job_path = _upload(client, CLEAN_PATH, story_slug="artist")
        completed = client.get(job_path)
        assert completed.status_code == 200
        assert "No project-policy findings." in completed.text
        assert "Verified delivery copy" in completed.text
        assert "Approval needed" not in completed.text
        assert "PASSED_PROJECT_READY" in completed.text
        _assert_focus_area_budget(completed.text, expected=3)
        assert client.get(f"{job_path}/download").status_code == 200


def test_web_rejects_non_glb_upload_without_starting_a_job(tmp_path: Path) -> None:
    """Invalid browser input gets a coherent intake error and no retained job."""
    work_root = tmp_path / "jobs"
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))
    response = client.post(
        "/stories/technical-artist/jobs",
        data={"profile_id": PROFILE_ID},
        files={"asset": ("not-a-model.glb", b"not a GLB", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "The upload is not a GLB 2.0 binary container." in response.text
    assert "Does this asset meet project policy?" in response.text
    _assert_focus_area_budget(response.text, expected=2)
    assert not work_root.exists() or not tuple(work_root.iterdir())


def test_web_packages_unsupported_asset_as_inspection_only(tmp_path: Path) -> None:
    """Unsupported structural content is blocked and packaged without a repaired GLB."""
    skinned_path = tmp_path / "skinned.glb"
    gltf = load_glb(CLEAN_PATH)
    gltf.skins.append(Skin(name="UnsupportedSkin", joints=[]))
    save_glb(gltf, skinned_path)
    source_before = skinned_path.read_bytes()

    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))
    job_path = _upload(client, skinned_path, story_slug="technical-artist")
    blocked = client.get(job_path)
    assert blocked.status_code == 200
    assert "Inspection-only result" in blocked.text
    assert "INSPECTION_ONLY_UNSUPPORTED_FEATURES" in blocked.text
    assert "UNSUPPORTED_REPAIR_FEATURES" in blocked.text
    _assert_focus_area_budget(blocked.text, expected=3)
    assert client.get(f"{job_path}/repaired.glb").status_code == 404
    assert skinned_path.read_bytes() == source_before

    archive_response = client.get(f"{job_path}/download")
    assert archive_response.status_code == 200
    archive_path = tmp_path / "blocked-result.zip"
    archive_path.write_bytes(archive_response.content)
    with ZipFile(archive_path) as archive:
        assert set(archive.namelist()) == PACKAGE_NAMES - {"repaired.glb"}
