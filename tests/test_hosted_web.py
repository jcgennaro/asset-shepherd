"""Browser-route acceptance for the D019 conversation-led workspace."""

import re
from pathlib import Path
from urllib.parse import urlparse
from zipfile import ZipFile

from fastapi.testclient import TestClient

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


def _hidden(html: str, name: str) -> str:
    match = re.search(rf'name="{name}" value="([^"]+)"', html)
    assert match is not None
    return match.group(1)


def test_conversation_route_preflights_then_survives_restart_through_download(
    tmp_path: Path,
) -> None:
    """The hosted UI keeps one conversation and Job Contract across application restarts."""
    work_root = tmp_path / "jobs"
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))

    entry = client.get("/workspace")
    assert entry.status_code == 200
    assert "Describe the model you\u2019re working on." in entry.text
    assert "Use the form-led reference workflow instead" not in entry.text
    assert "durable workspace" not in entry.text
    assert "only your description is sent" not in entry.text
    assert "One GLB · up to 50 MB" in entry.text
    assert "Choose or drop your GLB" in entry.text
    assert "Shepherd this asset" in entry.text
    assert "Measure my asset" not in entry.text
    assert entry.text.count('data-focus-area="') == 1

    created = client.post(
        "/workspace",
        data={"description": DESCRIPTION},
        files={"asset": (BROKEN_PATH.name, BROKEN_PATH.read_bytes(), "model/gltf-binary")},
        follow_redirects=False,
    )
    assert created.status_code == 303
    workspace_path = urlparse(created.headers["location"]).path
    workspace_id = workspace_path.rsplit("/", 1)[-1]

    measured = client.get(workspace_path)
    assert measured.status_code == 200
    assert "inspect this as a 1.8 m static game asset." in measured.text
    assert measured.text.count('class="expectation-group"') == 3
    assert "Did I get it right?" in measured.text
    assert "<summary>No</summary>" in measured.text
    assert ">Yes</button>" in measured.text
    assert 'textarea class="asset-description-input"' in measured.text
    assert 'class="asset-description-field"' in measured.text
    assert "data-confirmation-decision" in measured.text
    assert "&amp;amp;" not in measured.text
    assert "Job details" in measured.text
    assert "data-job-contract-dialog" in measured.text
    assert "Rules are derived only after target confirmation." in measured.text
    assert not (work_root / "hosted" / workspace_id / "output").exists()
    command_id = _hidden(measured.text, "command_id")

    confirmed = client.post(
        f"{workspace_path}/target",
        data={
            "command_id": command_id,
        },
        follow_redirects=False,
    )
    assert confirmed.status_code == 303
    pending = client.get(workspace_path)
    assert "Normalize scale, orientation, grounding:" in pending.text
    assert "Checking your GLB" in pending.text
    assert pending.text.count("data-inspection-check") == 6
    assert "More details" in pending.text
    assert re.search(r"\d+\.\d{3} m → 1\.800 m\?", pending.text)
    assert pending.text.count('class="approval-details"') == 1
    assert "The original file remains untouched." not in pending.text
    assert ">Approve <" in pending.text
    interrupt_id = _hidden(pending.text, "interrupt_id")
    decision_command = _hidden(pending.text, "command_id")

    restarted = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))
    resumed = restarted.get(workspace_path)
    assert resumed.status_code == 200
    assert _hidden(resumed.text, "interrupt_id") == interrupt_id

    asked = restarted.post(
        f"{workspace_path}/ask",
        data={"category": "authorization"},
        follow_redirects=False,
    )
    assert asked.status_code == 303
    still_pending = restarted.get(workspace_path)
    assert "Chat text cannot approve a repair." in still_pending.text
    assert _hidden(still_pending.text, "interrupt_id") == interrupt_id

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
    assert 'class="completion-heading"' in completed.text
    assert 'class="result-status' not in completed.text
    assert "Did we get it right?" in completed.text
    assert "data-result-accepted hidden" in completed.text
    assert "Download fixed model" in completed.text
    assert "Evidence package" in completed.text
    assert "data-model-comparison" in completed.text
    assert completed.text.count("<model-viewer") == 1
    offsets = re.findall(r'<extra-model[^>]+offset="([^"]+)"', completed.text)
    assert len(offsets) == 2
    assert all("m" not in offset for offset in offsets)
    assert "normal-size 20 cm banana" in completed.text

    acceptance_command = _hidden(completed.text, "command_id")
    accepted = restarted.post(
        f"{workspace_path}/result",
        data={"decision": "accept", "command_id": acceptance_command},
        headers={"X-Asset-Shepherd-Transition": "accept"},
        follow_redirects=False,
    )
    assert accepted.status_code == 204
    accepted_page = restarted.get(workspace_path)
    assert "Did we get it right?" not in accepted_page.text
    assert "data-result-accepted hidden" not in accepted_page.text
    assert "Ready to download." in accepted_page.text

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
    assert "About how tall should it be?" in clarification.text
    assert 'name="target_height_m"' in clarification.text
    assert 'name="target_use"' not in clarification.text
    command_id = _hidden(clarification.text, "command_id")

    answered = client.post(
        f"{workspace_path}/target/clarify",
        data={"target_height_m": "1.8", "command_id": command_id},
        follow_redirects=False,
    )
    assert answered.status_code == 303
    proposal = client.get(workspace_path)
    assert "inspect this as a 1.8 m static game asset." in proposal.text
    assert "1.8 m" in proposal.text
    assert "<summary>No</summary>" in proposal.text
    assert proposal.text.count('class="expectation-group"') == 3
    assert "No semantic piece-count assumption" in proposal.text
    assert 'name="target_use"' not in proposal.text
    assert "What real-world height should it have?" not in proposal.text


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

    resumed_first = client.get(created_paths[0])
    resumed_second = client.get(created_paths[1])
    assert "Approve" in resumed_first.text
    assert "Did I get it right?" in resumed_second.text


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
    assert 'name="replace_workspace_id" required' in gallery.text
    assert "Replace one existing asset" in gallery.text
