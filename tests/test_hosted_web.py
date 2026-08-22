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
    assert "Show me what you made." in entry.text
    assert "Choose the untouched GLB" in entry.text
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
    assert "Measured, target not yet agreed." in measured.text
    assert (
        "No policy findings, repair plan, approval, mutation, or readiness result exists yet."
        in measured.text
    )
    assert "Job Contract" in measured.text
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
    assert "One physical change needs your decision." in pending.text
    assert "Approve exact plan" in pending.text
    assert "Typing approval language cannot authorize this action." in pending.text
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
    assert "The verified package is ready." in completed.text
    assert "Download result ZIP" in completed.text

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
    assert "One quick answer before I can propose the target." in clarification.text
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
    assert "I have enough information. Is this target right?" in proposal.text
    assert "Static game asset" in proposal.text
    assert "1.8 m" in proposal.text
    assert 'name="target_height_m"' not in proposal.text
