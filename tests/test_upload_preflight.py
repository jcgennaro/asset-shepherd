"""Real asynchronous upload boundary and bounded, model-free preflight acceptance."""

import subprocess
from pathlib import Path
from threading import Event
from time import monotonic, sleep
from typing import cast
from unittest.mock import patch
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

from asset_shepherd.inspector import preflight_asset
from asset_shepherd.models import PreflightResult
from asset_shepherd.upload_preflight import UploadPreflight
from asset_shepherd.web import create_app

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "fixtures" / "broken_robot.glb"


def wait_ready(client: TestClient, status_url: str) -> dict[str, str]:
    """Poll a local receipt with a finite deadline, never a provider request."""
    deadline = monotonic() + 25
    while monotonic() < deadline:
        receipt = client.get(status_url).json()
        if receipt["state"] != "CHECKING":
            return receipt
        sleep(0.05)
    raise AssertionError("Local preflight did not finish")


def test_upload_returns_while_checking_and_blocks_intake_until_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A slow sensor cannot hold the upload response, health check, or status route open."""
    entered, release = Event(), Event()
    expected = preflight_asset(SOURCE)

    def slow_check(_self: UploadPreflight, _path: Path) -> PreflightResult:
        entered.set()
        assert release.wait(15)
        return expected

    monkeypatch.setattr(UploadPreflight, "_check", slow_check)
    work_root = tmp_path / "jobs"
    app = create_app(project_root=ROOT, work_root=work_root)
    client = TestClient(app)
    try:
        started = monotonic()
        response = client.post(
            "/workspace/new/upload",
            files={"asset": ("collar.glb", SOURCE.read_bytes())},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert monotonic() - started < 2
        assert entered.wait(2)
        describe = urlparse(response.headers["location"]).path
        status = describe.replace("/describe", "/upload-status")
        pending = client.get(describe)
        assert "Upload received—checking your asset" in pending.text
        assert "shepherd-sprite-thinking" in pending.text
        assert "No model is running yet" not in pending.text
        assert "Return to Gallery" not in pending.text
        assert 'aria-label="Asset Shepherd gallery"' in pending.text
        assert "data-tour-auto" not in pending.text
        assert 'name="description"' not in pending.text
        assert client.get("/healthz").status_code == 200
        assert client.get(status).json()["state"] == "CHECKING"
        with patch("asset_shepherd.web.build_target_intake_analyzer") as analyzer:
            assert (
                client.post(describe, data={"description": "A 1.8 m static robot."}).status_code
                == 409
            )
            analyzer.assert_not_called()
        busy = client.post(
            "/workspace/new/upload", files={"asset": ("second.glb", SOURCE.read_bytes())}
        )
        assert busy.status_code == 400
        assert "Another upload is being checked" in busy.text
    finally:
        release.set()
    assert wait_ready(client, status)["state"] == "READY"
    assert 'name="description"' in client.get(describe).text
    restored = TestClient(create_app(project_root=ROOT, work_root=work_root))
    assert restored.get(status).json()["state"] == "READY"
    # No second detailed sensor at the description-to-workspace boundary.
    with patch("asset_shepherd.hosted_workspace.preflight_asset", side_effect=AssertionError):
        created = restored.post(
            describe,
            data={
                "description": "A friendly humanoid robot intended as a 1.8 m static game asset."
            },
            follow_redirects=False,
        )
    assert created.status_code == 303


def test_real_upload_subprocess_and_cached_hash_binding(tmp_path: Path) -> None:
    """The production subprocess works, and a changed source cannot reuse its check."""
    work_root = tmp_path / "jobs"
    client = TestClient(create_app(project_root=ROOT, work_root=work_root))
    response = client.post(
        "/workspace/new/upload",
        files={"asset": (SOURCE.name, SOURCE.read_bytes())},
        follow_redirects=False,
    )
    describe = urlparse(response.headers["location"]).path
    assert wait_ready(client, describe.replace("/describe", "/upload-status"))["state"] == "READY"
    draft_id = describe.split("/")[-2]
    (work_root / "hosted-start" / draft_id / "source.glb").write_bytes(
        (ROOT / "fixtures" / "clean_robot.glb").read_bytes()
    )
    rejected = client.post(
        describe, data={"description": "A friendly humanoid robot, about 1.8 m tall."}
    )
    assert rejected.status_code == 400
    assert "saved asset check does not match" in rejected.text


def test_failed_and_interrupted_checks_have_explicit_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Timeouts and process restarts cannot leave a permanent checking spinner."""

    def timeout(_self: UploadPreflight, _source: Path) -> PreflightResult:
        raise subprocess.TimeoutExpired("preflight", 240)

    monkeypatch.setattr(UploadPreflight, "_check", timeout)
    # Hold execution so the HTTP route consistently returns its asynchronous receipt.
    work: list[object] = []
    monkeypatch.setattr(UploadPreflight, "_launch", staticmethod(work.append))
    work_root = tmp_path / "jobs"
    client = TestClient(create_app(project_root=ROOT, work_root=work_root))
    response = client.post(
        "/workspace/new/upload",
        files={"asset": (SOURCE.name, SOURCE.read_bytes())},
        follow_redirects=False,
    )
    describe = urlparse(response.headers["location"]).path
    restored = TestClient(create_app(project_root=ROOT, work_root=work_root))
    interrupted = restored.get(describe)
    assert "interrupted" in interrupted.text
    assert "Check uploaded file again" in interrupted.text
    retry = restored.post(describe.replace("/describe", "/check"), follow_redirects=False)
    assert retry.status_code == 303
    from collections.abc import Callable

    cast(Callable[[], None], work[-1])()
    failed = restored.get(describe)
    assert "exceeded four minutes" in failed.text
    assert 'name="description"' not in failed.text
    assert "Check uploaded file again" in failed.text
