"""Cloud workspace durability and conditional-write acceptance tests."""

from io import BytesIO
from os import environ
from pathlib import Path
from typing import cast

import pytest
from botocore.exceptions import ClientError

from asset_shepherd.cloud_workspace import S3DynamoWorkspaceRepository
from asset_shepherd.hosted_workspace import HostedWorkspaceError, HostedWorkspaceStore
from asset_shepherd.models import ProjectProfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLEAN_PATH = PROJECT_ROOT / "fixtures" / "clean_robot.glb"
BROKEN_PATH = PROJECT_ROOT / "fixtures" / "broken_robot.glb"
DESCRIPTION = "A friendly humanoid robot intended as a 1.8 m static game asset."


class _FakeS3:
    """Minimal immutable-object S3 surface used by the repository."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.upload_count = 0

    def get_object(self, **kwargs: object) -> dict[str, object]:
        key = str(kwargs["Key"])
        return {"Body": BytesIO(self.objects[key])}

    def download_file(self, bucket: str, key: str, filename: str) -> None:
        del bucket
        Path(filename).write_bytes(self.objects[key])

    def head_object(self, **kwargs: object) -> dict[str, object]:
        key = str(kwargs["Key"])
        if key not in self.objects:
            raise ClientError(
                {"Error": {"Code": "404", "Message": "missing"}},
                "HeadObject",
            )
        return {}

    def upload_file(
        self,
        filename: str,
        bucket: str,
        key: str,
        **kwargs: object,
    ) -> None:
        del bucket, kwargs
        self.objects[key] = Path(filename).read_bytes()
        self.upload_count += 1

    def put_object(self, **kwargs: object) -> dict[str, object]:
        key = str(kwargs["Key"])
        body = kwargs["Body"]
        assert isinstance(body, bytes)
        self.objects[key] = body
        return {}


class _FakeDynamo:
    """Minimal owner-index and optimistic-write DynamoDB surface."""

    def __init__(self) -> None:
        self.items: dict[str, dict[str, object]] = {}

    def query(self, **kwargs: object) -> dict[str, object]:
        expression_values = cast(dict[str, dict[str, str]], kwargs["ExpressionAttributeValues"])
        owner = expression_values[":owner_id"]["S"]
        limit = kwargs["Limit"]
        assert isinstance(limit, int)
        values = [item for item in self.items.values() if item["owner_id"] == {"S": owner}]
        values.sort(key=lambda item: str(item["updated_at"]), reverse=True)
        return {"Items": values[:limit]}

    def get_item(self, **kwargs: object) -> dict[str, object]:
        key = cast(dict[str, dict[str, str]], kwargs["Key"])
        workspace_key = key["PK"]["S"]
        item = self.items.get(workspace_key)
        return {"Item": item} if item is not None else {}

    def put_item(self, **kwargs: object) -> dict[str, object]:
        item = kwargs["Item"]
        assert isinstance(item, dict)
        primary_key = cast(dict[str, str], item["PK"])
        workspace_key = primary_key["S"]
        existing = self.items.get(workspace_key)
        expected_values = kwargs.get("ExpressionAttributeValues")
        if expected_values is None:
            conflict = existing is not None
        else:
            typed_values = cast(dict[str, dict[str, str]], expected_values)
            expected = typed_values[":expected_version"]
            conflict = existing is None or existing["record_version"] != expected
        if conflict:
            raise ClientError(
                {
                    "Error": {
                        "Code": "ConditionalCheckFailedException",
                        "Message": "stale",
                    }
                },
                "PutItem",
            )
        self.items[workspace_key] = item
        return {}

    def delete_item(self, **kwargs: object) -> dict[str, object]:
        key = cast(dict[str, dict[str, str]], kwargs["Key"])
        workspace_key = key["PK"]["S"]
        self.items.pop(workspace_key, None)
        return {}


def _family() -> ProjectProfile:
    return ProjectProfile.model_validate_json(
        (
            PROJECT_ROOT
            / "src"
            / "asset_shepherd"
            / "data"
            / "unreal_static_game_asset_family.json"
        ).read_text(encoding="utf-8")
    )


def _repository(s3: _FakeS3, dynamodb: _FakeDynamo) -> S3DynamoWorkspaceRepository:
    return S3DynamoWorkspaceRepository(
        bucket="private-workspaces",
        table="workspace-state",
        owner_id="contest-demo",
        region="us-east-1",
        s3_client=s3,
        dynamodb_client=dynamodb,
    )


def test_cloud_workspace_survives_a_clean_process_cache(tmp_path: Path) -> None:
    """The current record and immutable GLB hydrate after the local tree disappears."""
    s3 = _FakeS3()
    dynamodb = _FakeDynamo()
    repository = _repository(s3, dynamodb)
    first_root = tmp_path / "first"
    workspace = HostedWorkspaceStore(
        first_root,
        _family(),
        workspace_repository=repository,
    ).create(DESCRIPTION, CLEAN_PATH.name, BytesIO(CLEAN_PATH.read_bytes()))

    assert workspace.record.record_version == 1
    assert len(repository.list_record_json(limit=7)) == 1

    replacement_store = HostedWorkspaceStore(
        tmp_path / "replacement",
        _family(),
        workspace_repository=repository,
    )
    restored = replacement_store.get(workspace.record.workspace_id)

    assert restored is not None
    assert restored.record.record_version == 1
    assert restored.source_path.read_bytes() == CLEAN_PATH.read_bytes()


def test_cloud_workspace_rejects_a_stale_conditional_write(tmp_path: Path) -> None:
    """Two process caches cannot both advance the same workspace record version."""
    s3 = _FakeS3()
    dynamodb = _FakeDynamo()
    repository = _repository(s3, dynamodb)
    initial_store = HostedWorkspaceStore(
        tmp_path / "initial",
        _family(),
        workspace_repository=repository,
    )
    workspace = initial_store.create(
        DESCRIPTION,
        CLEAN_PATH.name,
        BytesIO(CLEAN_PATH.read_bytes()),
    )
    first_store = HostedWorkspaceStore(
        tmp_path / "first",
        _family(),
        workspace_repository=repository,
    )
    second_store = HostedWorkspaceStore(
        tmp_path / "second",
        _family(),
        workspace_repository=repository,
    )
    first = first_store.get(workspace.record.workspace_id)
    second = second_store.get(workspace.record.workspace_id)
    assert first is not None and second is not None

    first_store.answer_evidence_question(first, "measurements")
    with pytest.raises(HostedWorkspaceError, match="changed in another request"):
        second_store.answer_evidence_question(second, "materials")


def test_cloud_workspace_content_objects_are_deduplicated(tmp_path: Path) -> None:
    """Advancing only metadata does not upload the unchanged GLB again."""
    s3 = _FakeS3()
    dynamodb = _FakeDynamo()
    repository = _repository(s3, dynamodb)
    store = HostedWorkspaceStore(
        tmp_path / "cache",
        _family(),
        workspace_repository=repository,
    )
    workspace = store.create(
        DESCRIPTION,
        CLEAN_PATH.name,
        BytesIO(CLEAN_PATH.read_bytes()),
    )
    upload_count = s3.upload_count

    store.answer_evidence_question(workspace, "measurements")

    assert s3.upload_count > upload_count
    source_digest = CLEAN_PATH.read_bytes()
    assert sum(value == source_digest for value in s3.objects.values()) == 1


def test_cloud_workspace_resumes_approval_and_completion_across_processes(
    tmp_path: Path,
) -> None:
    """Intake, interrupt, authorized mutation, and packaging survive cache replacement."""
    repository = _repository(_FakeS3(), _FakeDynamo())
    created = HostedWorkspaceStore(
        tmp_path / "intake",
        _family(),
        workspace_repository=repository,
    ).create(DESCRIPTION, BROKEN_PATH.name, BytesIO(BROKEN_PATH.read_bytes()))
    workspace_id = created.record.workspace_id

    planning_store = HostedWorkspaceStore(
        tmp_path / "planning",
        _family(),
        workspace_repository=repository,
    )
    planning = planning_store.get(workspace_id)
    assert planning is not None
    waiting = planning_store.confirm_target(
        planning,
        accept_supported_goal=False,
        command_id="1" * 32,
    )
    interrupt_id = waiting.record.pending_interrupt_id
    assert interrupt_id is not None

    repair_store = HostedWorkspaceStore(
        tmp_path / "repair",
        _family(),
        workspace_repository=repository,
    )
    repair = repair_store.get(workspace_id)
    assert repair is not None and repair.waiting_for_approval
    completed = repair_store.decide(
        repair,
        interrupt_id=interrupt_id,
        approved=True,
        command_id="2" * 32,
    )
    assert completed.ready_candidate

    completed_store = HostedWorkspaceStore(
        tmp_path / "completed",
        _family(),
        workspace_repository=repository,
    )
    restored = completed_store.get(workspace_id)
    assert restored is not None and restored.ready_candidate
    repaired_before = (restored.output_dir / "repaired.glb").read_bytes()
    result_before = (restored.output_dir / "result.zip").read_bytes()
    duplicate = completed_store.decide(
        restored,
        interrupt_id=interrupt_id,
        approved=True,
        command_id="2" * 32,
    )
    assert (duplicate.output_dir / "repaired.glb").read_bytes() == repaired_before
    assert (duplicate.output_dir / "result.zip").read_bytes() == result_before


@pytest.mark.live
def test_live_cloud_workspace_round_trip(tmp_path: Path) -> None:
    """Prove real S3/Dynamo intake, approval, repair, and completion replacement."""
    bucket = environ.get("ASSET_SHEPHERD_WORKSPACE_BUCKET")
    table = environ.get("ASSET_SHEPHERD_WORKSPACE_TABLE")
    region = environ.get("ASSET_SHEPHERD_AWS_REGION")
    profile = environ.get("AWS_PROFILE")
    if not bucket or not table or not region:
        pytest.skip("Live cloud workspace resources are not configured")
    repository = S3DynamoWorkspaceRepository(
        bucket=bucket,
        table=table,
        owner_id="cloud-state-smoke",
        region=region,
        aws_profile=profile,
    )
    workspace = HostedWorkspaceStore(
        tmp_path / "first",
        _family(),
        workspace_repository=repository,
    ).create(DESCRIPTION, BROKEN_PATH.name, BytesIO(BROKEN_PATH.read_bytes()))
    try:
        planning_store = HostedWorkspaceStore(
            tmp_path / "planning",
            _family(),
            workspace_repository=repository,
        )
        planning = planning_store.get(workspace.record.workspace_id)
        assert planning is not None
        assert planning.source_path.read_bytes() == BROKEN_PATH.read_bytes()
        waiting = planning_store.confirm_target(
            planning,
            accept_supported_goal=False,
            command_id="a" * 32,
        )
        interrupt_id = waiting.record.pending_interrupt_id
        assert interrupt_id is not None

        repair_store = HostedWorkspaceStore(
            tmp_path / "repair",
            _family(),
            workspace_repository=repository,
        )
        repair = repair_store.get(workspace.record.workspace_id)
        assert repair is not None and repair.waiting_for_approval
        completed = repair_store.decide(
            repair,
            interrupt_id=interrupt_id,
            approved=True,
            command_id="b" * 32,
        )
        assert completed.ready_candidate

        final_store = HostedWorkspaceStore(
            tmp_path / "final",
            _family(),
            workspace_repository=repository,
        )
        restored = final_store.get(workspace.record.workspace_id)
        assert restored is not None and restored.ready_candidate
        assert (restored.output_dir / "result.zip").is_file()
        records = repository.list_record_json(limit=7)
        assert len(records) == 1
        assert '"phase":"COMPLETE"' in records[0]
    finally:
        repository.delete(workspace.record.workspace_id)
