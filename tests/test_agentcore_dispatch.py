"""Acceptance for durable asynchronous AgentCore command receipts."""

from __future__ import annotations

from typing import cast

import pytest
from botocore.exceptions import ClientError

from asset_shepherd.agentcore_dispatch import AgentCoreCommandDispatcher, AgentCoreDispatchError


class FakeSqs:
    """Capture queued command bodies."""

    def __init__(self) -> None:
        """Start with no messages."""
        self.messages: list[str] = []

    def send_message(self, **kwargs: object) -> dict[str, object]:
        """Record one message like the low-level SQS client."""
        self.messages.append(cast(str, kwargs["MessageBody"]))
        return {"MessageId": "queued"}


class FakeDynamo:
    """Provide the conditional item subset used by the dispatcher."""

    def __init__(self) -> None:
        """Start with an empty table."""
        self.items: dict[tuple[str, str], dict[str, object]] = {}

    @staticmethod
    def _key(value: dict[str, object]) -> tuple[str, str]:
        pk = cast(dict[str, str], value["PK"])["S"]
        sk = cast(dict[str, str], value["SK"])["S"]
        return pk, sk

    def get_item(self, **kwargs: object) -> dict[str, object]:
        """Return one strongly consistent fake item."""
        key = self._key(cast(dict[str, object], kwargs["Key"]))
        item = self.items.get(key)
        return {"Item": item} if item is not None else {}

    def put_item(self, **kwargs: object) -> dict[str, object]:
        """Create one item or raise the DynamoDB conditional error."""
        item = cast(dict[str, object], kwargs["Item"])
        key = self._key(item)
        if key in self.items:
            raise ClientError(
                {"Error": {"Code": "ConditionalCheckFailedException", "Message": "exists"}},
                "PutItem",
            )
        self.items[key] = item
        return {}


def _payload(*, actor_id: str = "contest-demo", approved: bool = True) -> dict[str, object]:
    return {
        "schema_version": 1,
        "operation": "decision",
        "actor_id": actor_id,
        "workspace_id": "a" * 32,
        "command_id": "b" * 32,
        "interrupt_id": "interrupt-1234",
        "approved": approved,
    }


def _dispatcher() -> tuple[AgentCoreCommandDispatcher, FakeSqs, FakeDynamo]:
    sqs = FakeSqs()
    dynamo = FakeDynamo()
    dispatcher = AgentCoreCommandDispatcher(
        queue_url="https://sqs.us-east-1.amazonaws.com/123/commands",
        table="workspace-table",
        actor_id="contest-demo",
        region="us-east-1",
        sqs_client=sqs,
        dynamodb_client=dynamo,
    )
    return dispatcher, sqs, dynamo


def test_enqueue_creates_bounded_receipt_and_sends_typed_command() -> None:
    """A new typed command gets one private receipt and one queue message."""
    dispatcher, sqs, _dynamo = _dispatcher()

    command = dispatcher.enqueue(_payload())

    assert command.operation == "decision"
    assert len(sqs.messages) == 1
    assert '"approved":true' in sqs.messages[0]
    assert dispatcher.status("a" * 32, "b" * 32) == {
        "schema_version": 1,
        "workspace_id": "a" * 32,
        "command_id": "b" * 32,
        "state": "QUEUED",
    }


def test_exact_queued_retry_is_safe_but_running_receipt_is_not_duplicated() -> None:
    """A lost send can be retried while in-flight work is not duplicated."""
    dispatcher, sqs, dynamo = _dispatcher()
    dispatcher.enqueue(_payload())
    dispatcher.enqueue(_payload())
    assert len(sqs.messages) == 2

    item = next(iter(dynamo.items.values()))
    item["state"] = {"S": "RUNNING"}
    dispatcher.enqueue(_payload())

    assert len(sqs.messages) == 2


def test_command_id_cannot_be_reused_for_another_payload() -> None:
    """One stable command ID cannot authorize two different actions."""
    dispatcher, _sqs, _dynamo = _dispatcher()
    dispatcher.enqueue(_payload())

    with pytest.raises(AgentCoreDispatchError, match="different action"):
        dispatcher.enqueue(_payload(approved=False))


def test_deployment_actor_is_enforced_before_queueing() -> None:
    """A browser cannot select a different deployment actor."""
    dispatcher, sqs, _dynamo = _dispatcher()

    with pytest.raises(AgentCoreDispatchError, match="not authorized"):
        dispatcher.enqueue(_payload(actor_id="another-user"))

    assert sqs.messages == []
