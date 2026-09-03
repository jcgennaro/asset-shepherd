"""Browser-route acceptance for the D019 conversation-led workspace."""

import json
import re
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import cast
from unittest.mock import patch
from urllib.parse import urlparse
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

from asset_shepherd.agent_job import VerificationFunction
from asset_shepherd.glb import load_glb, save_glb
from asset_shepherd.hosted_workspace import HostedWorkspaceStore
from asset_shepherd.intake_analyzer import (
    TargetDimensionsInference,
    TargetIntakeInference,
    contract_from_inference,
)
from asset_shepherd.models import AssetTargetUse, VerificationResult, VerificationState
from asset_shepherd.repair import RepairOutcome
from asset_shepherd.target_intake import TargetIntakeContract
from asset_shepherd.web import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BROKEN_PATH = PROJECT_ROOT / "fixtures" / "broken_robot.glb"
DESCRIPTION = "A friendly humanoid robot intended as a 1.8 m static game asset."
PACKAGE_NAMES = {
    "decisions.json",
    "inspection.json",
    "provenance.json",
    "repair_plan.json",
    "report.md",
    "repaired.glb",
    "verification.json",
}


def test_upload_rejects_pathological_world_bounds_before_description(tmp_path: Path) -> None:
    """Objective extent-ratio rejection happens before target intake or agent work."""
    pathological_path = tmp_path / "pathological-bounds.glb"
    gltf = load_glb(PROJECT_ROOT / "fixtures" / "clean_robot.glb")
    assert gltf.scenes is not None
    scene_nodes = gltf.scenes[gltf.scene].nodes
    assert scene_nodes is not None
    assert gltf.nodes is not None
    root_index = scene_nodes[0]
    gltf.nodes[root_index].scale = [100_000.0, 1.0, 1.0]
    save_glb(gltf, pathological_path)
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))

    response = client.post(
        "/workspace/new/upload",
        files={
            "asset": (
                pathological_path.name,
                pathological_path.read_bytes(),
                "model/gltf-binary",
            )
        },
    )

    assert response.status_code == 400
    assert "too disproportionate to shepherd" in response.text
    assert "limit 10,000x" in response.text
    assert "/describe" not in response.url.path


def test_bedrock_upload_offers_only_hinted_models_and_persists_the_choice(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Model selection is compact, allowlisted, and durable across the upload boundary."""
    monkeypatch.setenv("ASSET_SHEPHERD_MODEL_PROVIDER", "bedrock-converse")
    monkeypatch.setenv("ASSET_SHEPHERD_INTAKE_PROVIDER", "bedrock-converse")
    monkeypatch.setenv("ASSET_SHEPHERD_MODEL_ID", "moonshotai.kimi-k2.5")
    monkeypatch.setenv("ASSET_SHEPHERD_AWS_REGION", "us-east-1")
    work_root = tmp_path / "jobs"
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))

    upload = client.get("/workspace/new/upload")

    assert upload.status_code == 200
    assert "Agent model: <span" in upload.text
    assert upload.text.count("Recommended") == 1
    assert "Kimi K2.5" in upload.text
    assert "Claude Haiku 4.5" in upload.text
    assert "Mistral Large 3" in upload.text
    assert "Qwen3 VL 235B" in upload.text
    assert "Nova 2 Lite" in upload.text
    assert "try when visual evidence is the main uncertainty" in upload.text
    assert "compare repair quality and cost" in upload.text
    assert "Lower-cost diagnostic" in upload.text

    uploaded = client.post(
        "/workspace/new/upload",
        data={"agent_model": "mistral.mistral-large-3-675b-instruct"},
        files={"asset": (BROKEN_PATH.name, BROKEN_PATH.read_bytes(), "model/gltf-binary")},
        follow_redirects=False,
    )

    assert uploaded.status_code == 303
    draft_id = urlparse(uploaded.headers["location"]).path.split("/")[-2]
    draft = (work_root / "hosted-start" / draft_id / "draft.json").read_text(encoding="utf-8")
    assert '"model_id": "mistral.mistral-large-3-675b-instruct"' in draft


def test_bedrock_upload_rejects_a_model_outside_the_allowlist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A posted arbitrary Bedrock model ID cannot bypass the visible selector."""
    monkeypatch.setenv("ASSET_SHEPHERD_MODEL_PROVIDER", "bedrock-converse")
    monkeypatch.setenv("ASSET_SHEPHERD_MODEL_ID", "moonshotai.kimi-k2.5")
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))

    response = client.post(
        "/workspace/new/upload",
        data={"agent_model": "some-provider.unreviewed-model"},
        files={"asset": (BROKEN_PATH.name, BROKEN_PATH.read_bytes(), "model/gltf-binary")},
    )

    assert response.status_code == 400
    assert "Choose an available Asset Shepherd model." in response.text


def test_describe_notebook_can_replace_its_uploaded_cell_without_losing_a_valid_draft(
    tmp_path: Path,
) -> None:
    """Editing Upload validates the replacement before retiring the prior staged source."""
    work_root = tmp_path / "jobs"
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))
    uploaded = client.post(
        "/workspace/new/upload",
        files={"asset": (BROKEN_PATH.name, BROKEN_PATH.read_bytes(), "model/gltf-binary")},
        follow_redirects=False,
    )
    old_draft_id = urlparse(uploaded.headers["location"]).path.split("/")[-2]
    replacement_path = PROJECT_ROOT / "fixtures" / "clean_robot.glb"

    invalid = client.post(
        "/workspace/new/upload",
        data={"replace_draft_id": old_draft_id},
        files={"asset": ("broken.glb", b"not a GLB", "application/octet-stream")},
    )
    assert invalid.status_code == 400
    assert (work_root / "hosted-start" / old_draft_id / "source.glb").is_file()

    replaced = client.post(
        "/workspace/new/upload",
        data={"replace_draft_id": old_draft_id},
        files={
            "asset": (
                replacement_path.name,
                replacement_path.read_bytes(),
                "model/gltf-binary",
            )
        },
        follow_redirects=False,
    )

    assert replaced.status_code == 303
    new_draft_id = urlparse(replaced.headers["location"]).path.split("/")[-2]
    assert new_draft_id != old_draft_id
    assert not (work_root / "hosted-start" / old_draft_id).exists()
    assert (work_root / "hosted-start" / new_draft_id / "source.glb").read_bytes() == (
        replacement_path.read_bytes()
    )


def _hidden(html: str, name: str) -> str:
    match = re.search(rf'name="{name}" value="([^"]+)"', html)
    assert match is not None
    return match.group(1)


def test_completed_turn_scene_is_lazy_and_hash_bound(tmp_path: Path) -> None:
    """A notebook turn loads one archived GLB only through its exact recorded hash."""
    app = create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs")
    hosted_store = cast(HostedWorkspaceStore, app.state.hosted_workspace_store)
    workspace = hosted_store.create(
        DESCRIPTION,
        BROKEN_PATH.name,
        BytesIO(BROKEN_PATH.read_bytes()),
    )
    archived = workspace.root / "turns" / "turn-000" / "output" / "repaired.glb"
    archived.parent.mkdir(parents=True)
    archived.write_bytes((PROJECT_ROOT / "fixtures" / "clean_robot.glb").read_bytes())
    output_sha256 = sha256(archived.read_bytes()).hexdigest()
    (workspace.root / "conversation.json").write_text(
        f'{{"schema_version":1,"turns":[{{"turn_index":0,"output_sha256":"{output_sha256}"}}]}}',
        encoding="utf-8",
    )
    client = TestClient(app)
    base = f"/workspace/{workspace.record.workspace_id}/turns/0"

    scene = client.get(f"{base}/scene")

    assert scene.status_code == 200
    assert scene.text.count("<model-viewer") == 1
    assert 'class="model-comparison source-only"' in scene.text
    assert f"{base}/model.glb" in scene.text
    asset = client.get(f"{base}/model.glb")
    assert asset.status_code == 200
    assert asset.content == archived.read_bytes()


def test_conversation_route_preflights_then_survives_restart_through_download(
    tmp_path: Path,
) -> None:
    """The hosted UI keeps one conversation and Job Contract across application restarts."""
    work_root = tmp_path / "jobs"
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))

    entry = client.get("/workspace")
    assert entry.status_code == 200
    thinking_sprite = client.get("/static/asset-shepherd-thinking.png")
    assert thinking_sprite.status_code == 200
    assert thinking_sprite.headers["content-type"] == "image/png"
    assert thinking_sprite.content.startswith(b"\x89PNG\r\n\x1a\n")
    running_sprite = client.get("/static/asset-shepherd-run-away.png")
    assert running_sprite.status_code == 200
    assert running_sprite.headers["content-type"] == "image/png"
    assert running_sprite.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert "Asset Shepherd -- Gallery" in entry.text
    assert '<span class="shepherd-sprite" aria-hidden="true"></span>' in entry.text
    assert "shepherd-sprite-idle" not in entry.text
    assert 'class="workspace-logo"' in entry.text
    assert 'class="rail-logo"' not in entry.text
    assert "New asset" in entry.text
    assert "Model description" not in entry.text
    assert "Choose or drop your GLB" not in entry.text
    assert ">Gallery</strong>" in entry.text
    assert ">Workflow</strong>" in entry.text
    assert 'aria-label="Workflow steps"' not in entry.text
    assert "Use the form-led reference workflow instead" not in entry.text
    assert "durable workspace" not in entry.text
    assert "only your description is sent" not in entry.text
    assert entry.text.count('data-focus-area="') == 1

    upload = client.get("/workspace/new/upload")
    assert upload.status_code == 200
    assert "Choose or drop your GLB" in upload.text
    assert "Model description" not in upload.text
    assert "Upload the GLB you want me to shepherd." in upload.text
    assert 'class="conversation-prompt agent-message"' in upload.text
    assert "What about FBX?" in upload.text
    assert "FBX support is in development" in upload.text
    assert upload.text.count("<h1") == 1
    assert "<h2" not in upload.text
    assert "<h3" not in upload.text

    uploaded = client.post(
        "/workspace/new/upload",
        files={"asset": (BROKEN_PATH.name, BROKEN_PATH.read_bytes(), "model/gltf-binary")},
        follow_redirects=False,
    )
    assert uploaded.status_code == 303
    describe_path = urlparse(uploaded.headers["location"]).path
    describe = client.get(describe_path)
    assert 'class="asset-description-label"' not in describe.text
    assert 'aria-label="Model description"' in describe.text
    assert "Choose or drop your GLB" not in describe.text
    assert "Describe the model you\u2019re working on." in describe.text
    assert 'class="conversation-prompt agent-message"' in describe.text
    assert "Show description examples" in describe.text
    assert "data-description-examples-dialog" in describe.text
    assert '<details class="description-help">' not in describe.text
    assert "Shepherd this asset" in describe.text
    assert 'data-busy-message="Reading your description and drafting a target…"' in describe.text
    assert describe.text.count("<h1") == 1
    assert "<h2" not in describe.text
    assert "<h3" not in describe.text
    assert 'class="model-comparison source-only"' in describe.text
    assert describe.text.count("<model-viewer") == 1
    assert 'class="evidence-sidebar"' in describe.text
    assert "data-notebook-scene-host" in describe.text
    assert f"{describe_path.rsplit('/describe', 1)[0]}/source.glb" in describe.text
    assert describe.text.count('data-comparison-target="before"') == 1
    assert 'data-comparison-target="after"' not in describe.text
    assert describe.text.count('data-comparison-origin="before"') == 1
    assert 'slot="hotspot-before-origin" data-position="0m 0m 0m"' in describe.text
    assert 'rotation-per-second="4deg"' in describe.text
    assert 'id="notebook-upload"' in describe.text
    assert 'id="notebook-describe"' in describe.text
    assert describe.text.index('id="notebook-upload"') < describe.text.index(
        'id="notebook-describe"'
    )
    assert f"Uploaded {BROKEN_PATH.name}." in describe.text
    assert "The GLB parsed successfully at" in describe.text
    assert 'name="replace_draft_id"' in describe.text

    created = client.post(
        describe_path,
        data={"description": DESCRIPTION},
        follow_redirects=False,
    )
    assert created.status_code == 303
    workspace_path = urlparse(created.headers["location"]).path
    workspace_id = workspace_path.rsplit("/", 1)[-1]

    measured = client.get(workspace_path)
    assert measured.status_code == 200
    assert "shepherd this for Unspecified endpoint within 1.8 x 1.8 x 1.8 m." in measured.text
    assert measured.text.count('class="expectation-group"') == 3
    assert "Start shepherding" in measured.text
    assert "How closely will this asset normally be viewed?" in measured.text
    assert "Hero / close-up" in measured.text
    assert "Normal gameplay" in measured.text
    assert "Background / repeated" in measured.text
    assert 'name="viewing_use" value="NORMAL_GAMEPLAY" required checked' in measured.text
    assert "data-viewing-use-help-dialog" in measured.text
    assert "Up to 50,000 triangles" in measured.text
    assert "Up to 15,000 triangles" in measured.text
    assert "Up to 2,500 triangles" in measured.text
    assert "<summary>Change target…</summary>" in measured.text
    assert 'textarea class="asset-description-input"' in measured.text
    assert 'class="asset-description-field"' in measured.text
    assert "data-confirmation-decision" in measured.text
    assert 'class="evidence-sidebar"' in measured.text
    assert "data-notebook-scene-host" in measured.text
    assert "&amp;amp;" not in measured.text
    assert "Job details" in measured.text
    assert 'class="model-comparison source-only"' in measured.text
    assert measured.text.count("<model-viewer") == 1
    assert "data-job-contract-dialog" in measured.text
    assert "Rules are derived only after target confirmation." in measured.text
    assert not (work_root / "hosted" / workspace_id / "output").exists()
    assert measured.text.index('id="notebook-upload"') < measured.text.index(
        'id="notebook-describe"'
    )
    assert 'data-activity-step="3"' in measured.text
    assert 'data-activity-label="Shepherd"' in measured.text
    assert f"Uploaded {BROKEN_PATH.name}." in measured.text
    assert f"{workspace_path}/redo" not in measured.text
    command_id = _hidden(measured.text, "command_id")

    confirmed = client.post(
        f"{workspace_path}/target",
        data={
            "command_id": command_id,
            "viewing_use": "NORMAL_GAMEPLAY",
        },
        follow_redirects=False,
    )
    assert confirmed.status_code == 303
    frozen_profile = (work_root / "hosted" / workspace_id / "profile.json").read_text(
        encoding="utf-8"
    )
    assert '"max_triangles":15000' in frozen_profile.replace(" ", "")
    pending = client.get(workspace_path)
    assert "Asset Shepherd -- Friendly Humanoid Robot" in pending.text
    assert pending.text.count("data-inspection-check") == 5
    assert "6 complete" not in pending.text
    assert "More details" not in pending.text
    assert 'class="inspection-table"' not in pending.text
    assert pending.text.count('class="inspection-lane-table"') == 1
    assert 'class="approval-change"' not in pending.text
    assert "Proposed action" in pending.text
    assert "Approval required" in pending.text
    assert "Mesh detail preserved" in pending.text
    assert "15,000-triangle normal gameplay soft cap" in pending.text
    assert "Display names" in pending.text
    assert "Repair plan" not in pending.text
    assert "Confirmed the proposed target." in pending.text
    assert pending.text.index('id="notebook-upload"') < pending.text.index('id="notebook-describe"')
    assert pending.text.index('id="notebook-describe"') < pending.text.index(
        "data-current-workflow-cell"
    )
    assert f"{workspace_path}/source-scene" in pending.text
    source_scene = client.get(f"{workspace_path}/source-scene")
    assert source_scene.status_code == 200
    assert source_scene.text.count("<model-viewer") == 1
    assert f"{workspace_path}/uploaded.glb" in source_scene.text
    assert client.get(f"{workspace_path}/uploaded.glb").content == BROKEN_PATH.read_bytes()
    assert pending.text.count('data-tooltip="') == 5
    assert "The original file remains untouched." not in pending.text
    assert "Ask from recorded evidence" not in pending.text
    assert "VERTEX REPRESENTATION" in pending.text
    assert "expected attribute-seam splits" in pending.text
    assert "POSITION TOPOLOGY" in pending.text
    assert "protected seams" not in pending.text
    assert ">Approve <" in pending.text
    assert "data-activity-url=" in pending.text
    assert f"{workspace_path}/activity" in pending.text
    activity = client.get(f"{workspace_path}/activity")
    assert activity.status_code == 200
    activity_payload = activity.json()
    assert activity_payload["state"] == "WAITING"
    assert any(item["label"] == "Measuring the GLB" for item in activity_payload["items"])
    assert all("reasoning" not in item for item in activity_payload["items"])
    interrupt_id = _hidden(pending.text, "interrupt_id")
    decision_command = _hidden(pending.text, "command_id")

    restarted = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))
    resumed = restarted.get(workspace_path)
    assert resumed.status_code == 200
    assert _hidden(resumed.text, "interrupt_id") == interrupt_id

    approved = restarted.post(
        f"{workspace_path}/decision",
        data={
            "interrupt_id": interrupt_id,
            "decision": "approve",
            "command_id": decision_command,
        },
        follow_redirects=False,
    )
    assert approved.status_code == 303
    completed = restarted.get(workspace_path)
    assert 'class="conversation-prompt agent-message completion-prompt"' in completed.text
    assert completed.text.count("Asset Shepherd says:") == 1
    assert 'class="result-status' not in completed.text
    assert "Action taken" in completed.text
    assert "Proposed action" not in completed.text
    assert completed.text.count("!→✓") == 2
    assert "Addressed —" in completed.text
    assert "Applied —" in completed.text
    assert "Use this version" in completed.text
    assert "data-result-accepted hidden" in completed.text
    assert 'id="notebook-download"' in completed.text
    assert "Download fixed model" in completed.text
    assert "Evidence package" in completed.text
    assert f"{workspace_path}/redo" in completed.text
    assert completed.text.count("<summary>Rewind…</summary>") == 2
    assert "data-model-comparison" in completed.text
    assert completed.text.count("<model-viewer") == 1
    offsets = re.findall(r'<extra-model[^>]+offset="([^"]+)"', completed.text)
    assert len(offsets) == 2
    assert all("m" not in offset for offset in offsets)
    assert "normal-size 20 cm banana" in completed.text
    assert "Confirmed the proposed target." in completed.text
    assert completed.text.index('id="notebook-upload"') < completed.text.index(
        'id="notebook-describe"'
    )
    assert completed.text.index('id="notebook-describe"') < completed.text.index(
        "data-current-workflow-cell"
    )
    completed_activity = restarted.get(f"{workspace_path}/activity").json()
    assert completed_activity["state"] == "COMPLETE"
    assert completed_activity["items"][-1]["label"] == "Verifying and packaging the result"

    acceptance_command = _hidden(completed.text, "command_id")
    accepted = restarted.post(
        f"{workspace_path}/result",
        data={"decision": "accept", "command_id": acceptance_command},
        headers={"X-Asset-Shepherd-Transition": "accept"},
        follow_redirects=False,
    )
    assert accepted.status_code == 204
    accepted_page = restarted.get(workspace_path)
    assert "Use this version" not in accepted_page.text
    assert "data-result-accepted hidden" not in accepted_page.text
    assert "The current version is ready to download." in accepted_page.text
    assert "data-current-workflow-cell" not in accepted_page.text
    assert 'class="workflow-cell download-workflow-cell current"' in accepted_page.text
    assert "Return to gallery" in accepted_page.text
    assert 'class="gallery-return-sprite"' in accepted_page.text
    assert 'class="gallery-return-icon" aria-hidden="true">↵</span>' in accepted_page.text

    with patch(
        "asset_shepherd.hosted_workspace.build_live_agent",
        side_effect=AssertionError("accepted workspace attempted a live-model restore"),
    ):
        terminal_restart = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))
        reopened_terminal = terminal_restart.get(workspace_path)
    assert reopened_terminal.status_code == 200
    assert "Return to gallery" in reopened_terminal.text
    assert "Download fixed model" in reopened_terminal.text
    assert terminal_restart.get(f"{workspace_path}/repaired.glb").status_code == 200
    assert terminal_restart.get(f"{workspace_path}/download").status_code == 200

    archive_response = restarted.get(f"{workspace_path}/download")
    assert archive_response.status_code == 200
    archive_path = tmp_path / "hosted-result.zip"
    archive_path.write_bytes(archive_response.content)
    with ZipFile(archive_path) as archive:
        assert set(archive.namelist()) == PACKAGE_NAMES

    duplicate = restarted.post(
        f"{workspace_path}/decision",
        data={
            "interrupt_id": interrupt_id,
            "decision": "approve",
            "command_id": decision_command,
        },
        follow_redirects=False,
    )
    assert duplicate.status_code == 303


def test_hosted_route_asks_only_for_missing_target_information(tmp_path: Path) -> None:
    """The hosted conversation clarifies one absent field before offering confirmation."""
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))
    created = client.post(
        "/workspace",
        data={"description": "A friendly robot intended as a static game asset."},
        files={"asset": (BROKEN_PATH.name, BROKEN_PATH.read_bytes(), "model/gltf-binary")},
        follow_redirects=False,
    )
    workspace_path = urlparse(created.headers["location"]).path

    clarification = client.get(workspace_path)
    assert "Enter the approximate target size." in clarification.text
    assert 'name="target_x_m"' in clarification.text
    assert 'name="target_y_m"' in clarification.text
    assert 'name="target_z_m"' in clarification.text
    assert 'name="target_use"' not in clarification.text
    command_id = _hidden(clarification.text, "command_id")

    answered = client.post(
        f"{workspace_path}/target/clarify",
        data={
            "target_x_m": "0.8",
            "target_y_m": "1.8",
            "target_z_m": "0.6",
            "command_id": command_id,
        },
        follow_redirects=False,
    )
    assert answered.status_code == 303
    proposal = client.get(workspace_path)
    assert "within 0.8 x 1.8 x 0.6 m." in proposal.text
    assert "<summary>Change target…</summary>" in proposal.text
    assert proposal.text.count('class="expectation-group"') == 3
    assert "1 expected semantic piece" in proposal.text
    assert "valid GLB required" not in proposal.text
    assert 'name="target_use"' not in proposal.text
    assert "What real-world height should it have?" not in proposal.text


def test_hosted_endpoint_clarification_collects_destination_and_viewing_use(
    tmp_path: Path,
) -> None:
    """A missing endpoint collects both global target choices in one responsive card."""

    class MissingEndpointAnalyzer:
        provider = "test"
        model_id = "semantic-test"

        def analyze(self, description: str) -> TargetIntakeContract:
            return contract_from_inference(
                description,
                TargetIntakeInference(
                    engagement_decision="PROCEED",
                    asset_name="Computer Chip",
                    target_use=AssetTargetUse.STATIC_GAME_ASSET,
                    target_use_confidence=0.99,
                    target_use_evidence="The chip is a static prop.",
                    endpoint=None,
                    endpoint_detail=None,
                    endpoint_confidence=0.2,
                    endpoint_evidence=None,
                    target_dimensions_cm=TargetDimensionsInference(
                        x_cm=5.0,
                        y_cm=2.0,
                        z_cm=5.0,
                    ),
                    target_dimensions_confidence=0.99,
                    target_dimensions_evidence="The description supplies approximate dimensions.",
                    expected_piece_count=1,
                    expected_piece_count_evidence="The description identifies one chip.",
                ),
                provider=self.provider,
                model_id=self.model_id,
            )

    client = TestClient(
        create_app(
            project_root=PROJECT_ROOT,
            work_root=tmp_path / "jobs",
            intake_analyzer=MissingEndpointAnalyzer(),
        )
    )
    uploaded = client.post(
        "/workspace/new/upload",
        files={"asset": (BROKEN_PATH.name, BROKEN_PATH.read_bytes(), "model/gltf-binary")},
        follow_redirects=False,
    )
    describe_path = urlparse(uploaded.headers["location"]).path
    created = client.post(
        describe_path,
        data={"description": "A computer chip about 5 by 5 by 2 cm."},
        follow_redirects=False,
    )
    workspace_path = urlparse(created.headers["location"]).path
    page = client.get(workspace_path)

    assert "Choose the target engine and how this asset will be viewed." in page.text
    assert "I need one" not in page.text
    assert 'aria-label="Explain target engines"' in page.text
    assert "What the target changes" in page.text
    assert "Asset Shepherd still returns a GLB." in page.text
    assert "proprietary-format conversion" in page.text
    assert page.text.count('class="endpoint-option"') == 4
    assert 'href="https://unity.com/"' in page.text
    assert 'href="https://www.unrealengine.com/"' in page.text
    assert 'href="https://godotengine.org/"' in page.text
    assert "endpoint-orbit" in page.text
    assert "How closely will this asset normally be viewed?" in page.text
    assert "Hero / close-up" in page.text
    assert "Normal gameplay" in page.text
    assert "Background / repeated" in page.text
    assert 'name="viewing_use" value="NORMAL_GAMEPLAY" required checked' in page.text
    assert 'aria-label="Explain viewing use and mesh complexity"' in page.text
    assert "Up to 50,000 triangles" in page.text
    assert "Up to 15,000 triangles" in page.text
    assert "Up to 2,500 triangles" in page.text
    assert "Choose by use case." not in page.text
    assert 'name="endpoint_detail"' in page.text
    assert "data-endpoint-detail" in page.text
    assert 'aria-label="Current uploaded 3D target preview"' in page.text

    answered = client.post(
        f"{workspace_path}/target/clarify",
        data={
            "command_id": _hidden(page.text, "command_id"),
            "endpoint": "UNREAL",
            "endpoint_detail": "stale restored browser value",
            "viewing_use": "SMALL_DISTANT_REPEATED",
        },
        follow_redirects=False,
    )
    assert answered.status_code == 303
    reviewed = client.get(workspace_path)
    assert 'name="viewing_use"' not in reviewed.text
    assert "How closely will this asset normally be viewed?" not in reviewed.text
    assert "Start shepherding" in reviewed.text
    saved_target = json.loads(
        (
            tmp_path / "jobs" / "hosted" / workspace_path.rsplit("/", 1)[-1] / "target_intake.json"
        ).read_text(encoding="utf-8")
    )
    assert saved_target["endpoint"] == "UNREAL"
    assert saved_target["endpoint_detail"] is None


def test_upload_preflight_rejects_an_invalid_glb_before_description(tmp_path: Path) -> None:
    """Upload-first intake cannot ask for intent after the source boundary already failed."""
    work_root = tmp_path / "jobs"
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))

    rejected = client.post(
        "/workspace/new/upload",
        files={"asset": ("broken.glb", b"not a GLB", "application/octet-stream")},
    )

    assert rejected.status_code == 400
    assert "The upload is not a GLB 2.0 binary container." in rejected.text
    assert "Model description" not in rejected.text
    assert "Upload the GLB you want me to shepherd." in rejected.text
    assert not tuple(work_root.rglob("source.glb"))


def test_invalid_upload_fixture_set_fails_concisely_before_agent_work(tmp_path: Path) -> None:
    """Malformed GLBs and unsupported FBX fail at the appropriate upload boundary."""
    work_root = tmp_path / "jobs"
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))
    fixture_root = PROJECT_ROOT / "fixtures" / "invalid_uploads"
    cases = (
        ("tiny-gibberish.glb", "The upload is not a GLB 2.0 binary container."),
        (
            "truncated-clean-robot.glb",
            "This GLB is damaged or incomplete and could not be read.",
        ),
        (
            "invalid-json-chunk.glb",
            "This GLB is damaged or incomplete and could not be read.",
        ),
        ("minimal-ascii.fbx", "Choose exactly one file with a .glb extension."),
    )

    for filename, expected_message in cases:
        path = fixture_root / filename
        assert path.stat().st_size < 1024
        response = client.post(
            "/workspace/new/upload",
            files={"asset": (filename, path.read_bytes(), "application/octet-stream")},
        )
        assert response.status_code == 400
        assert expected_message in response.text
        assert "Model description" not in response.text
        assert "Upload the GLB you want me to shepherd." in response.text

    assert not tuple(work_root.rglob("source.glb"))


def test_workspace_gallery_names_and_resumes_isolated_asset_state(tmp_path: Path) -> None:
    """Gallery cards use intake names and return each asset to its own persisted phase."""
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))
    created_paths: list[str] = []
    for description in (
        DESCRIPTION,
        "A compact service robot intended as a 1.2 m static game asset.",
    ):
        created = client.post(
            "/workspace",
            data={"description": description},
            files={"asset": (BROKEN_PATH.name, BROKEN_PATH.read_bytes(), "model/gltf-binary")},
            follow_redirects=False,
        )
        created_paths.append(urlparse(created.headers["location"]).path)

    first_page = client.get(created_paths[0])
    client.post(
        f"{created_paths[0]}/target",
        data={"command_id": _hidden(first_page.text, "command_id")},
        follow_redirects=False,
    )

    gallery = client.get("/workspace")
    assert "Friendly Humanoid Robot" in gallery.text
    assert "Compact Service Robot" in gallery.text
    assert BROKEN_PATH.name not in gallery.text
    assert all(path in gallery.text for path in created_paths)
    assert gallery.text.count('class="asset-gallery-card"') == 2
    assert gallery.text.count("<model-viewer") == 2
    assert gallery.text.count('class="asset-redo"') == 2
    assert 'class="asset-gallery-status attention"' in gallery.text
    assert "Step 3 · Review" in gallery.text
    assert 'class="asset-gallery-status pending"' in gallery.text
    assert "Step 2 · Describe" in gallery.text
    assert "Target Confirmation" not in gallery.text

    resumed_first = client.get(created_paths[0])
    resumed_second = client.get(created_paths[1])
    assert "Approve" in resumed_first.text
    assert "Start shepherding" in resumed_second.text
    assert ">Gallery</a>" in resumed_first.text


def test_gallery_redo_reuses_source_and_preserves_saved_run_until_submit(
    tmp_path: Path,
) -> None:
    """Redo starts from the saved GLB while the prior resumable state remains intact."""
    work_root = tmp_path / "jobs"
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))
    created = client.post(
        "/workspace",
        data={"description": DESCRIPTION},
        files={"asset": (BROKEN_PATH.name, BROKEN_PATH.read_bytes(), "model/gltf-binary")},
        follow_redirects=False,
    )
    workspace_path = urlparse(created.headers["location"]).path
    redo = client.post(f"{workspace_path}/redo", follow_redirects=False)
    assert redo.status_code == 303
    describe_path = urlparse(redo.headers["location"]).path
    describe = client.get(describe_path)
    assert DESCRIPTION in describe.text
    assert client.get(workspace_path).status_code == 200
    gallery = client.get("/workspace")
    assert "Continue redo" in gallery.text
    assert describe_path in gallery.text

    restarted = client.post(
        describe_path,
        data={"description": DESCRIPTION},
        follow_redirects=False,
    )
    assert restarted.status_code == 303
    restarted_path = urlparse(restarted.headers["location"]).path
    assert restarted_path != workspace_path
    assert client.get(workspace_path).status_code == 404
    assert client.get(restarted_path).status_code == 200
    assert client.get(f"{restarted_path}/source.glb").content == BROKEN_PATH.read_bytes()


def test_uploaded_description_draft_resumes_from_gallery_after_restart(tmp_path: Path) -> None:
    """Leaving after upload preserves the GLB and the exact description step."""
    work_root = tmp_path / "jobs"
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))
    uploaded = client.post(
        "/workspace/new/upload",
        files={"asset": (BROKEN_PATH.name, BROKEN_PATH.read_bytes(), "model/gltf-binary")},
        follow_redirects=False,
    )
    describe_path = urlparse(uploaded.headers["location"]).path

    gallery = client.get("/workspace")
    assert "Broken Robot" in gallery.text
    assert "Step 2 · Describe" in gallery.text
    assert 'class="asset-gallery-status pending"' in gallery.text
    assert describe_path in gallery.text

    restarted = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))
    restarted_gallery = restarted.get("/workspace")
    assert describe_path in restarted_gallery.text
    assert restarted.get(describe_path).status_code == 200
    draft_id = describe_path.split("/")[-2]
    assert (
        restarted.get(f"/workspace/new/{draft_id}/source.glb").content == BROKEN_PATH.read_bytes()
    )


def test_full_gallery_requires_visible_replacement_choice(tmp_path: Path) -> None:
    """The eighth upload UI makes replacement explicit instead of evicting silently."""
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))
    for index in range(7):
        created = client.post(
            "/workspace",
            data={
                "description": (
                    f"A friendly robot number {index} intended as a 1.8 m static game asset."
                )
            },
            files={"asset": (BROKEN_PATH.name, BROKEN_PATH.read_bytes(), "model/gltf-binary")},
            follow_redirects=False,
        )
        assert created.status_code == 303

    gallery = client.get("/workspace")
    assert gallery.text.count('class="asset-gallery-card"') == 7
    assert gallery.text.count('class="asset-replace"') == 7
    assert "New asset" not in gallery.text

    replace_path = re.search(r'href="([^"]+replace_workspace_id=[^"]+)"', gallery.text)
    assert replace_path is not None
    replacement = client.get(replace_path.group(1))
    assert replacement.status_code == 200
    assert 'name="replace_workspace_id"' in replacement.text
    assert "Choose or drop your GLB" in replacement.text
    assert "Model description" not in replacement.text


def test_rejected_candidate_remains_downloadable_before_human_acceptance(
    tmp_path: Path,
) -> None:
    """Automated rejection removes the verified label, not the user's candidate file."""

    def reject_verification(*args: object) -> VerificationResult:
        outcome = cast(RepairOutcome, args[6])
        return VerificationResult(
            verification_id="verification-forced-rejection-v1",
            source_sha256=outcome.source_sha256,
            output_sha256=outcome.output_sha256,
            state=VerificationState.FAILED,
            checks=(),
            remaining_warnings=("FORCED_TEST_REJECTION",),
            second_plan_candidate_count=1,
        )

    app = create_app(
        project_root=PROJECT_ROOT,
        work_root=tmp_path / "jobs",
        verification_function=cast(VerificationFunction, reject_verification),
    )
    client = TestClient(app)
    uploaded = client.post(
        "/workspace/new/upload",
        files={"asset": (BROKEN_PATH.name, BROKEN_PATH.read_bytes(), "model/gltf-binary")},
        follow_redirects=False,
    )
    describe_path = urlparse(uploaded.headers["location"]).path
    created = client.post(
        describe_path,
        data={"description": "A 1.8 m friendly humanoid robot static game asset."},
        follow_redirects=False,
    )
    workspace_path = urlparse(created.headers["location"]).path
    workspace_id = workspace_path.rsplit("/", 1)[-1]
    proposal = client.get(workspace_path)
    client.post(
        f"{workspace_path}/target",
        data={"command_id": _hidden(proposal.text, "command_id")},
        follow_redirects=False,
    )

    hosted_store = cast(HostedWorkspaceStore, app.state.hosted_workspace_store)
    workspace = hosted_store.get(workspace_id)
    assert workspace is not None and workspace.runtime is not None

    pending = client.get(workspace_path)
    completed = client.post(
        f"{workspace_path}/decision",
        data={
            "interrupt_id": _hidden(pending.text, "interrupt_id"),
            "decision": "approve",
            "command_id": _hidden(pending.text, "command_id"),
        },
        follow_redirects=False,
    )
    assert completed.status_code == 303

    result = client.get(workspace_path)
    assert "Action taken" in result.text
    assert "Attempted — verification did not confirm" in result.text
    assert "!→✓" not in result.text
    assert "Use this version" in result.text
    assert "Download candidate" in result.text
    assert "data-result-accepted hidden" in result.text
    candidate = client.get(f"{workspace_path}/candidate-preview.glb")
    assert candidate.status_code == 200
    assert candidate.headers["content-type"] == "model/gltf-binary"
    assert candidate.headers["content-disposition"].endswith('-candidate.glb"')
    assert candidate.content == workspace.runtime.job.candidate_path.read_bytes()
