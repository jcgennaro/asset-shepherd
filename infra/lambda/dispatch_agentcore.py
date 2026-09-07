"""SQS-triggered bridge from the public web tier to private AgentCore Runtime."""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import UTC, datetime
from typing import Any, TypeGuard

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
_dynamodb = boto3.client("dynamodb")
_agentcore = boto3.client(
    "bedrock-agentcore",
    config=Config(
        connect_timeout=5,
        read_timeout=850,
        retries={"total_max_attempts": 1, "mode": "standard"},
    ),
)
_TABLE = os.environ["WORKSPACE_TABLE"]
_RUNTIME_ARN = os.environ["AGENT_RUNTIME_ARN"]
_ACTOR_ID = os.environ["WORKSPACE_OWNER_ID"]


def _log_event(
    event: str,
    *,
    message_id: str,
    command: dict[str, Any] | None = None,
    duration_ms: int | None = None,
) -> None:
    """Write only bounded correlation fields, never the command or provider response."""
    value: dict[str, object] = {"event": event, "message_id": message_id}
    if command is not None:
        value.update(
            {
                "workspace_id": command.get("workspace_id"),
                "command_id": command.get("command_id"),
                "operation": command.get("operation"),
            }
        )
    if duration_ms is not None:
        value["duration_ms"] = duration_ms
    logger.info("%s", json.dumps(value, separators=(",", ":"), sort_keys=True))


def _key(command: dict[str, Any]) -> dict[str, dict[str, str]]:
    return {
        "PK": {"S": f"COMMAND#{command['workspace_id']}"},
        "SK": {"S": f"COMMAND#{command['command_id']}"},
    }


def _receipt_addressable(command: object) -> TypeGuard[dict[str, Any]]:
    """Return whether a message can safely address its existing command receipt."""
    return isinstance(command, dict) and all(
        isinstance(command.get(key), str) and bool(command[key])
        for key in ("workspace_id", "command_id")
    )


def _set_state(
    command: dict[str, Any],
    state: str,
    *,
    safe_error: str | None = None,
    lease_until: int | None = None,
) -> None:
    names = {"#state": "state"}
    values: dict[str, dict[str, str]] = {
        ":state": {"S": state},
        ":updated": {"S": datetime.now(UTC).isoformat()},
    }
    expression = "SET #state = :state, dispatch_updated_at = :updated"
    if safe_error is not None:
        expression += ", safe_error = :error"
        values[":error"] = {"S": safe_error[:500]}
    if lease_until is not None:
        expression += ", lease_until_epoch = :lease"
        values[":lease"] = {"N": str(lease_until)}
    try:
        _dynamodb.update_item(
            TableName=_TABLE,
            Key=_key(command),
            ConditionExpression="attribute_exists(PK)",
            UpdateExpression=expression,
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
        )
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
            raise
        # Trash removed this receipt while the completed invocation was returning.


def _claim(command: dict[str, Any]) -> bool:
    now = int(time.time())
    try:
        _dynamodb.update_item(
            TableName=_TABLE,
            Key=_key(command),
            UpdateExpression=(
                "SET #state = :running, dispatch_updated_at = :updated, lease_until_epoch = :lease"
            ),
            ConditionExpression=(
                "dispatch_owner = :owner AND "
                "(#state IN (:queued, :retrying) OR "
                "(#state = :running AND lease_until_epoch < :now))"
            ),
            ExpressionAttributeNames={"#state": "state"},
            ExpressionAttributeValues={
                ":owner": {"S": _ACTOR_ID},
                ":queued": {"S": "QUEUED"},
                ":retrying": {"S": "RETRYING"},
                ":running": {"S": "RUNNING"},
                ":updated": {"S": datetime.now(UTC).isoformat()},
                ":lease": {"N": str(now + 840)},
                ":now": {"N": str(now)},
            },
        )
        return True
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            return False
        raise


def _invoke(command: dict[str, Any]) -> str:
    if command.get("actor_id") != _ACTOR_ID:
        _set_state(command, "FAILED", safe_error="The command actor is not authorized.")
        return "FAILED"
    response = _agentcore.invoke_agent_runtime(
        agentRuntimeArn=_RUNTIME_ARN,
        runtimeSessionId=f"workspace-{command['workspace_id']}",
        contentType="application/json",
        accept="application/json",
        payload=json.dumps(command, separators=(",", ":")).encode("utf-8"),
    )
    stream = response.get("response")
    raw = stream.read() if hasattr(stream, "read") else b""
    result = json.loads(raw.decode("utf-8")) if raw else {}
    if response.get("statusCode") != 200 or result.get("ok") is not True:
        message = result.get("error")
        safe_error = message if isinstance(message, str) else "The agent could not continue."
        _set_state(command, "FAILED", safe_error=safe_error)
        return "FAILED"
    _set_state(command, "SUCCEEDED")
    return "SUCCEEDED"


def lambda_handler(event: dict[str, Any], _context: object) -> dict[str, list[dict[str, str]]]:
    """Process one-message batches and let SQS retry only transient failures."""
    failures: list[dict[str, str]] = []
    for record in event.get("Records", []):
        message_id = str(record.get("messageId", ""))
        command: dict[str, Any] | None = None
        started = time.perf_counter()
        try:
            decoded = json.loads(record["body"])
            if not _receipt_addressable(decoded):
                _log_event("dispatch_ignored_unaddressable", message_id=message_id)
                continue
            command = decoded
            if not _claim(command):
                _log_event("dispatch_ignored_unclaimable", message_id=message_id, command=command)
                continue
            _log_event("dispatch_started", message_id=message_id, command=command)
            state = _invoke(command)
            _log_event(
                f"dispatch_{state.lower()}",
                message_id=message_id,
                command=command,
                duration_ms=round((time.perf_counter() - started) * 1000),
            )
        except Exception:
            logger.exception("AgentCore dispatch failed")
            if _receipt_addressable(command):
                _set_state(
                    command,
                    "FAILED",
                    safe_error="The agent could not be reached. Reload before retrying.",
                )
            _log_event(
                "dispatch_exception",
                message_id=message_id,
                command=command,
                duration_ms=round((time.perf_counter() - started) * 1000),
            )
    return {"batchItemFailures": failures}
