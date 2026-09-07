"""Permanent Gallery deletion, exact storage scope, and concurrency acceptance."""

from io import BytesIO
from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from asset_shepherd.agentcore_dispatch import AgentCoreCommandDispatcher, AgentCoreDispatchError
from asset_shepherd.hosted_workspace import HostedWorkspaceError, HostedWorkspaceStore
from asset_shepherd.web import create_app
from test_agentcore_dispatch import FakeSqs
from test_cloud_workspace import (
    CLEAN_PATH,
    DESCRIPTION,
    _FakeDynamo,  # pyright: ignore[reportPrivateUsage]
    _FakeS3,  # pyright: ignore[reportPrivateUsage]
    _family,  # pyright: ignore[reportPrivateUsage]
    _repository,  # pyright: ignore[reportPrivateUsage]
)


def test_cloud_trash_erases_artifacts_receipts_and_not_spending(tmp_path: Path) -> None:
    """Repeated short pages are exhausted; other assets and accounting are untouched."""
    s3, dynamo = _FakeS3(), _FakeDynamo()
    repository = _repository(s3, dynamo)
    store = HostedWorkspaceStore(tmp_path, _family(), workspace_repository=repository)
    asset = store.create(DESCRIPTION, "robot.glb", BytesIO(CLEAN_PATH.read_bytes()))
    workspace_id = asset.record.workspace_id
    s3.objects[f"sessions/session_{workspace_id}/session.json"] = b"conversation"
    s3.objects["workspaces/other/objects/keep"] = b"other"
    dynamo.items["spending"] = {"PK": {"S": "SPEND#2026-09-07"}}
    dynamo.items[f"COMMAND#{workspace_id}"] = {
        "PK": {"S": f"COMMAND#{workspace_id}"},
        "SK": {"S": "COMMAND#done"},
        "dispatch_owner": {"S": "contest-demo"},
    }
    store.trash(workspace_id)
    assert s3.objects == {"workspaces/other/objects/keep": b"other"}
    assert set(dynamo.items) == {"spending"}
    assert not asset.root.exists()
    assert store.get(workspace_id) is None
    assert store.list_records() == ()
    # An old cache cannot publish objects after the asset has been removed.
    before = dict(s3.objects)
    with pytest.raises(HostedWorkspaceError, match="trashed"):
        repository.persist(asset.root, asset.record.model_dump_json(), expected_version=1)
    assert s3.objects == before


def test_cloud_trash_waits_for_active_writer_and_checks_owner(tmp_path: Path) -> None:
    """A separate runtime lease or a different owner prevents any destructive action."""
    s3, dynamo = _FakeS3(), _FakeDynamo()
    repository = _repository(s3, dynamo)
    store = HostedWorkspaceStore(tmp_path, _family(), workspace_repository=repository)
    asset = store.create(DESCRIPTION, "robot.glb", BytesIO(CLEAN_PATH.read_bytes()))
    before = dict(s3.objects)
    other_process = _repository(s3, dynamo)
    with other_process.exclusive(asset.record.workspace_id):
        with pytest.raises(HostedWorkspaceError, match="busy"):
            store.trash(asset.record.workspace_id)
    repository.owner_id = "another-owner"
    with pytest.raises(HostedWorkspaceError, match="not accessible"):
        store.trash(asset.record.workspace_id)
    assert s3.objects == before


def test_partial_cloud_trash_can_be_retried(tmp_path: Path) -> None:
    """Cleanup failures retain a retryable pointer and fence reads and writes."""
    s3, dynamo = _FakeS3(), _FakeDynamo()
    repository = _repository(s3, dynamo)
    store = HostedWorkspaceStore(tmp_path, _family(), workspace_repository=repository)
    asset = store.create(DESCRIPTION, "robot.glb", BytesIO(CLEAN_PATH.read_bytes()))
    with patch.object(s3, "delete_objects", return_value={"Errors": [{"Code": "Denied"}]}):
        with pytest.raises(HostedWorkspaceError, match="retry Trash"):
            store.trash(asset.record.workspace_id)
    assert len(store.list_records()) == 1
    assert store.get(asset.record.workspace_id) is None
    store.trash(asset.record.workspace_id)
    assert store.list_records() == ()


def test_gallery_trash_requires_confirmation_and_removes_local_asset(tmp_path: Path) -> None:
    """A confirmed POST frees a slot and old download URLs stop working."""
    app = create_app(work_root=tmp_path)
    store = HostedWorkspaceStore(tmp_path / "hosted", _family())
    asset = store.create(DESCRIPTION, "robot.glb", BytesIO(CLEAN_PATH.read_bytes()))
    sibling = store.create(DESCRIPTION, "keep.glb", BytesIO(CLEAN_PATH.read_bytes()))
    client = TestClient(app)
    workspace_id = asset.record.workspace_id
    url = f"/workspace/{workspace_id}/trash"
    gallery = client.get("/workspace").text
    assert "data-trash-form" in gallery
    assert 'class="asset-trash"' in gallery
    assert "Usage accounting is retained" not in gallery
    assert client.get(url).status_code == 405
    assert client.post(url, data={"confirmation": "no"}).status_code == 400
    assert asset.source_path.exists()
    response = client.post(url, data={"confirmation": workspace_id}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].endswith("/workspace")
    assert not asset.root.exists()
    assert sibling.source_path.exists()
    assert client.get(f"/workspace/{workspace_id}").status_code == 404
    assert len(store.list_records()) == 1


@pytest.mark.usefixtures("inline_upload_checks")
def test_gallery_trash_discards_an_upload_slot(tmp_path: Path) -> None:
    """A not-yet-described GLB is removable as well as a saved workspace."""
    client = TestClient(create_app(work_root=tmp_path))
    response = client.post(
        "/workspace/new/upload",
        files={"asset": ("robot.glb", CLEAN_PATH.read_bytes())},
        follow_redirects=False,
    )
    draft_id = response.headers["location"].split("/")[-2]
    response = client.post(
        f"/workspace/new/{draft_id}/trash",
        data={"confirmation": draft_id},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert not (tmp_path / "hosted-start" / draft_id).exists()


def test_deleted_workspace_rejects_queued_admission(tmp_path: Path) -> None:
    """An old browser cannot recreate command history or start a model after trash."""
    s3, dynamo, sqs = _FakeS3(), _FakeDynamo(), FakeSqs()
    repository = _repository(s3, dynamo)
    store = HostedWorkspaceStore(tmp_path, _family(), workspace_repository=repository)
    asset = store.create(DESCRIPTION, "robot.glb", BytesIO(CLEAN_PATH.read_bytes()))
    dispatcher = AgentCoreCommandDispatcher(
        queue_url="https://sqs.example.test/commands",
        table="workspace-state",
        actor_id="contest-demo",
        region="us-east-1",
        sqs_client=sqs,
        dynamodb_client=dynamo,
        workspace_repository=repository,
    )
    store.trash(asset.record.workspace_id)
    with pytest.raises(AgentCoreDispatchError, match="trashed"):
        dispatcher.enqueue(
            {
                "schema_version": 1,
                "operation": "retry",
                "actor_id": "contest-demo",
                "workspace_id": asset.record.workspace_id,
                "command_id": "c" * 32,
            }
        )
    assert not sqs.messages
    assert not dynamo.items


def test_queue_delivery_occurs_after_releasing_admission_lock(tmp_path: Path) -> None:
    """Even an immediate worker can acquire the workspace mutation token."""
    s3, dynamo, sqs = _FakeS3(), _FakeDynamo(), FakeSqs()
    repository = _repository(s3, dynamo)
    store = HostedWorkspaceStore(tmp_path, _family(), workspace_repository=repository)
    asset = store.create(DESCRIPTION, "robot.glb", BytesIO(CLEAN_PATH.read_bytes()))
    dispatcher = AgentCoreCommandDispatcher(
        queue_url="https://sqs.example.test/commands",
        table="workspace-state",
        actor_id="contest-demo",
        region="us-east-1",
        sqs_client=sqs,
        dynamodb_client=dynamo,
        workspace_repository=repository,
    )
    worker = _repository(s3, dynamo)

    def immediate_delivery(**kwargs: object) -> dict[str, object]:
        with worker.exclusive(asset.record.workspace_id):
            return {"MessageId": "immediate"}

    with patch.object(sqs, "send_message", immediate_delivery):
        dispatcher.enqueue(
            {
                "schema_version": 1,
                "operation": "retry",
                "actor_id": "contest-demo",
                "workspace_id": asset.record.workspace_id,
                "command_id": "d" * 32,
            }
        )


def test_trash_removes_all_versions_and_delete_markers(tmp_path: Path) -> None:
    """Version IDs, including delete markers, are passed to S3 deletion explicitly."""
    s3, dynamo = _FakeS3(), _FakeDynamo()
    repository = _repository(s3, dynamo)
    store = HostedWorkspaceStore(tmp_path, _family(), workspace_repository=repository)
    asset = store.create(DESCRIPTION, "robot.glb", BytesIO(CLEAN_PATH.read_bytes()))
    key = f"workspaces/{asset.record.workspace_id}/objects/test"
    versions = [{"Key": key, "VersionId": "old"}, {"Key": key, "VersionId": "current"}]
    markers = [{"Key": key, "VersionId": "marker"}]
    removed: list[dict[str, str]] = []

    def listing(**kwargs: object) -> dict[str, object]:
        if key.startswith(str(kwargs["Prefix"])):
            return {"Versions": versions[:1], "DeleteMarkers": markers[:]}
        return {}

    def delete(**kwargs: object) -> dict[str, object]:
        objects = cast(dict[str, list[dict[str, str]]], kwargs["Delete"])["Objects"]
        for item in objects:
            removed.append(item)
            (markers if item["VersionId"] == "marker" else versions).remove(item)
        return {}

    with (
        patch.object(s3, "list_object_versions", listing),
        patch.object(s3, "delete_objects", delete),
    ):
        store.trash(asset.record.workspace_id)
    assert {item["VersionId"] for item in removed} == {"old", "current", "marker"}


@pytest.mark.usefixtures("inline_upload_checks")
def test_trash_removes_pending_redo_source(tmp_path: Path) -> None:
    """Redo drafts cannot retain a trashed asset's uploaded binary in a reserved slot."""
    client = TestClient(create_app(work_root=tmp_path))
    store = HostedWorkspaceStore(tmp_path / "hosted", _family())
    asset = store.create(DESCRIPTION, "robot.glb", BytesIO(CLEAN_PATH.read_bytes()))
    workspace_id = asset.record.workspace_id
    client.post(f"/workspace/{workspace_id}/redo", follow_redirects=False)
    assert list((tmp_path / "hosted-start").glob("*/source.glb"))
    assert (
        client.post(
            f"/workspace/{workspace_id}/trash",
            data={"confirmation": workspace_id},
            follow_redirects=False,
        ).status_code
        == 303
    )
    assert not list((tmp_path / "hosted-start").glob("*/source.glb"))
