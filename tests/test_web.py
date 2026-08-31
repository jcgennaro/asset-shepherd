"""Acceptance tests for the local intent-to-download web product."""

# pygltflib is typed internally but does not publish PEP 561 metadata.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import urlparse
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from pygltflib import Skin

from asset_shepherd.glb import load_glb, save_glb, world_bounds
from asset_shepherd.hosted_workspace import WorkspacePhase
from asset_shepherd.intake_analyzer import (
    INTAKE_REFUSAL_MESSAGE,
    TargetDimensionsInference,
    TargetIntakeContentRefusal,
    TargetIntakeInference,
    contract_from_inference,
)
from asset_shepherd.intent import validate_asset_intent
from asset_shepherd.models import (
    AssetEndpoint,
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
from asset_shepherd.web import create_app, gallery_status

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


@pytest.mark.parametrize(
    ("phase", "label", "tone"),
    (
        (WorkspacePhase.TARGET_CONFIRMATION, "Step 2 · Describe", "pending"),
        (WorkspacePhase.APPROVAL, "Step 3 · Review", "attention"),
        (WorkspacePhase.COMPLETE, "Step 3 · Ready", "success"),
        (WorkspacePhase.BLOCKED, "Step 3 · Blocked", "danger"),
        (WorkspacePhase.ERROR, "Step 3 · Failed", "danger"),
    ),
)
def test_gallery_status_uses_workflow_language_and_accessible_tone(
    phase: WorkspacePhase,
    label: str,
    tone: str,
) -> None:
    """Every durable state maps to one concise gallery status."""
    status = gallery_status(phase)

    assert status.label == label
    assert status.tone == tone


def test_gallery_status_locates_refinement_iterations() -> None:
    """A saved refinement reports its exact Step 4 iteration in the gallery."""
    status = gallery_status(WorkspacePhase.APPROVAL, 2)
    assert status.label == "Step 4.2 · Review"
    assert status.tone == "attention"


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


def test_web_starts_with_the_authoritative_asset_gallery(tmp_path: Path) -> None:
    """The public root cannot strand users in the superseded form-led surface."""
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))
    redirect = client.get("/", follow_redirects=False)
    response = client.get("/workspace")

    assert redirect.status_code == 303
    assert urlparse(redirect.headers["location"]).path == "/workspace"
    assert response.status_code == 200
    assert "<title>Asset Shepherd -- Gallery</title>" in response.text
    assert "New asset" in response.text
    assert ">Gallery</strong>" in response.text
    assert ">Workflow</strong>" in response.text
    assert 'aria-label="Workflow steps"' not in response.text
    assert ">Agree</strong>" not in response.text
    assert ">Inspect</strong>" not in response.text
    _assert_focus_area_budget(response.text)


def test_description_fields_still_share_one_component(tmp_path: Path) -> None:
    """Legacy and hosted target edits retain one shared description field renderer."""
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))
    css = client.get("/static/app.css")
    intent_path = _draft_intent(client)
    confirm = client.get(intent_path)

    assert css.status_code == 200
    assert re.search(
        r"\.intent-stage\s*\{[^}]*width: 100%;[^}]*margin:",
        css.text,
        re.DOTALL,
    )
    assert re.search(
        r"\.intent-stage \.intent-heading h2\s*\{[^}]*"
        r"font-size: clamp\(1\.75rem, 2\.4vw, 2\.5rem\);",
        css.text,
        re.DOTALL,
    )
    assert re.search(
        r"textarea\.asset-description-input\s*\{[^}]*width: 100%;[^}]*"
        r"height: 168px;[^}]*font-size: 1rem;[^}]*font-weight: 400;",
        css.text,
        re.DOTALL,
    )
    assert re.search(
        r"\.confirmation-actions \.intent-adjust \.intent-form\s*\{\s*width: 100%;",
        css.text,
    )
    assert 'class="intent-stage intent-confirmation"' in confirm.text
    assert 'class="asset-description-field"' in confirm.text
    assert "data-confirmation-decision" in confirm.text
    assert "&amp;amp;" not in confirm.text

    component_source = (
        PROJECT_ROOT / "src" / "asset_shepherd" / "templates" / "_workflow_components.html"
    ).read_text(encoding="utf-8")
    assert component_source.count('<textarea class="asset-description-input"') == 1
    assert component_source.count('<section class="confirmation-question"') == 1
    for template in (PROJECT_ROOT / "src" / "asset_shepherd" / "templates").glob("*.html"):
        if template.name != "_workflow_components.html":
            source = template.read_text(encoding="utf-8")
            assert '<textarea class="asset-description-input"' not in source
            assert '<section class="confirmation-question"' not in source


def test_upload_controls_support_click_and_drag_drop(tmp_path: Path) -> None:
    """Both upload surfaces share one GLB chooser-and-drop interaction."""
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))
    _, intake_path = _confirmed_intent(client)
    hosted_upload_path = "/workspace/new/upload"

    for response in (client.get(intake_path), client.get(hosted_upload_path)):
        assert response.status_code == 200
        assert "Choose or drop your GLB" in response.text
        assert "data-drop-zone" in response.text
        assert "data-file-input" in response.text
        assert "data-file-error" in response.text

    script = client.get("/static/app.js")
    assert script.status_code == 200
    assert 'addEventListener("dragover"' not in script.text
    assert 'for (const eventName of ["dragenter", "dragover"])' in script.text
    assert 'dropZone.addEventListener("drop"' in script.text
    assert "fileInput.files = dropped" in script.text
    assert 'endsWith(".glb")' in script.text


def test_textareas_submit_with_ctrl_enter_only(tmp_path: Path) -> None:
    """Ctrl+Enter uses native form submission while ordinary Enter remains text input."""
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))
    script = client.get("/static/app.js")

    assert script.status_code == 200
    assert 'for (const textarea of document.querySelectorAll("textarea"))' in script.text
    assert 'event.key === "Enter"' in script.text
    assert "event.ctrlKey" in script.text
    assert "event.preventDefault()" in script.text
    assert "form.requestSubmit(submitButton)" in script.text


def test_how_it_works_stays_in_the_flow_rail_and_explains_the_product(
    tmp_path: Path,
) -> None:
    """The persistent question-mark action opens one concise workflow explanation."""
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))

    entry = client.get("/workspace")
    assert entry.status_code == 200
    assert ">Gallery</strong>" in entry.text
    assert ">Workflow</strong>" in entry.text
    assert 'aria-label="Workflow steps"' not in entry.text
    assert 'class="help-icon" aria-hidden="true">?</span>' in entry.text
    assert 'href="/how-it-works"' in entry.text

    upload = client.get("/workspace/new/upload")
    assert 'aria-label="Workflow steps"' in upload.text
    assert upload.text.index(">Upload</strong>") < upload.text.index(">Describe</strong>")
    assert upload.text.index(">Describe</strong>") < upload.text.index(">Shepherd</strong>")
    assert upload.text.index(">Shepherd</strong>") < upload.text.index(">Refine</strong>")

    help_page = client.get("/how-it-works")
    assert help_page.status_code == 200
    assert "<title>Asset Shepherd -- How it works</title>" in help_page.text
    assert (
        "Upload the GLB, describe the intended result, and keep the best iteration "
        "as you work with the agent." in help_page.text
    )
    assert "Upload and describe" in help_page.text
    assert "Review what we found" in help_page.text
    assert "Refine if needed" in help_page.text
    assert "Download the result" in help_page.text
    assert len(re.findall(r"<span>0[1-4]</span>", help_page.text)) == 4
    assert "Current scope" not in help_page.text
    assert "Version 1" not in help_page.text
    assert "What can Asset Shepherd repair?" not in help_page.text
    assert "Deterministic tools" not in help_page.text
    assert "provenance" not in help_page.text.lower()
    assert "safety boundary" not in help_page.text.lower()
    assert "original stays untouched" not in help_page.text.lower()
    assert help_page.text.count("<h1") == 1
    assert "<h2" not in help_page.text
    assert "<h3" not in help_page.text
    _assert_focus_area_budget(help_page.text)


def test_what_it_does_groups_worker_value_into_three_checks(tmp_path: Path) -> None:
    """The brain action opens one concise worker-facing capability summary."""
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))

    entry = client.get("/workspace")
    assert 'href="/what-it-does"' in entry.text
    assert 'title="See what Asset Shepherd checks"' in entry.text
    assert ">What it does</span>" in entry.text

    page = client.get("/what-it-does")
    assert page.status_code == 200
    assert "<title>Asset Shepherd -- What it does</title>" in page.text
    assert "will import, look right, and remain practical to ship" in page.text
    assert "Imports cleanly" in page.text
    assert "Looks as intended" in page.text
    assert "Practical to ship" in page.text
    assert "forward direction" in page.text
    assert len(re.findall(r"<span>0[1-3]</span>", page.text)) == 3
    assert "Version 1" not in page.text
    assert "Deterministic" not in page.text
    assert page.text.count("<h1") == 1
    assert "<h2" not in page.text
    assert "<h3" not in page.text
    _assert_focus_area_budget(page.text)


@pytest.mark.parametrize("height_cm", (0.5, 2.0, 120.0, 80000.0))
def test_confirmation_uses_a_readable_metric_unit_for_target_scale(
    tmp_path: Path,
    height_cm: float,
) -> None:
    """Confirmation presents the complete tight X/Y/Z target box."""

    class ScaleAnalyzer:
        provider = "openai"
        model_id = "gpt-5.6-luna"

        def analyze(self, description: str) -> TargetIntakeContract:
            return contract_from_inference(
                description,
                TargetIntakeInference(
                    engagement_decision="PROCEED",
                    asset_name="Tiny Bracelet",
                    target_use=AssetTargetUse.STATIC_GAME_ASSET,
                    target_use_confidence=0.96,
                    target_use_evidence="The description identifies a static prop.",
                    endpoint=AssetEndpoint.UNITY,
                    endpoint_detail=None,
                    endpoint_confidence=0.9,
                    endpoint_evidence="The asset is intended for Unity.",
                    target_dimensions_cm=TargetDimensionsInference(
                        x_cm=height_cm * 0.5,
                        y_cm=height_cm,
                        z_cm=height_cm * 0.25,
                    ),
                    target_dimensions_confidence=0.91,
                    target_dimensions_evidence="The description states the intended scale.",
                    expected_piece_count=1,
                    expected_piece_count_evidence="The description identifies one bracelet.",
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
    meters = height_cm / 100
    assert f"{meters * 0.5:g} x {meters:g} x {meters * 0.25:g} m" in review.text


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
    assert (
        "I\u2019d shepherd this for Unspecified endpoint within 1.72 x 1.72 x 1.72 m."
        in review.text
    )
    assert "Playable animated character" in review.text
    assert "1.72 x 1.72 x 1.72 m" in review.text
    assert "Static inspection and handoff; no rigging or animation repair" in review.text
    assert review.text.count('class="expectation-group"') == 3
    assert "Purpose" in review.text
    assert "Scale and pose" in review.text
    assert "Structure" in review.text
    assert "Structure and safety" not in review.text
    assert "source content protected" not in review.text.lower()
    assert "source content preserved" not in review.text.lower()
    assert 'name="target_use"' not in review.text
    assert 'name="target_height_m"' not in review.text
    assert "Did I get it right?" in review.text
    assert ">Yes</button>" in review.text
    assert "<summary>No</summary>" in review.text
    assert "Yes, inspect this asset" not in review.text
    assert "No, edit and try again" not in review.text
    assert 'textarea class="asset-description-input"' in review.text
    assert "It\u2019s not working for me" in review.text
    assert "no rigging or animation repair" in review.text
    assert "Choose your GLB file" not in review.text
    assert "Review rules" not in review.text
    _assert_focus_area_budget(review.text)

    unconfirmed_intake = client.get(f"{intent_path}/intake", follow_redirects=False)
    assert unconfirmed_intake.status_code == 303
    assert urlparse(unconfirmed_intake.headers["location"]).path == intent_path

    intake_path = _agree_intent(client, intent_path)
    intake = client.get(intake_path)
    assert intake.status_code == 200
    assert "Asset Shepherd -- Shepherd" in intake.text
    assert "Add the GLB and I\u2019ll shepherd it toward the target we agreed." in intake.text
    assert "Review rules" in intake.text
    assert "Choose or drop your GLB" in intake.text
    assert "Agreed target" not in intake.text
    assert "Review the rules I derived" not in intake.text
    assert intake.text.count("<h1") == 1
    assert "<h2" not in intake.text
    assert "<h3" not in intake.text
    _assert_focus_area_budget(intake.text)


def test_web_validates_description_before_target_drafting(tmp_path: Path) -> None:
    """Invalid conversational input cannot create a target story or a job."""
    work_root = tmp_path / "jobs"
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))
    response = client.post("/intents", data={"description": "too short"})

    assert response.status_code == 400
    assert "at least 12 characters" in response.text
    assert not work_root.exists()


def test_web_refuses_disallowed_intake_without_echoing_or_storing_it(tmp_path: Path) -> None:
    """Both entry routes show one concise refusal and retain no request or uploaded file."""

    class RefusalAnalyzer:
        provider = "test"
        model_id = "refusal-test"

        def analyze(self, description: str) -> TargetIntakeContract:
            del description
            raise TargetIntakeContentRefusal(INTAKE_REFUSAL_MESSAGE)

    work_root = tmp_path / "jobs"
    client = TestClient(
        create_app(
            project_root=PROJECT_ROOT,
            work_root=work_root,
            intake_analyzer=RefusalAnalyzer(),
        )
    )
    declined_description = "A sufficiently long description declined by the intake model."

    form_led = client.post("/intents", data={"description": declined_description})
    assert form_led.status_code == 400
    assert unescape(form_led.text).count(INTAKE_REFUSAL_MESSAGE) == 1
    assert "Check the target" not in form_led.text
    assert declined_description not in form_led.text

    staged = client.post(
        "/workspace/new/upload",
        files={"asset": (CLEAN_PATH.name, CLEAN_PATH.read_bytes(), "model/gltf-binary")},
        follow_redirects=False,
    )
    assert staged.status_code == 303
    describe_path = urlparse(staged.headers["location"]).path
    assert tuple(work_root.rglob("source.glb"))

    hosted = client.post(describe_path, data={"description": declined_description})
    assert hosted.status_code == 400
    assert unescape(hosted.text).count(INTAKE_REFUSAL_MESSAGE) == 1
    assert "Workspace not started" not in hosted.text
    assert declined_description not in hosted.text
    assert not tuple(work_root.rglob("source.glb"))
    assert not tuple(work_root.rglob("workspace.json"))


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
    assert "What should its tight X/Y/Z bounds be?" in clarification.text
    assert "treating it as static game asset" in clarification.text
    assert "Tight target bounds" in clarification.text
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
    assert "Static game asset" in review.text
    assert "1.2 x 1.2 x 1.2 m" in review.text


def test_missing_intent_is_clarified_in_words_without_a_mode_selector(tmp_path: Path) -> None:
    """An unresolved deterministic fallback asks for better context, not a preset choice."""
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))
    created = client.post(
        "/intents",
        data={"description": "A mountain of goop for a surreal game world."},
        follow_redirects=False,
    )
    intent_path = urlparse(created.headers["location"]).path
    clarification = client.get(intent_path)

    assert "Tell me the missing intent in your own words." in clarification.text
    assert 'name="description"' in clarification.text
    assert 'name="target_use"' not in clarification.text
    assert 'name="target_height_m"' not in clarification.text

    completed = client.post(
        f"{intent_path}/clarify",
        data={"description": "A 600 m static game asset: a mountain of goop for scenery."},
        follow_redirects=False,
    )
    assert completed.status_code == 303
    review = client.get(intent_path)
    assert "Static game asset" in review.text
    assert "600 x 600 x 600 m" in review.text


def test_semantic_intake_proposes_and_allows_adjustment_without_duplicate_questions(
    tmp_path: Path,
) -> None:
    """A model-backed ordinary prompt reaches one concise, user-adjustable confirmation."""

    class SemanticAnalyzer:
        provider = "openai"
        model_id = "gpt-5.6-luna"

        def analyze(self, description: str) -> TargetIntakeContract:
            height_cm = 60000.0 if "600 m" in description else 80000.0
            return contract_from_inference(
                description,
                TargetIntakeInference(
                    engagement_decision="PROCEED",
                    asset_name="Goop Mountain",
                    target_use=AssetTargetUse.STATIC_GAME_ASSET,
                    target_use_confidence=0.96,
                    target_use_evidence="A mountain is an environmental feature.",
                    endpoint=AssetEndpoint.GODOT,
                    endpoint_detail=None,
                    endpoint_confidence=0.9,
                    endpoint_evidence="The surreal game is being built in Godot.",
                    target_dimensions_cm=TargetDimensionsInference(
                        x_cm=height_cm * 0.75,
                        y_cm=height_cm,
                        z_cm=height_cm * 0.625,
                    ),
                    target_dimensions_confidence=0.91,
                    target_dimensions_evidence="A mountain is a kilometer-scale feature.",
                    expected_piece_count=1,
                    expected_piece_count_evidence="The description identifies one mountain.",
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
    assert "Static game asset" in proposal.text
    assert "600 x 800 x 500 m" in proposal.text
    assert "quick answer" not in proposal.text
    assert "<summary>No</summary>" in proposal.text
    assert "Show inference evidence" not in proposal.text
    assert "A mountain is an environmental feature." in proposal.text
    assert "1 expected semantic piece" in proposal.text
    assert "valid GLB required" not in proposal.text
    assert proposal.text.count('class="expectation-group"') == 3
    assert "Always checked for every GLB" not in proposal.text
    assert 'name="target_use"' not in proposal.text
    assert 'name="target_height_m"' not in proposal.text

    revised = client.post(
        f"{intent_path}/revise",
        data={"description": "A 600 m mountain of goop for a surreal game world."},
        follow_redirects=False,
    )
    assert revised.status_code == 303
    adjusted = client.get(intent_path)
    assert "450 x 600 x 375 m" in adjusted.text


def test_shared_feedback_page_records_workflow_context(tmp_path: Path) -> None:
    """One reusable feedback page stores bounded reasons, notes, and workflow context."""
    work_root = tmp_path / "jobs"
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))

    page = client.get(
        "/feedback",
        params={
            "context": "target-confirmation",
            "reference_id": "intent-123",
            "return_path": "/intents/intent-123",
        },
    )
    assert page.status_code == 200
    assert "What isn\u2019t working?" in page.text
    assert "Reviewing the proposed target" in page.text
    assert page.text.count('name="reason"') == 4
    assert 'maxlength="1000"' in page.text

    submitted = client.post(
        "/feedback",
        data={
            "context": "target-confirmation",
            "reference_id": "intent-123",
            "return_path": "/intents/intent-123",
            "reason": "wrong-result",
            "note": "The proposed scale ignored the description.",
        },
    )
    assert submitted.status_code == 200
    assert "Thanks. I recorded that." in submitted.text
    assert 'href="/intents/intent-123"' in submitted.text

    records = list((work_root / "feedback").glob("*.json"))
    assert len(records) == 1
    payload = json.loads(records[0].read_text(encoding="utf-8"))
    assert payload["context"] == "target-confirmation"
    assert payload["reference_id"] == "intent-123"
    assert payload["reason"] == "wrong-result"
    assert payload["note"] == "The proposed scale ignored the description."


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
    assert "Review rules" in response.text
    assert "1.8 m height" in response.text
    assert "All active rules" in response.text
    assert "Why these rules?" in response.text
    assert "This is the height already confirmed in the target story." in response.text
    assert "Target height" in response.text
    assert "Require Y-up geometry" in response.text
    assert "Name pattern" in response.text
    assert "Maximum triangles" in response.text
    assert "Approval for physical normalization" in response.text
    assert "Adjust supported rules" in response.text
    assert "Fixed safety boundary" not in response.text
    assert "source preservation" not in response.text.lower()
    assert "transform matrix" not in response.text.lower()
    assert 'data-intake-panel="rules"' not in response.text
    assert 'data-intake-panel="upload"' not in response.text
    assert "Choose or drop your GLB" in response.text
    assert response.text.count("<h1") == 1
    assert "<h2" not in response.text
    assert "<h3" not in response.text
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
    assert "Inspection results" in pending.text
    assert "Checking your GLB" in pending.text
    assert "Summary" in pending.text
    assert "Do these issues look fixable?" in pending.text
    assert "More details" in pending.text
    assert "Normalize physical scale, upright orientation, and grounding" not in pending.text
    assert 'class="inspect-storyboard"' not in pending.text
    assert pending.text.count("data-inspection-check") == 5
    assert "Confirmed target story" not in pending.text
    assert 'class="job-workflow-nav"' not in pending.text
    _assert_focus_area_budget(pending.text)
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
    assert "GLB structure" in inspect_view.text
    assert "Size and pose" in inspect_view.text
    assert "Topology" in inspect_view.text
    assert "Materials and textures" in inspect_view.text
    assert "Display names" in inspect_view.text
    assert "nodes" in inspect_view.text
    assert "meshes" in inspect_view.text
    assert "primitives" in inspect_view.text
    assert "Target-specific expectation" in inspect_view.text
    assert "Height target 180.0 cm ± 9.0 cm" in inspect_view.text
    assert "safe" not in inspect_view.text.lower()
    assert "source content" not in inspect_view.text.lower()
    _assert_focus_area_budget(inspect_view.text)

    gated_decide = client.get(f"{job_path}?view=decide")
    assert "Do these issues look fixable?" in gated_decide.text
    assert "Normalize physical scale, upright orientation, and grounding" not in gated_decide.text

    acknowledged = client.post(f"{job_path}/inspection/confirm", follow_redirects=False)
    assert acknowledged.status_code == 303
    assert acknowledged.headers["location"].endswith("?view=decide")
    decision_view = client.get(acknowledged.headers["location"])
    assert "Normalize physical scale, upright orientation, and grounding" in decision_view.text
    interrupt_id = _interrupt_id(decision_view.text)

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
    assert "Did we get it right?" in completed.text
    assert "data-result-accepted hidden" in completed.text
    assert "Download fixed model" in completed.text
    assert "Evidence package" in completed.text
    assert "data-model-comparison" in completed.text
    assert completed.text.count("<model-viewer") == 1
    assert completed.text.count("<extra-model") == 2
    offsets = re.findall(r'<extra-model[^>]+offset="([^"]+)"', completed.text)
    assert len(offsets) == 2
    assert all("m" not in offset for offset in offsets)
    assert completed.text.count("data-comparison-cycle") == 2
    assert 'title="Cycle viewpoint: Both → Before"' in completed.text
    assert 'data-comparison-fit="before"' not in completed.text
    assert 'data-comparison-fit="after"' not in completed.text
    assert completed.text.count('data-comparison-origin="before"') == 1
    assert completed.text.count('data-comparison-origin="after"') == 1
    assert "Show metric X, Y, and Z axes" in completed.text
    assert "normal-size 20 cm banana" in completed.text
    assert "BEFORE MODEL HERE" not in completed.text
    _assert_focus_area_budget(completed.text)
    repaired_response = client.get(f"{job_path}/repaired.glb")
    assert repaired_response.status_code == 200
    disposition = repaired_response.headers["content-disposition"]
    assert disposition.endswith('.glb"')
    assert "repaired.glb" not in disposition

    accepted = client.post(
        f"{job_path}/result",
        data={"decision": "accept"},
        headers={"X-Asset-Shepherd-Transition": "accept"},
        follow_redirects=False,
    )
    assert accepted.status_code == 204
    accepted_page = client.get(f"{job_path}?view=download")
    assert "Did we get it right?" not in accepted_page.text
    assert "data-result-accepted hidden" not in accepted_page.text
    assert "Ready to download." in accepted_page.text

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
        assert "data-model-comparison" not in completed.text
        _assert_focus_area_budget(completed.text)
        inspected = client.get(f"{job_path}?view=inspect")
        assert "No changes are needed." in inspected.text
        assert "Ready to download." in inspected.text
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
    assert "Add the GLB and I\u2019ll shepherd it toward the target we agreed." in response.text
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
    assert "inspection only unsupported features" in blocked_inspect.text
    assert "UNSUPPORTED_REPAIR_FEATURES" in blocked_inspect.text
    assert "This model needs another export." in blocked_inspect.text
    assert "Return to your model creation tool" in blocked_inspect.text
    assert "safety" not in blocked_inspect.text.lower()
    assert client.get(f"{job_path}/repaired.glb").status_code == 404
    assert skinned_path.read_bytes() == source_before

    archive_response = client.get(f"{job_path}/download")
    assert archive_response.status_code == 200
    archive_path = tmp_path / "blocked-result.zip"
    archive_path.write_bytes(archive_response.content)
    with ZipFile(archive_path) as archive:
        assert set(archive.namelist()) == PACKAGE_NAMES - {"repaired.glb"}


def test_comparison_viewer_assets_and_controls_are_local_and_metric(tmp_path: Path) -> None:
    """The viewer has local assets, metric helpers, and projected 3D bounds."""
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))

    banana_response = client.get("/static/banana-scale.glb")
    assert banana_response.status_code == 200
    assert banana_response.headers["content-type"] == "model/gltf-binary"
    entry = client.get("/workspace")
    assert "/static/vendor/model-viewer.min.js" in entry.text
    assert "ajax.googleapis.com" not in entry.text
    assert client.get("/static/vendor/model-viewer.min.js").status_code == 200
    assert (
        PROJECT_ROOT / "src" / "asset_shepherd" / "static" / "vendor" / "model-viewer.LICENSE"
    ).is_file()
    vendor_source = (
        PROJECT_ROOT / "src" / "asset_shepherd" / "static" / "vendor" / "model-viewer.min.js"
    ).read_text(encoding="utf-8")
    assert "sourceMappingURL=model-viewer.min.js.map" not in vendor_source
    banana_path = PROJECT_ROOT / "src" / "asset_shepherd" / "static" / "banana-scale.glb"
    banana_bounds = world_bounds(load_glb(banana_path))
    assert 0.16 <= max(banana_bounds.dimensions) <= 0.21

    script = client.get("/static/app.js")
    assert script.status_code == 200
    assert 'viewer.addEventListener("camera-change", scheduleHud)' in script.text
    assert "function renderOrbitHud()" in script.text
    assert "window.requestAnimationFrame(renderOrbitHud)" in script.text
    assert 'document.addEventListener("visibilitychange", syncOrbitHudAnimation)' in script.text
    assert "viewer.queryHotspot(name)" in script.text
    assert "viewer.updateHotspot({" in script.text
    assert "function niceMeterStep(span)" in script.text
    assert 'bananaModel?.setAttribute("scale"' in script.text
    assert 'axisLayer.toggleAttribute("hidden"' in script.text
    assert "function animateBananaIn(bounds)" in script.text
    assert "function animateBananaOut()" in script.text
    assert "function adaptiveMetricUnit(longestM)" in script.text
    assert "function formatBoundsDimensions(bounds)" in script.text
    assert 'viewer.toggleAttribute("auto-rotate", shouldOrbit)' in script.text
    assert "viewer.jumpCameraToGoal" not in script.text
    assert "const boundingBoxEdges = [" in script.text
    assert "[5, 7], [6, 7]" in script.text
    assert "const componentColorCount = 6" in script.text
    assert "`comparison-component-box component-color-${colorIndex}`" in script.text
    assert 'graphics.group.classList.toggle("active"' in script.text
    assert 'proposal?.classList.add("active")' in script.text
    assert 'proposal?.classList.remove("active")' in script.text
    assert "!activeComponentId || graphics.id !== activeComponentId" not in script.text
    assert "targetWidth" not in script.text
    assert "function initializeSceneNotebook(notebook)" in script.text
    assert 'notebook.querySelector("[data-notebook-shared-scene]")' in script.text
    assert 'window.addEventListener("scroll", scheduleSelection' in script.text
    assert "const viewportCenter = window.innerHeight / 2" in script.text
    assert "slot.append(sharedScene)" in script.text

    comparison_template = (
        PROJECT_ROOT / "src" / "asset_shepherd" / "templates" / "_model_comparison.html"
    ).read_text(encoding="utf-8")
    assert 'interpolation-decay="240"' in comparison_template
    assert 'auto-rotate-delay="0" rotation-per-second="4deg"' in comparison_template

    workspace_template = (
        PROJECT_ROOT / "src" / "asset_shepherd" / "templates" / "hosted_workspace.html"
    ).read_text(encoding="utf-8")
    assert "data-scene-notebook" in workspace_template
    assert 'id="notebook-upload"' in workspace_template
    assert 'id="notebook-describe"' in workspace_template
    assert "target_notebook_sentence" in workspace_template
    assert "hosted_source_scene" in workspace_template
    assert "data-current-workflow-cell" in workspace_template
    assert "data-notebook-scene-slot" in workspace_template
    assert "view.proposal_summary" in workspace_template
    assert "view.decision_summary" in workspace_template
    assert "view.outcome_summary" in workspace_template
    assert "current_turn_decision_summary" in workspace_template
    assert "current_turn_outcome_summary" in workspace_template
    assert "notebook-intake-message" in workspace_template
    assert "data-notebook-shared-scene" in workspace_template
    assert "hosted_turn_scene" in workspace_template

    checklist_template = (
        PROJECT_ROOT / "src" / "asset_shepherd" / "templates" / "_inspection_checklist.html"
    ).read_text(encoding="utf-8")
    assert "component-color-{{ loop.index0 % 6 }}" in checklist_template

    stylesheet = client.get("/static/app.css")
    assert stylesheet.status_code == 200
    assert ":not([data-workflow-activity]):not([data-model-comparison])" in stylesheet.text
    assert ".component-color-0" in stylesheet.text
    assert ".component-color-5" in stylesheet.text
    assert ".component-proposal.active" in stylesheet.text
    assert ".notebook-scene-slot.active" in stylesheet.text
    assert ".intent-rail li.scene-current" in stylesheet.text


def test_old_role_routes_redirect_to_the_intent_entry_point(tmp_path: Path) -> None:
    """Existing bookmarks remain safe without preserving the retired selector modality."""
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))
    for slug in ("game-developer", "artist", "technical-artist", "advanced"):
        response = client.get(f"/stories/{slug}", follow_redirects=False)
        assert response.status_code == 303
        assert urlparse(response.headers["location"]).path == "/"
