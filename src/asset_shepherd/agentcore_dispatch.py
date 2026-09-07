"""Durable web-to-AgentCore command dispatch over SQS and DynamoDB."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Protocol, cast

import boto3
from botocore.exceptions import ClientError

from asset_shepherd.agentcore_runtime import RuntimeCommand, validate_runtime_command
from asset_shepherd.cloud_workspace import S3DynamoWorkspaceRepository


class AgentCoreDispatchError(ValueError):
    """Raised when a remote command cannot be safely queued or inspected."""


class _SqsClient(Protocol):
    def send_message(self, **kwargs: object) -> dict[str, object]: ...


class _DynamoClient(Protocol):
    def get_item(self, **kwargs: object) -> dict[str, object]: ...

    def put_item(self, **kwargs: object) -> dict[str, object]: ...


def _string_attribute(item: dict[str, object], key: str) -> str | None:
    raw = item.get(key)
    if not isinstance(raw, dict):
        return None
    value = cast(dict[str, object], raw).get("S")
    return value if isinstance(value, str) else None


class AgentCoreCommandDispatcher:
    """Queue exact typed commands and expose only bounded dispatch status."""

    def __init__(
        self,
        *,
        queue_url: str,
        table: str,
        actor_id: str,
        region: str,
        sqs_client: _SqsClient | None = None,
        dynamodb_client: _DynamoClient | None = None,
        workspace_repository: S3DynamoWorkspaceRepository | None = None,
    ) -> None:
        """Bind one deployment actor to its queue and command-state table."""
        if not queue_url or not table or not actor_id or not region:
            raise ValueError("Remote AgentCore dispatch requires queue, table, actor, and region")
        session = boto3.Session(region_name=region)
        self.queue_url = queue_url
        self.table = table
        self.actor_id = actor_id
        self.workspace_repository = workspace_repository
        self.sqs = sqs_client or cast(
            _SqsClient,
            session.client("sqs"),  # pyright: ignore[reportUnknownMemberType]
        )
        self.dynamodb = dynamodb_client or cast(
            _DynamoClient,
            session.client("dynamodb"),  # pyright: ignore[reportUnknownMemberType]
        )

    @staticmethod
    def _key(workspace_id: str, command_id: str) -> dict[str, dict[str, str]]:
        return {
            "PK": {"S": f"COMMAND#{workspace_id}"},
            "SK": {"S": f"COMMAND#{command_id}"},
        }

    def _item(self, workspace_id: str, command_id: str) -> dict[str, object] | None:
        response = self.dynamodb.get_item(
            TableName=self.table,
            Key=self._key(workspace_id, command_id),
            ConsistentRead=True,
        )
        raw_item = response.get("Item")
        if not isinstance(raw_item, dict):
            return None
        item = cast(dict[str, object], raw_item)
        return item if _string_attribute(item, "dispatch_owner") == self.actor_id else None

    def enqueue(self, payload: object) -> RuntimeCommand:
        """Fence queue admission against permanent deletion in hosted deployments."""
        command = validate_runtime_command(payload)
        if command.actor_id != self.actor_id:
            raise AgentCoreDispatchError("The command actor is not authorized for this deployment.")
        repository = self.workspace_repository
        if repository is None:
            return self._enqueue(payload)
        with repository.exclusive(command.workspace_id):
            response = self.dynamodb.get_item(
                TableName=self.table,
                Key={"PK": {"S": f"WORKSPACE#{command.workspace_id}"}, "SK": {"S": "STATE"}},
                ConsistentRead=True,
            )
            item = cast(dict[str, object], response.get("Item", {}))
            if (
                _string_attribute(item, "owner_id") != self.actor_id
                or _string_attribute(item, "deletion_status") == "DELETING"
            ):
                raise AgentCoreDispatchError("This asset has been trashed or is being deleted.")
            return self._enqueue(payload)

    def _enqueue(self, payload: object) -> RuntimeCommand:
        """Persist and send one idempotent command envelope."""
        command = validate_runtime_command(payload)
        if command.actor_id != self.actor_id:
            raise AgentCoreDispatchError("The command actor is not authorized for this deployment.")
        body = json.dumps(
            command.model_dump(mode="json"),
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        payload_hash = sha256(body.encode("utf-8")).hexdigest()
        now = datetime.now(UTC)
        item = {
            **self._key(command.workspace_id, command.command_id),
            "dispatch_owner": {"S": self.actor_id},
            "operation": {"S": command.operation},
            "payload_sha256": {"S": payload_hash},
            "state": {"S": "QUEUED"},
            "dispatch_updated_at": {"S": now.isoformat()},
            "expires_at_epoch": {"N": str(int((now + timedelta(days=7)).timestamp()))},
        }
        should_send = True
        try:
            self.dynamodb.put_item(
                TableName=self.table,
                Item=item,
                ConditionExpression="attribute_not_exists(PK)",
            )
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
                raise
            existing = self._item(command.workspace_id, command.command_id)
            if existing is None or _string_attribute(existing, "payload_sha256") != payload_hash:
                raise AgentCoreDispatchError(
                    "This command identifier was already used for a different action."
                ) from error
            should_send = _string_attribute(existing, "state") in {"QUEUED", "RETRYING"}
        if should_send:
            self.sqs.send_message(QueueUrl=self.queue_url, MessageBody=body)
        return command

    def status(self, workspace_id: str, command_id: str) -> dict[str, object] | None:
        """Return safe queue state without exposing the command or provider response."""
        item = self._item(workspace_id, command_id)
        if item is None:
            return None
        state = _string_attribute(item, "state") or "QUEUED"
        value: dict[str, object] = {
            "schema_version": 1,
            "workspace_id": workspace_id,
            "command_id": command_id,
            "state": state,
        }
        error = _string_attribute(item, "safe_error")
        if state == "FAILED" and error:
            value["error"] = error
        return value
