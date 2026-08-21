"""M8 acceptance tests for the local upload-to-download web product."""

# pygltflib is typed internally but does not publish PEP 561 metadata.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

import re
from pathlib import Path
from urllib.parse import urlparse
from zipfile import ZipFile

from fastapi.testclient import TestClient
from pygltflib import Skin

from asset_shepherd.glb import load_glb, save_glb
from asset_shepherd.models import Decisions, DecisionValue
from asset_shepherd.web import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BROKEN_PATH = PROJECT_ROOT / "fixtures" / "broken_robot.glb"
CLEAN_PATH = PROJECT_ROOT / "fixtures" / "clean_robot.glb"
PROFILE_ID = "unreal-indie-robot-v1"
PACKAGE_NAMES = {
    "decisions.json",
    "inspection.json",
    "provenance.json",
    "repair_plan.json",
    "report.md",
    "repaired.glb",
    "verification.json",
}


def _upload(client: TestClient, source: Path, profile_id: str = PROFILE_ID) -> str:
    """Upload one fixture and return its redirected local job path."""
    response = client.post(
        "/jobs",
        data={"profile_id": profile_id},
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


def test_web_broken_fixture_refresh_approve_and_download(tmp_path: Path) -> None:
    """A browser can refresh, approve by interrupt ID, preview, and download the result."""
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=tmp_path / "jobs"))
    job_path = _upload(client, BROKEN_PATH)

    pending = client.get(job_path)
    assert pending.status_code == 200
    assert "Approval needed" in pending.text
    assert "Normalize physical scale, upright orientation, and grounding" in pending.text
    interrupt_id = _interrupt_id(pending.text)
    pending_output = tmp_path / "jobs" / job_path.rsplit("/", 1)[-1] / "output"
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
    assert "Verified candidate" in completed.text
    assert "PASSED_WITH_REMAINING_WARNINGS" in completed.text
    assert "Download result ZIP" in completed.text
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


def test_web_clean_fixture_completes_twice_from_clean_app_starts(tmp_path: Path) -> None:
    """The clean no-approval path completes twice from independent application starts."""
    for run_number in range(2):
        work_root = tmp_path / f"clean-start-{run_number}"
        client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))
        job_path = _upload(client, CLEAN_PATH)
        completed = client.get(job_path)
        assert completed.status_code == 200
        assert "No project-policy findings." in completed.text
        assert "Verified candidate" in completed.text
        assert "Approval needed" not in completed.text
        assert "PASSED_PROJECT_READY" in completed.text
        assert client.get(f"{job_path}/download").status_code == 200


def test_web_rejects_non_glb_upload_without_starting_a_job(tmp_path: Path) -> None:
    """Invalid browser input gets a coherent intake error and no retained job."""
    work_root = tmp_path / "jobs"
    client = TestClient(create_app(project_root=PROJECT_ROOT, work_root=work_root))
    response = client.post(
        "/jobs",
        data={"profile_id": PROFILE_ID},
        files={"asset": ("not-a-model.glb", b"not a GLB", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "The upload is not a GLB 2.0 binary container." in response.text
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
    assert "INSPECTION_ONLY_UNSUPPORTED_FEATURES" in blocked.text
    assert "UNSUPPORTED_REPAIR_FEATURES" in blocked.text
    assert client.get(f"{job_path}/repaired.glb").status_code == 404
    assert skinned_path.read_bytes() == source_before

    archive_response = client.get(f"{job_path}/download")
    assert archive_response.status_code == 200
    archive_path = tmp_path / "blocked-result.zip"
    archive_path.write_bytes(archive_response.content)
    with ZipFile(archive_path) as archive:
        assert set(archive.namelist()) == PACKAGE_NAMES - {"repaired.glb"}
