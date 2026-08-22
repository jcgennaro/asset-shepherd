"""Acceptance tests for the local intent-to-download web product."""

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
from asset_shepherd.intake_analyzer import TargetIntakeInference, contract_from_inference
from asset_shepherd.intent import validate_asset_intent
from asset_shepherd.models import (
    AssetIntentProvenance,
    AssetTargetUse,
    Decisions,
    DecisionValue,
    InspectionResult,
    ProjectProfile,
    Provenance,
)
from asset_shepherd.profile_policy import canonical_profile_sha256
from asset_shepherd.target_intake import TargetIntakeContract
from asset_shepherd.web import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BROKEN_PATH = PROJECT_ROOT / "fixtures" / "broken_robot.glb"
CLEAN_PATH = PROJECT_ROOT / "fixtures" / "clean_robot.glb"
FAMILY_ID = "unreal-static-game-asset-family-v1"
DEFAULT_DESCRIPTION = (
    "A friendly humanoid robot for use as a static Unreal game asset with painted metal panels."
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
_USE_DESCRIPTION = {
    AssetTargetUse.STATIC_GAME_ASSET.value: "a static environment prop",
    AssetTargetUse.RIG_READY_CHARACTER.value: "a rig-ready character",
    AssetTargetUse.PLAYABLE_CHARACTER.value: "a playable character",
}


def _draft_intent(
    client: TestClient,
    *,
    description: str = DEFAULT_DESCRIPTION,
    target_use: str = AssetTargetUse.STATIC_GAME_ASSET.value,
    target_height_m: str = "1.8",
) -> str:
    """Create one target-story draft and return its review path."""
    complete_description = (
        f"{description} Intended result: {_USE_DESCRIPTION[target_use]} at "
        f"{target_height_m} m tall."
    )
    response = client.post(
        "/intents",
        data={"description": complete_description},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return urlparse(response.headers["location"]).path


def _agree_intent(client: TestClient, intent_path: str) -> str:
    """Confirm one reviewed target story and return its intake path."""
    response = client.post(f"{intent_path}/agree", follow_redirects=False)
    assert response.status_code == 303
    return urlparse(response.headers["location"]).path


def _confirmed_intent(
    client: TestClient,
    *,
    description: str = DEFAULT_DESCRIPTION,
    target_use: str = AssetTargetUse.STATIC_GAME_ASSET.value,
    target_height_m: str = "1.8",
) -> tuple[str, str]:
    """Draft and confirm one target story, returning ID and intake path."""
    intent_path = _draft_intent(
        client,
        description=description,
        target_use=target_use,
        target_height_m=target_height_m,
    )
    intake_path = _agree_intent(client, intent_path)
    return intent_path.rsplit("/", 1)[-1], intake_path


def _upload(
    client: TestClient,
    source: Path,
    *,
    policy_data: dict[str, str] | None = None,
    intent_id: str | None = None,
    target_height_m: str = "1.8",
) -> str:
    """Upload one fixture under a confirmed intent and return its job path."""
    if intent_id is None:
        intent_id, _ = _confirmed_intent(client, target_height_m=target_height_m)
    response = client.post(
        f"/intents/{intent_id}/jobs",
        data=policy_data or {},
        files={"asset": (source.name, source.read_bytes(), "model/gltf-binary")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return urlparse(response.headers["location"]).path


def _interrupt_id(html: str) -> str:
    """Extract the opaque interrupt ID emitted into the exact decision form."""
    match = re.search(r'name="interrupt_id" value="([^"]+)"', html)
    assert match is not None
    return match.group(1)


def _assert_focus_area_budget(html: str, expected: int = 1) -> None:
    """Keep every rendered state inside the one-step attention budget."""
    focus_areas = re.findall(r'data-focus-area="([^"]+)"', html)
    assert len(focus_areas) == expected, focus_areas
    assert len(focus_areas) <= 3


def test_web_starts_with_asset_intent_instead_of_an_audience_selector(tmp_path: Path) -> None:
    """The entry point asks for the user's target rather than their job title."""
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))
    response = client.get("/")

    assert response.status_code == 200
    assert "<title>Asset Shepherd -- Describe</title>" in response.text
    assert "What were you trying to make?" in response.text
    assert 'name="target_use"' not in response.text
    assert 'name="target_height_m"' not in response.text
    assert "propose the use and scale" in response.text
    assert "Propose a target" in response.text
    assert "Game developer" not in response.text
    assert "3D artist" not in response.text
    assert "Technical artist" not in response.text
    assert "Describe" in response.text
    assert "Agree" in response.text
    assert "Inspect" in response.text
    _assert_focus_area_budget(response.text)


def test_how_it_works_is_directly_below_new_asset_and_explains_the_flow(
    tmp_path: Path,
) -> None:
    """The persistent question-mark action opens one concise workflow explanation."""
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))

    entry = client.get("/workspace")
    assert entry.status_code == 200
    new_asset_position = entry.text.index(">New asset<")
    help_position = entry.text.index(">How it works<")
    assert new_asset_position < help_position
    assert 'class="help-icon" aria-hidden="true">?</span>' in entry.text
    assert 'href="http://testserver/how-it-works"' in entry.text

    help_page = client.get("/how-it-works")
    assert help_page.status_code == 200
    assert "<title>Asset Shepherd -- How it works</title>" in help_page.text
    assert "One asset in." in help_page.text
    assert "Describe the target" in help_page.text
    assert "Upload the untouched GLB" in help_page.text
    assert "Make one meaningful decision" in help_page.text
    assert "Download with proof" in help_page.text
    assert "Your original stays untouched" in help_page.text
    assert "What can Asset Shepherd repair?" in help_page.text
    _assert_focus_area_budget(help_page.text)


@pytest.mark.parametrize(
    ("height_cm", "expected_label"),
    ((0.5, "5 mm"), (2.0, "2 cm"), (120.0, "1.2 m"), (80000.0, "800 m")),
)
def test_confirmation_uses_a_readable_metric_unit_for_target_scale(
    tmp_path: Path,
    height_cm: float,
    expected_label: str,
) -> None:
    """Human-readable scale avoids tiny decimal meters on the public confirmation page."""

    class ScaleAnalyzer:
        provider = "openai"
        model_id = "gpt-5.6-luna"

        def analyze(self, description: str) -> TargetIntakeContract:
            return contract_from_inference(
                description,
                TargetIntakeInference(
                    target_use=AssetTargetUse.STATIC_GAME_ASSET,
                    target_use_confidence=0.96,
                    target_use_evidence="The description identifies a static prop.",
                    target_height_cm=height_cm,
                    target_height_confidence=0.91,
                    target_height_evidence="The description states the intended scale.",
                ),
                provider=self.provider,
                model_id=self.model_id,
            )

    client = TestClient(
        create_app(
            project_root=PROJECT_ROOT,
            work_root=tmp_path / "jobs",
            intake_analyzer=ScaleAnalyzer(),
        )
    )
    created = client.post(
        "/intents",
        data={"description": "A tiny bracelet with buttons used as a static game prop."},
        follow_redirects=False,
    )
    review = client.get(urlparse(created.headers["location"]).path)

    assert review.status_code == 200
    assert f"about {expected_label} tall" in review.text


def test_web_drafts_and_requires_explicit_target_story_agreement(tmp_path: Path) -> None:
    """No rules or upload control appears until the exact story is reviewed and agreed."""
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))
    intent_path = _draft_intent(
        client,
        description="A dark science-fiction armored woman with orange and teal emissive accents.",
        target_use=AssetTargetUse.PLAYABLE_CHARACTER.value,
        target_height_m="1.72",
    )

    review = client.get(intent_path)
    assert review.status_code == 200
    assert "treat this as a playable animated character, about 1.72 m tall." in review.text
    assert "Use this target" in review.text
    assert "rigging, skinning, and animation remain an external repair handoff" in review.text
    assert "Choose your GLB file" not in review.text
    assert "Review rules" not in review.text
    _assert_focus_area_budget(review.text)

    unconfirmed_intake = client.get(f"{intent_path}/intake", follow_redirects=False)
    assert unconfirmed_intake.status_code == 303
    assert urlparse(unconfirmed_intake.headers["location"]).path == intent_path

    intake_path = _agree_intent(client, intent_path)
    intake = client.get(intake_path)
    assert intake.status_code == 200
    assert "Agreed target" in intake.text
    assert "playable animated character for Unreal at 1.72 m tall" in intake.text
    assert "Review the rules I derived" in intake.text
    assert "Upload the GLB you want checked" in intake.text
    _assert_focus_area_budget(intake.text)


def test_web_validates_description_before_target_drafting(tmp_path: Path) -> None:
    """Invalid conversational input cannot create a target story or a job."""
    work_root = tmp_path / "jobs"
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))
    response = client.post("/intents", data={"description": "too short"})

    assert response.status_code == 400
    assert "at least 12 characters" in response.text
    assert not work_root.exists()


def test_web_asks_only_for_missing_target_fields_before_confirmation(tmp_path: Path) -> None:
    """Explicit use survives extraction while one absent height becomes the only question."""
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))
    created = client.post(
        "/intents",
        data={"description": "A hanging lantern used as a static environment prop in my game."},
        follow_redirects=False,
    )
    assert created.status_code == 303
    intent_path = urlparse(created.headers["location"]).path

    clarification = client.get(intent_path)
    assert clarification.status_code == 200
    assert "About how tall should it be?" in clarification.text
    assert "treating it as static game asset" in clarification.text
    assert "What real-world height should it have?" in clarification.text
    assert "What should this asset become?" not in clarification.text
    assert "Agree and continue" not in clarification.text

    invalid = client.post(
        f"{intent_path}/clarify",
        data={"target_height_m": "0"},
    )
    assert invalid.status_code == 400
    assert "greater than 0" in invalid.text

    completed = client.post(
        f"{intent_path}/clarify",
        data={"target_height_m": "1.2"},
        follow_redirects=False,
    )
    assert completed.status_code == 303
    review = client.get(intent_path)
    assert "treat this as a static game asset, about 1.2 m tall." in review.text


def test_semantic_intake_proposes_and_allows_adjustment_without_duplicate_questions(
    tmp_path: Path,
) -> None:
    """A model-backed ordinary prompt reaches one concise, user-adjustable confirmation."""

    class SemanticAnalyzer:
        provider = "openai"
        model_id = "gpt-5.6-luna"

        def analyze(self, description: str) -> TargetIntakeContract:
            return contract_from_inference(
                description,
                TargetIntakeInference(
                    target_use=AssetTargetUse.STATIC_GAME_ASSET,
                    target_use_confidence=0.96,
                    target_use_evidence="A mountain is an environmental feature.",
                    target_height_cm=80000.0,
                    target_height_confidence=0.91,
                    target_height_evidence="A mountain is a kilometer-scale feature.",
                ),
                provider=self.provider,
                model_id=self.model_id,
            )

    client = TestClient(
        create_app(
            project_root=PROJECT_ROOT,
            work_root=tmp_path / "jobs",
            intake_analyzer=SemanticAnalyzer(),
        )
    )
    created = client.post(
        "/intents",
        data={"description": "A mountain of goop for a surreal game world."},
        follow_redirects=False,
    )
    intent_path = urlparse(created.headers["location"]).path
    proposal = client.get(intent_path)

    assert proposal.status_code == 200
    assert "treat this as a static game asset, about 800 m tall." in proposal.text
    assert "quick answer" not in proposal.text
    assert "Adjust" in proposal.text
    assert "Why this target?" in proposal.text
    assert "A mountain is an environmental feature." in proposal.text
    assert "not a measurement of the GLB" in proposal.text

    revised = client.post(
        f"{intent_path}/revise",
        data={"target_use": "STATIC_GAME_ASSET", "target_height_m": "600"},
        follow_redirects=False,
    )
    assert revised.status_code == 303
    adjusted = client.get(intent_path)
    assert "treat this as a static game asset, about 600 m tall." in adjusted.text


def test_web_agent_resolves_one_family_after_confirmation_without_duplicate_height(
    tmp_path: Path,
) -> None:
    """Agreed intent yields one reviewable family proposal with no baseline selection."""
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))
    _, intake_path = _confirmed_intent(client)
    response = client.get(intake_path)

    assert response.status_code == 200
    assert "Choose a policy baseline" not in response.text
    assert "Human-scale static mesh" not in response.text
    assert "Compact static mesh" not in response.text
    assert 'name="profile_id"' not in response.text
    assert "Agent-resolved rules · 1.8 m target" in response.text
    assert "Review all active rules" in response.text
    assert "Why these rules?" in response.text
    assert "This is the height already confirmed in the target story." in response.text
    assert "Target height" in response.text
    assert "Require Y-up geometry" in response.text
    assert "Name pattern" in response.text
    assert "Maximum triangles" in response.text
    assert "Approval for physical normalization" in response.text
    assert "Adjust supported rules" in response.text
    assert "Fixed safety boundary" in response.text
    assert "transform matrix" not in response.text.lower()
    assert 'data-intake-panel="rules"' in response.text
    assert 'data-intake-panel="upload" aria-labelledby="upload-title" hidden' in response.text
    assert "Confirmed target 1.8 m" in response.text
    assert response.text.count('name="target_height_m"') == 0
    _assert_focus_area_budget(response.text)


def test_web_cannot_upload_before_agreement(tmp_path: Path) -> None:
    """Possessing a draft ID is not repair or inspection authorization."""
    work_root = tmp_path / "jobs"
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))
    intent_path = _draft_intent(client)
    intent_id = intent_path.rsplit("/", 1)[-1]

    response = client.post(
        f"/intents/{intent_id}/jobs",
        data={},
        files={"asset": (CLEAN_PATH.name, CLEAN_PATH.read_bytes(), "model/gltf-binary")},
    )

    assert response.status_code == 400
    assert "Agree on the target story before uploading" in response.text
    assert not work_root.exists() or not tuple(work_root.iterdir())


def test_web_broken_fixture_completes_the_agreed_guarded_flow(tmp_path: Path) -> None:
    """A confirmed intent flows through interrupt, verification, and package evidence."""
    work_root = tmp_path / "jobs"
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))
    intent_id, _ = _confirmed_intent(client)
    job_path = _upload(client, BROKEN_PATH, intent_id=intent_id)

    pending = client.get(job_path)
    assert pending.status_code == 200
    assert "Approval needed" in pending.text
    assert "Normalize physical scale, upright orientation, and grounding" in pending.text
    assert "Confirmed target story" in pending.text
    _assert_focus_area_budget(pending.text)
    interrupt_id = _interrupt_id(pending.text)
    job_id = job_path.rsplit("/", 1)[-1]
    job_root = work_root / job_id
    output = job_root / "output"

    inspection = InspectionResult.model_validate_json(
        (output / "inspection.json").read_text(encoding="utf-8")
    )
    ruled_findings = tuple(
        finding for finding in inspection.findings if finding.profile_rule is not None
    )
    assert ruled_findings
    assert all(finding.rule_provenance is not None for finding in ruled_findings)
    assert not (output / "candidate.glb").exists()

    inspect_view = client.get(f"{job_path}?view=inspect")
    assert inspect_view.status_code == 200
    assert "Policy rule" in inspect_view.text
    assert "Height target 180.0 cm ± 9.0 cm" in inspect_view.text
    _assert_focus_area_budget(inspect_view.text)

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
    assert "Import-ready candidate" in completed.text
    assert "Ready-to-import proof" in completed.text
    assert "PASSED_WITH_REMAINING_WARNINGS" in completed.text
    assert "Download result ZIP" in completed.text
    _assert_focus_area_budget(completed.text)
    assert client.get(f"{job_path}/repaired.glb").status_code == 200

    recorded_decision = client.get(f"{job_path}?view=decide")
    assert "Decision recorded" in recorded_decision.text
    assert "normalize-root-v1" in recorded_decision.text

    archive_response = client.get(f"{job_path}/download")
    assert archive_response.status_code == 200
    archive_path = tmp_path / "result.zip"
    archive_path.write_bytes(archive_response.content)
    with ZipFile(archive_path) as archive:
        assert set(archive.namelist()) == PACKAGE_NAMES

    decisions = Decisions.model_validate_json(
        (output / "decisions.json").read_text(encoding="utf-8")
    )
    normalization = next(
        record for record in decisions.records if record.candidate_id == "normalize-root-v1"
    )
    assert normalization.decision is DecisionValue.APPROVED
    assert normalization.interrupt_id == interrupt_id

    frozen_intent = AssetIntentProvenance.model_validate_json(
        (job_root / "intent.json").read_text(encoding="utf-8")
    )
    target_intake = TargetIntakeContract.model_validate_json(
        (job_root / "target_intake.json").read_text(encoding="utf-8")
    )
    assert target_intake.ready_for_confirmation
    assert target_intake.target_use is AssetTargetUse.STATIC_GAME_ASSET
    assert target_intake.target_height_cm == 180.0
    validate_asset_intent(frozen_intent)
    provenance = Provenance.model_validate_json(
        (output / "provenance.json").read_text(encoding="utf-8")
    )
    assert provenance.asset_intent == frozen_intent
    assert frozen_intent.intent_id == intent_id
    assert frozen_intent.target_use is AssetTargetUse.STATIC_GAME_ASSET
    assert frozen_intent.target_height_cm == 180.0
    assert re.fullmatch(r"[0-9a-f]{64}", frozen_intent.canonical_sha256)
    assert provenance.profile_policy is not None
    assert provenance.profile_policy.frozen_profile_id.startswith(f"{FAMILY_ID}-resolved-")
    assert provenance.profile_policy.base_preset_id == FAMILY_ID
    assert provenance.profile_policy.policy_family_id == FAMILY_ID
    assert provenance.profile_policy.explicit_overrides == {
        "expected_height_cm.target": 180.0,
        "expected_height_cm.tolerance": 9.0,
        "orientation.ground_tolerance_cm": 0.9,
    }
    assert provenance.profile_policy.rule_sources["expected_height_cm.target"] == (
        "CONFIRMED_INTENT"
    )


def test_intended_height_derives_a_frozen_profile_without_raw_transform_input(
    tmp_path: Path,
) -> None:
    """Confirmed height resolves the family without exposing a scale operation."""
    work_root = tmp_path / "jobs"
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))
    job_path = _upload(client, CLEAN_PATH, target_height_m="1.82")
    job_root = work_root / job_path.rsplit("/", 1)[-1]

    frozen_profile = ProjectProfile.model_validate_json(
        (job_root / "profile.json").read_text(encoding="utf-8")
    )
    provenance = Provenance.model_validate_json(
        (job_root / "output" / "provenance.json").read_text(encoding="utf-8")
    )
    assert frozen_profile.profile_id.startswith(f"{FAMILY_ID}-resolved-")
    assert provenance.asset_intent is not None
    assert provenance.asset_intent.target_height_cm == 182.0
    assert provenance.profile_policy is not None
    assert provenance.profile_policy.explicit_overrides == {
        "expected_height_cm.target": 182.0,
        "expected_height_cm.tolerance": 9.1,
        "orientation.ground_tolerance_cm": 0.91,
    }
    assert "scale factor" not in provenance.asset_intent.confirmed_story.lower()


def test_web_custom_profile_is_validated_frozen_and_does_not_mutate_preset(
    tmp_path: Path,
) -> None:
    """A supported custom copy gets an immutable job snapshot and complete provenance."""
    preset_paths = (
        PROJECT_ROOT / "profiles" / "unreal_indie_robot.json",
        PROJECT_ROOT / "validation" / "profiles" / "small_stylized_static_mesh.json",
        PROJECT_ROOT / "src" / "asset_shepherd" / "data" / "unreal_static_game_asset_family.json",
    )
    policy_bytes_before = {path: path.read_bytes() for path in preset_paths}
    work_root = tmp_path / "jobs"
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))

    job_path = _upload(
        client,
        CLEAN_PATH,
        policy_data=CUSTOM_PROFILE_DATA,
        target_height_m="1.82",
    )
    job_root = work_root / job_path.rsplit("/", 1)[-1]
    frozen_profile = ProjectProfile.model_validate_json(
        (job_root / "profile.json").read_text(encoding="utf-8")
    )
    provenance = Provenance.model_validate_json(
        (job_root / "output" / "provenance.json").read_text(encoding="utf-8")
    )

    assert frozen_profile.profile_id.startswith(f"{FAMILY_ID}-resolved-")
    assert provenance.profile_id == frozen_profile.profile_id
    assert provenance.profile_policy is not None
    assert provenance.profile_policy.frozen_profile_id == frozen_profile.profile_id
    assert provenance.profile_policy.base_preset_id == FAMILY_ID
    assert provenance.profile_policy.policy_family_id == FAMILY_ID
    assert provenance.profile_policy.profile_version == 1
    assert provenance.profile_policy.explicit_overrides == {
        "expected_height_cm.target": 182.0,
        "expected_height_cm.tolerance": 1.0,
        "orientation.ground_tolerance_cm": 1.0,
    }
    assert provenance.profile_policy.rule_sources["expected_height_cm.tolerance"] == (
        "USER_OVERRIDE"
    )
    assert provenance.profile_policy.canonical_sha256 == canonical_profile_sha256(frozen_profile)
    assert {path: path.read_bytes() for path in preset_paths} == policy_bytes_before


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("custom_naming_pattern", "[", "naming pattern is invalid"),
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
    intent_id, _ = _confirmed_intent(client)
    policy_data = {**CUSTOM_PROFILE_DATA, field: value}

    response = client.post(
        f"/intents/{intent_id}/jobs",
        data=policy_data,
        files={"asset": (CLEAN_PATH.name, CLEAN_PATH.read_bytes(), "model/gltf-binary")},
    )

    assert response.status_code == 400
    assert message in response.text
    assert not work_root.exists() or not tuple(work_root.iterdir())


def test_changing_rules_or_intent_after_upload_creates_new_jobs(tmp_path: Path) -> None:
    """Frozen jobs are never reinterpreted when policy or target intent changes."""
    work_root = tmp_path / "jobs"
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))
    first_intent_id, _ = _confirmed_intent(client, target_height_m="1.8")
    first_path = _upload(
        client,
        CLEAN_PATH,
        intent_id=first_intent_id,
        policy_data=CUSTOM_PROFILE_DATA,
    )
    second_policy = {**CUSTOM_PROFILE_DATA, "custom_height_tolerance_cm": "2"}
    second_path = _upload(
        client,
        CLEAN_PATH,
        intent_id=first_intent_id,
        policy_data=second_policy,
    )
    third_path = _upload(client, CLEAN_PATH, target_height_m="1.81")

    assert len({first_path, second_path, third_path}) == 3
    roots = [work_root / path.rsplit("/", 1)[-1] for path in (first_path, second_path, third_path)]
    intents = [
        AssetIntentProvenance.model_validate_json(
            (root / "intent.json").read_text(encoding="utf-8")
        )
        for root in roots
    ]
    profiles = [
        ProjectProfile.model_validate_json((root / "profile.json").read_text(encoding="utf-8"))
        for root in roots
    ]
    inspections = [
        InspectionResult.model_validate_json(
            (root / "output" / "inspection.json").read_text(encoding="utf-8")
        )
        for root in roots
    ]
    assert intents[0].intent_id == intents[1].intent_id
    assert intents[2].intent_id != intents[0].intent_id
    assert canonical_profile_sha256(profiles[0]) != canonical_profile_sha256(profiles[1])
    assert len({inspection.profile_id for inspection in inspections}) == 3
    assert (
        "Changing rules starts a new inspection and job"
        in client.get(f"{first_path}?view=inspect").text
    )


def test_web_clean_fixture_completes_twice_from_clean_app_starts(tmp_path: Path) -> None:
    """The clean no-approval path completes twice from independent application starts."""
    for run_number in range(2):
        work_root = tmp_path / f"clean-start-{run_number}"
        client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))
        job_path = _upload(client, CLEAN_PATH)
        completed = client.get(job_path)
        assert completed.status_code == 200
        assert "Import-ready candidate" in completed.text
        assert "Approval needed" not in completed.text
        assert "PASSED_PROJECT_READY" in completed.text
        _assert_focus_area_budget(completed.text)
        inspected = client.get(f"{job_path}?view=inspect")
        assert "No project-policy findings." in inspected.text
        assert client.get(f"{job_path}/download").status_code == 200


def test_web_rejects_non_glb_upload_without_starting_a_job(tmp_path: Path) -> None:
    """Invalid browser input gets a coherent intake error and no retained job."""
    work_root = tmp_path / "jobs"
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))
    intent_id, _ = _confirmed_intent(client)
    response = client.post(
        f"/intents/{intent_id}/jobs",
        data={},
        files={"asset": ("not-a-model.glb", b"not a GLB", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "The upload is not a GLB 2.0 binary container." in response.text
    assert "Agreed target" in response.text
    _assert_focus_area_budget(response.text)
    assert not work_root.exists() or not tuple(work_root.iterdir())


def test_web_packages_unsupported_asset_as_inspection_only(tmp_path: Path) -> None:
    """Unsupported structural content is blocked and packaged without a repaired GLB."""
    skinned_path = tmp_path / "skinned.glb"
    gltf = load_glb(CLEAN_PATH)
    gltf.skins.append(Skin(name="UnsupportedSkin", joints=[]))
    save_glb(gltf, skinned_path)
    source_before = skinned_path.read_bytes()

    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))
    job_path = _upload(client, skinned_path)
    blocked = client.get(job_path)
    assert blocked.status_code == 200
    assert "Inspection-only result" in blocked.text
    blocked_inspect = client.get(f"{job_path}?view=inspect")
    assert "INSPECTION_ONLY_UNSUPPORTED_FEATURES" in blocked_inspect.text
    assert "UNSUPPORTED_REPAIR_FEATURES" in blocked_inspect.text
    assert client.get(f"{job_path}/repaired.glb").status_code == 404
    assert skinned_path.read_bytes() == source_before

    archive_response = client.get(f"{job_path}/download")
    assert archive_response.status_code == 200
    archive_path = tmp_path / "blocked-result.zip"
    archive_path.write_bytes(archive_response.content)
    with ZipFile(archive_path) as archive:
        assert set(archive.namelist()) == PACKAGE_NAMES - {"repaired.glb"}


def test_old_role_routes_redirect_to_the_intent_entry_point(tmp_path: Path) -> None:
    """Existing bookmarks remain safe without preserving the retired selector modality."""
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))
    for slug in ("game-developer", "artist", "technical-artist", "advanced"):
        response = client.get(f"/stories/{slug}", follow_redirects=False)
        assert response.status_code == 303
        assert urlparse(response.headers["location"]).path == "/"
