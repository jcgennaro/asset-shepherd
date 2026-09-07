"""S3 artifact snapshots and conditional DynamoDB workspace records."""

import json
import re
import shutil
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Protocol, cast
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError

from asset_shepherd.hosted_workspace import HostedWorkspaceError


class _ReadableBody(Protocol):
    def read(self) -> bytes:
        """Read the complete bounded manifest body."""
        raise NotImplementedError


class _S3Client(Protocol):
    def list_object_versions(self, **kwargs: object) -> dict[str, object]: ...

    def delete_objects(self, **kwargs: object) -> dict[str, object]: ...
    def get_object(self, **kwargs: object) -> dict[str, object]: ...

    def download_file(self, bucket: str, key: str, filename: str) -> None: ...

    def head_object(self, **kwargs: object) -> dict[str, object]: ...

    def upload_file(self, filename: str, bucket: str, key: str, **kwargs: object) -> None: ...

    def put_object(self, **kwargs: object) -> dict[str, object]: ...


class _DynamoClient(Protocol):
    def query(self, **kwargs: object) -> dict[str, object]: ...

    def get_item(self, **kwargs: object) -> dict[str, object]: ...

    def put_item(self, **kwargs: object) -> dict[str, object]: ...

    def delete_item(self, **kwargs: object) -> dict[str, object]: ...


def _string_attribute(item: dict[str, object], key: str) -> str | None:
    raw_attribute = item.get(key)
    if not isinstance(raw_attribute, dict):
        return None
    value = cast(dict[str, object], raw_attribute).get("S")
    return value if isinstance(value, str) else None


class S3DynamoWorkspaceRepository:
    """Keep the local workspace tree as a cache over immutable S3 objects."""

    def __init__(
        self,
        *,
        bucket: str,
        table: str,
        owner_id: str,
        region: str,
        aws_profile: str | None = None,
        s3_client: _S3Client | None = None,
        dynamodb_client: _DynamoClient | None = None,
    ) -> None:
        """Bind one application owner to exact S3 and DynamoDB resources."""
        if not bucket or not table or not owner_id or not region:
            raise ValueError("Cloud workspace storage requires bucket, table, owner, and region")
        allowed_owner_characters = "abcdefghijklmnopqrstuvwxyz0123456789-_."
        if any(character not in allowed_owner_characters for character in owner_id):
            raise ValueError(
                "Cloud workspace owner IDs use lowercase letters, digits, dash, dot, underscore"
            )
        session = boto3.Session(profile_name=aws_profile, region_name=region)
        self.bucket = bucket
        self.table = table
        self.owner_id = owner_id
        self._held: ContextVar[tuple[str, ...]] = ContextVar("workspace_locks", default=())
        self.s3 = s3_client or cast(
            _S3Client,
            session.client("s3"),  # pyright: ignore[reportUnknownMemberType]
        )
        self.dynamodb = dynamodb_client or cast(
            _DynamoClient,
            session.client("dynamodb"),  # pyright: ignore[reportUnknownMemberType]
        )

    @staticmethod
    def _workspace_key(workspace_id: str) -> dict[str, dict[str, str]]:
        if re.fullmatch(r"[0-9a-f]{32}", workspace_id) is None:
            raise HostedWorkspaceError("The workspace identifier is invalid.")
        return {"PK": {"S": f"WORKSPACE#{workspace_id}"}, "SK": {"S": "STATE"}}

    @contextmanager
    def exclusive(self, workspace_id: str) -> Generator[None]:
        """Exclude deletion and writers across processes; abandoned locks fail closed."""
        self._workspace_key(workspace_id)
        if workspace_id in self._held.get():
            yield
            return
        key = {"PK": {"S": f"LOCK#{workspace_id}"}, "SK": {"S": "MUTATION"}}
        token = uuid4().hex
        try:
            self.dynamodb.put_item(
                TableName=self.table,
                Item={**key, "owner_id": {"S": self.owner_id}, "token": {"S": token}},
                ConditionExpression="attribute_not_exists(PK)",
            )
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                raise HostedWorkspaceError(
                    "This asset is busy. Wait for its current operation before trying again."
                ) from error
            raise
        context_token = self._held.set((*self._held.get(), workspace_id))
        try:
            yield
        finally:
            self._held.reset(context_token)
            self.dynamodb.delete_item(
                TableName=self.table,
                Key=key,
                ConditionExpression="#token = :token",
                ExpressionAttributeNames={"#token": "token"},
                ExpressionAttributeValues={":token": {"S": token}},
            )

    def list_record_json(self, *, limit: int) -> tuple[str, ...]:
        """Query the newest active records through the owner-scoped gallery index."""
        response = self.dynamodb.query(
            TableName=self.table,
            IndexName="OwnerUpdatedIndex",
            KeyConditionExpression="owner_id = :owner_id",
            ExpressionAttributeValues={":owner_id": {"S": self.owner_id}},
            ScanIndexForward=False,
            Limit=limit,
        )
        values: list[str] = []
        raw_items = response.get("Items")
        if not isinstance(raw_items, list):
            return ()
        for raw_item in cast(list[object], raw_items):
            if not isinstance(raw_item, dict):
                continue
            key = _string_attribute(cast(dict[str, object], raw_item), "PK") or ""
            if not key.startswith("WORKSPACE#"):
                continue
            # The GSI is eventually consistent; a deleted slot must not reappear.
            current = self._item(key.removeprefix("WORKSPACE#"))
            if current is None:
                continue
            record_value = _string_attribute(current, "record_json")
            if isinstance(record_value, str):
                values.append(record_value)
        return tuple(values)

    def _item(self, workspace_id: str) -> dict[str, object] | None:
        response = self.dynamodb.get_item(
            TableName=self.table,
            Key=self._workspace_key(workspace_id),
            ConsistentRead=True,
        )
        item = response.get("Item")
        if not isinstance(item, dict):
            return None
        typed_item = cast(dict[str, object], item)
        owner = _string_attribute(typed_item, "owner_id")
        return typed_item if owner == self.owner_id else None

    def hydrate(self, workspace_id: str, destination: Path) -> bool:
        """Download the current hash-verified manifest into a fresh local cache tree."""
        item = self._item(workspace_id)
        if item is None or _string_attribute(item, "deletion_status") == "DELETING":
            return False
        manifest_key = _string_attribute(item, "manifest_key")
        if not isinstance(manifest_key, str):
            raise HostedWorkspaceError("The cloud workspace record has no artifact manifest.")
        expected_prefix = f"workspaces/{workspace_id}/manifests/"
        if not manifest_key.startswith(expected_prefix):
            raise HostedWorkspaceError("The cloud workspace manifest is outside its prefix.")
        manifest_response = self.s3.get_object(Bucket=self.bucket, Key=manifest_key)
        body = manifest_response.get("Body")
        if not hasattr(body, "read"):
            raise HostedWorkspaceError("The cloud workspace manifest body is invalid.")
        manifest = cast(
            dict[str, object],
            json.loads(cast(_ReadableBody, body).read().decode("utf-8")),
        )
        raw_files = manifest.get("files")
        if not isinstance(raw_files, dict):
            raise HostedWorkspaceError("The cloud workspace manifest is invalid.")

        destination = destination.resolve(strict=False)
        temporary = destination.with_name(f"{destination.name}.hydrate-{uuid4().hex}")
        temporary.mkdir(parents=True, exist_ok=False)
        try:
            for raw_relative, raw_entry in cast(dict[str, object], raw_files).items():
                relative = Path(raw_relative)
                if (
                    relative.is_absolute()
                    or ".." in relative.parts
                    or not isinstance(raw_entry, dict)
                ):
                    raise HostedWorkspaceError(
                        "The cloud workspace manifest contains an unsafe path."
                    )
                entry = cast(dict[str, object], raw_entry)
                object_key = entry.get("key")
                expected_hash = entry.get("sha256")
                if not isinstance(object_key, str) or not isinstance(expected_hash, str):
                    raise HostedWorkspaceError("The cloud workspace manifest entry is invalid.")
                if not object_key.startswith(f"workspaces/{workspace_id}/objects/"):
                    raise HostedWorkspaceError("A cloud workspace object is outside its prefix.")
                target = temporary / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                self.s3.download_file(self.bucket, object_key, str(target))
                if sha256(target.read_bytes()).hexdigest() != expected_hash:
                    raise HostedWorkspaceError(
                        "A cloud workspace artifact failed hash verification."
                    )
            if destination.exists():
                shutil.rmtree(destination)
            temporary.replace(destination)
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise
        return True

    def persist(
        self,
        workspace_root: Path,
        record_json: str,
        *,
        expected_version: int,
    ) -> None:
        """Fence every artifact write against deletion, including stale caches."""
        record = cast(dict[str, object], json.loads(record_json))
        workspace_id = str(record["workspace_id"])
        with self.exclusive(workspace_id):
            item = self._item(workspace_id)
            if expected_version and (
                item is None or _string_attribute(item, "deletion_status") == "DELETING"
            ):
                raise HostedWorkspaceError("This asset has been trashed or is being deleted.")
            self._persist_unlocked(workspace_root, record_json, expected_version=expected_version)

    def _persist_unlocked(
        self,
        workspace_root: Path,
        record_json: str,
        *,
        expected_version: int,
    ) -> None:
        """Upload immutable content and conditionally advance one manifest pointer."""
        record = cast(dict[str, object], json.loads(record_json))
        workspace_id = record.get("workspace_id")
        record_version = record.get("record_version")
        if not isinstance(workspace_id, str) or record_version != expected_version + 1:
            raise HostedWorkspaceError("The cloud workspace version transition is invalid.")

        files: dict[str, dict[str, str]] = {}
        for path in sorted(workspace_root.rglob("*")):
            if not path.is_file() or path.suffix == ".tmp":
                continue
            if path.is_symlink():
                raise HostedWorkspaceError("Cloud workspaces cannot contain symbolic links.")
            relative = path.relative_to(workspace_root).as_posix()
            digest = sha256(path.read_bytes()).hexdigest()
            object_key = f"workspaces/{workspace_id}/objects/{digest}"
            try:
                self.s3.head_object(Bucket=self.bucket, Key=object_key)
            except ClientError as error:
                if error.response.get("Error", {}).get("Code") not in {
                    "404",
                    "NoSuchKey",
                    "NotFound",
                }:
                    raise
                self.s3.upload_file(
                    str(path),
                    self.bucket,
                    object_key,
                    ExtraArgs={"Metadata": {"sha256": digest}},
                )
            files[relative] = {"key": object_key, "sha256": digest}

        manifest = {
            "schema_version": 1,
            "workspace_id": workspace_id,
            "record_version": record_version,
            "files": files,
        }
        manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
        manifest_hash = sha256(manifest_bytes).hexdigest()
        manifest_key = (
            f"workspaces/{workspace_id}/manifests/{record_version:08d}-{manifest_hash}.json"
        )
        self.s3.put_object(
            Bucket=self.bucket,
            Key=manifest_key,
            Body=manifest_bytes,
            ContentType="application/json",
            Metadata={"sha256": manifest_hash},
        )

        expires_at = datetime.fromisoformat(str(record["retention_expires_at"]))
        item = {
            **self._workspace_key(workspace_id),
            "owner_id": {"S": self.owner_id},
            "updated_at": {"S": str(record["updated_at"])},
            "record_version": {"N": str(record_version)},
            "expires_at_epoch": {"N": str(int(expires_at.astimezone(UTC).timestamp()))},
            "manifest_key": {"S": manifest_key},
            "manifest_sha256": {"S": manifest_hash},
            "record_json": {"S": record_json},
        }
        arguments: dict[str, object] = {
            "TableName": self.table,
            "Item": item,
            "ConditionExpression": (
                "attribute_not_exists(PK)"
                if expected_version == 0
                else "record_version = :expected_version"
            ),
        }
        if expected_version:
            arguments["ExpressionAttributeValues"] = {
                ":expected_version": {"N": str(expected_version)}
            }
        try:
            self.dynamodb.put_item(**arguments)
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                raise HostedWorkspaceError(
                    "This workspace changed in another request. Reload before continuing."
                ) from error
            raise

    def delete(self, workspace_id: str) -> None:
        """Delete the active owner-bound pointer; S3 lifecycle removes immutable content."""
        try:
            self.dynamodb.delete_item(
                TableName=self.table,
                Key=self._workspace_key(workspace_id),
                ConditionExpression="owner_id = :owner_id",
                ExpressionAttributeValues={":owner_id": {"S": self.owner_id}},
            )
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
                raise

    def trash(self, workspace_id: str) -> None:
        """Permanently erase exact asset prefixes and receipts, retaining spending records."""
        with self.exclusive(workspace_id):
            item = self._item(workspace_id)
            if item is None:
                raise HostedWorkspaceError("The asset does not exist or is not accessible.")
            receipts: list[dict[str, object]] = []
            query: dict[str, object] = {
                "TableName": self.table,
                "KeyConditionExpression": "PK = :pk",
                "ExpressionAttributeValues": {":pk": {"S": f"COMMAND#{workspace_id}"}},
                "ConsistentRead": True,
            }
            while True:
                page = self.dynamodb.query(**query)
                for receipt in cast(list[dict[str, object]], page.get("Items", [])):
                    if _string_attribute(receipt, "dispatch_owner") != self.owner_id:
                        raise HostedWorkspaceError("A command receipt belongs to another owner.")
                    receipts.append(receipt)
                if not page.get("LastEvaluatedKey"):
                    break
                query["ExclusiveStartKey"] = page["LastEvaluatedKey"]
            # Keep the pointer until cleanup succeeds so partial failures remain retryable.
            item["deletion_status"] = {"S": "DELETING"}
            self.dynamodb.put_item(
                TableName=self.table,
                Item=item,
                ConditionExpression="owner_id = :owner_id",
                ExpressionAttributeValues={":owner_id": {"S": self.owner_id}},
            )
            for prefix in (f"workspaces/{workspace_id}/", f"sessions/session_{workspace_id}/"):
                while True:
                    page = self.s3.list_object_versions(
                        Bucket=self.bucket, Prefix=prefix, MaxKeys=1000
                    )
                    objects: list[dict[str, str]] = []
                    for kind in ("Versions", "DeleteMarkers"):
                        for raw in cast(list[dict[str, str]], page.get(kind, [])):
                            if not raw["Key"].startswith(prefix):
                                raise HostedWorkspaceError("Deletion found an out-of-scope object.")
                            objects.append({"Key": raw["Key"], "VersionId": raw["VersionId"]})
                    if not objects:
                        break
                    response = self.s3.delete_objects(
                        Bucket=self.bucket, Delete={"Objects": objects, "Quiet": True}
                    )
                    if response.get("Errors"):
                        raise HostedWorkspaceError(
                            "Some stored files could not be deleted. Please retry Trash."
                        )
            for receipt in receipts:
                self.dynamodb.delete_item(
                    TableName=self.table,
                    Key={"PK": receipt["PK"], "SK": receipt["SK"]},
                    ConditionExpression="dispatch_owner = :owner",
                    ExpressionAttributeValues={":owner": {"S": self.owner_id}},
                )
            self.delete(workspace_id)
