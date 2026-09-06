"""Zero-network acceptance of shared model spending admission and settlement."""

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock

import httpx
import pytest
from botocore.exceptions import ClientError, EndpointConnectionError
from strands.models.model import Model
from strands.types.streaming import StreamEvent

from asset_shepherd.spending import (
    SpendLedger,
    SpendLimitError,
    billable_call,
    configured_ledger,
    rate_for,
    usage_cost,
)
from asset_shepherd.spending_model import SpendingModel

NOW = datetime(2026, 9, 6, 23, 59, tzinfo=UTC)
MODEL = "gpt-5.6-luna"
RATE = rate_for("openai", MODEL)


def _cancel(index: int) -> ClientError:
    return ClientError(
        {
            "Error": {"Code": "TransactionCanceledException", "Message": "Rejected"},
            "CancellationReasons": [
                {"Code": "ConditionalCheckFailed" if i == index else "None"} for i in range(3)
            ],
        },
        "TransactWriteItems",
    )


def _ledger(ceiling: int = 10_000_000) -> tuple[SpendLedger, Mock]:
    client = Mock()
    client.get_item.return_value = {"Item": {"charged": {"N": "0"}}}
    return SpendLedger("workspace-table", ceiling, client=client, clock=lambda: NOW), client


def test_rates_are_conservative_and_unknown_models_fail_closed() -> None:
    """Never guess a new provider price or silently omit its spending."""
    assert RATE.reservation == 539_746
    assert usage_cost(RATE, {"input_tokens": 1000, "output_tokens": 100}) == 680
    kimi = rate_for("bedrock-converse", "moonshotai.kimi-k2.5")
    assert (
        usage_cost(
            kimi,
            {
                "inputTokens": 1000,
                "outputTokens": 100,
                "cacheReadInputTokens": 200,
                "cacheWriteInputTokens": 100,
            },
        )
        == 1080
    )
    with pytest.raises(SpendLimitError):
        rate_for("meta", "unapproved-rate")
    assert configured_ledger({}) is None


@pytest.mark.parametrize(
    "usage",
    [
        None,
        {},
        {"input_tokens": 2},
        {"input_tokens": True, "output_tokens": 1},
        {"input_tokens": -1, "output_tokens": 1},
        {"input_tokens": 1, "output_tokens": 8193},
        {"input_tokens": 1, "output_tokens": 1, "cacheReadInputTokens": "100"},
    ],
)
def test_incomplete_usage_never_earns_a_refund(usage: object) -> None:
    """Treat uncertain charges as the full reserved request envelope."""
    assert usage_cost(RATE, usage) is None


def test_admission_atomically_reserves_total_receipt_and_slot() -> None:
    """Place the shared counter condition in the same transaction as the request lease."""
    ledger, client = _ledger()
    reservation = ledger.reserve("openai", MODEL)
    call = client.transact_write_items.call_args.kwargs
    total, receipt, slot = call["TransactItems"]
    assert total["Update"]["Key"] == {"PK": {"S": "SPEND#2026-09-06"}, "SK": {"S": "TOTAL"}}
    assert total["Update"]["ExpressionAttributeValues"][":room"] == {"N": "9460254"}
    assert "charged <= :room" in total["Update"]["ConditionExpression"]
    assert receipt["Put"]["Item"]["amount"] == {"N": str(RATE.reservation)}
    assert slot["Put"]["Item"]["holder"] == {"S": reservation.call_id}
    assert "expires_at_epoch < :now" in slot["Put"]["ConditionExpression"]
    assert len(call["ClientRequestToken"]) <= 36
    assert "WORKSPACE#" not in str(call) and "COMMAND#" not in str(call)


def test_denied_reservation_never_calls_provider() -> None:
    """Refuse a paid call before transmission when the shared daily room is exhausted."""
    ledger, client = _ledger()
    client.transact_write_items.side_effect = _cancel(0)
    provider = Mock()
    with pytest.raises(SpendLimitError, match="saved assets and downloads"):
        billable_call(ledger, "openai", MODEL, provider, lambda result: result)
    provider.assert_not_called()
    assert client.transact_write_items.call_count == 1


def test_no_reservation_larger_than_entire_ceiling() -> None:
    """Protect even a new day with no counter yet."""
    ledger, client = _ledger(1)
    with pytest.raises(SpendLimitError):
        ledger.reserve("openai", MODEL)
    client.transact_write_items.assert_not_called()


def test_three_busy_slots_stop_without_charging_a_separate_counter() -> None:
    """Each failed slot attempt rolls back the charge in the same DynamoDB transaction."""
    ledger, client = _ledger()
    client.transact_write_items.side_effect = _cancel(2)
    with pytest.raises(SpendLimitError, match="busy"):
        ledger.reserve("openai", MODEL)
    assert client.transact_write_items.call_count == 3
    assert [
        call.kwargs["TransactItems"][2]["Put"]["Item"]["SK"]["S"]
        for call in client.transact_write_items.call_args_list
    ] == ["0", "1", "2"]


def test_transport_failure_before_admission_fails_closed() -> None:
    """Do not risk inference when a DynamoDB transaction outcome is uncertain."""
    ledger, client = _ledger()
    client.transact_write_items.side_effect = EndpointConnectionError(
        endpoint_url="https://invalid"
    )
    with pytest.raises(SpendLimitError, match="unavailable"):
        ledger.reserve("openai", MODEL)


def test_settlement_refunds_once_to_original_day_and_releases_only_own_slot() -> None:
    """A midnight-crossing call cannot refund a new day or release another call's lease."""
    ledger, client = _ledger()
    reservation = ledger.reserve("openai", MODEL)
    ledger.clock = lambda: NOW + timedelta(minutes=2)
    reservation.finish({"input_tokens": 1000, "output_tokens": 100})
    transaction = client.transact_write_items.call_args.kwargs["TransactItems"]
    receipt, refund = transaction
    assert receipt["Update"]["ConditionExpression"] == "#s = :reserved"
    assert receipt["Update"]["ExpressionAttributeValues"][":amount"] == {"N": "680"}
    assert refund["Update"]["Key"]["PK"] == {"S": "SPEND#2026-09-06"}
    assert refund["Update"]["ExpressionAttributeValues"][":refund"] == {"N": "-539066"}
    release = client.delete_item.call_args.kwargs
    assert release["ConditionExpression"] == "holder = :holder"
    assert release["ExpressionAttributeValues"][":holder"] == {"S": reservation.call_id}
    client.transact_write_items.side_effect = _cancel(0)
    reservation.finish({"input_tokens": 1000, "output_tokens": 100})
    # There is no unconditional refund fallback after the duplicate transaction fails.
    client.update_item.assert_not_called()


def test_provider_failure_keeps_charge_and_does_not_mask_original_error() -> None:
    """Charge uncertain provider outcomes while preserving the underlying failure."""
    ledger, client = _ledger()
    provider = Mock(side_effect=RuntimeError("provider stopped"))
    with pytest.raises(RuntimeError, match="provider stopped"):
        billable_call(ledger, "openai", MODEL, provider, lambda result: result)
    receipt, refund = client.transact_write_items.call_args.kwargs["TransactItems"]
    assert receipt["Update"]["ExpressionAttributeValues"][":done"] == {"S": "UNKNOWN"}
    assert refund["Update"]["ExpressionAttributeValues"][":refund"] == {"N": "0"}


def test_usage_and_local_passthrough() -> None:
    """Reconcile successful nonstreaming intake without changing the returned response."""
    ledger, client = _ledger()
    result = {"usage": {"input_tokens": 20, "output_tokens": 5}, "content": "test"}
    provider = Mock(return_value=result)
    assert billable_call(ledger, "openai", MODEL, provider, lambda r: r["usage"]) is result
    assert client.transact_write_items.call_count == 2
    assert billable_call(None, "local", "test", provider, lambda r: r) is result


def test_warning_thresholds_reuse_private_topic_and_allow_delivery_retry() -> None:
    """Warn at $5 and $8 and retry failed delivery instead of losing the marker forever."""
    ledger, client = _ledger()
    ledger.sns, ledger.topic = Mock(), "owner-topic"
    client.get_item.return_value = {"Item": {"charged": {"N": "8100000"}}}
    ledger.reserve("openai", MODEL).finish({"input_tokens": 1, "output_tokens": 1})
    assert ledger.sns.publish.call_count == 2
    assert [c.kwargs["Subject"] for c in ledger.sns.publish.call_args_list] == [
        "Asset Shepherd model-spend safety: 50%",
        "Asset Shepherd model-spend safety: 80%",
    ]
    assert "retry_after < :now" in client.put_item.call_args.kwargs["ConditionExpression"]
    ledger.sns.publish.side_effect = EndpointConnectionError(endpoint_url="https://invalid")
    client.update_item.reset_mock()
    ledger.notify("2026-09-06", 100)
    client.update_item.assert_not_called()


def test_streaming_wraps_every_call_preserving_state_and_usage() -> None:
    """Meter tool-loop requests individually without losing Responses conversation state."""
    ledger, client = _ledger()
    inner = Mock()
    inner.stateful = True

    async def stream(*_args: object, **_kwargs: object) -> AsyncGenerator[StreamEvent, None]:
        yield {"metadata": {"usage": {"inputTokens": 100, "outputTokens": 10, "totalTokens": 110}}}

    inner.stream = stream
    wrapped = SpendingModel(cast(Model, inner), ledger, "openai", MODEL)
    assert wrapped.stateful is True

    async def collect() -> None:
        for _ in range(2):
            assert len([event async for event in wrapped.stream([])]) == 1

    asyncio.run(collect())
    assert client.transact_write_items.call_count == 4
    with pytest.raises(ValueError, match="immutable"):
        wrapped.update_config(max_output_tokens=999999)


def test_both_cloud_tiers_use_one_table_and_same_default_ceiling() -> None:
    """Never meter only the browser while leaving the paid repair runtime unbounded."""
    root = Path(__file__).resolve().parents[1] / "infra" / "cloudformation"
    for name in ("web-express.yaml", "agentcore-runtime.yaml"):
        template = (root / name).read_text(encoding="utf-8")
        assert "DailyModelUsd:\n    Type: Number\n    Default: 10" in template
        assert "ASSET_SHEPHERD_SPEND_TABLE" in template
        assert "ASSET_SHEPHERD_DAILY_MODEL_USD" in template
        assert "ASSET_SHEPHERD_SPEND_ALERT_TOPIC" in template
        assert "Action: sns:Publish\n                Resource: !Ref SpendAlertTopicArn" in template


def test_stateful_request_metadata_is_not_accidentally_dropped() -> None:
    """Accept the actual Strands usage spelling rather than charging every call's maximum."""
    usage: dict[str, Any] = {"inputTokens": 1200, "outputTokens": 300, "totalTokens": 1500}
    assert usage_cost(RATE, usage) == 1140
    usage["cacheReadInputTokens"] = 1000
    assert usage_cost(RATE, usage) == 1140  # OpenAI already includes cached input.


def test_saved_budget_failures_keep_actionable_public_message() -> None:
    """Do not turn a deliberate cost pause into the generic workflow failure banner."""
    from asset_shepherd.spending import PUBLIC_SPEND_MESSAGES
    from asset_shepherd.web import (
        _persisted_workflow_error_message,  # pyright: ignore[reportPrivateUsage]
    )

    for message in PUBLIC_SPEND_MESSAGES:
        assert _persisted_workflow_error_message(message) == message


def test_each_openai_intake_attempt_is_metered_before_http() -> None:
    """Retrying the size proposal requires a new reservation, not one for the whole intake."""
    from asset_shepherd.intake_analyzer import (
        OpenAITargetIntakeAnalyzer,
        OpenAITargetIntakeConfiguration,
        TargetIntakeAnalysisError,
    )

    ledger, db = _ledger()
    count = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        assert db.transact_write_items.call_count == count * 2 - 1
        return httpx.Response(200, json={"usage": {"input_tokens": 100, "output_tokens": 10}})

    analyzer = OpenAITargetIntakeAnalyzer(OpenAITargetIntakeConfiguration(api_key="test-only"))
    analyzer.spending_ledger = ledger
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        for retry in (False, True):
            analyzer._metered_post(client, {}, "A wooden table", retry)  # pyright: ignore[reportPrivateUsage]
        db.transact_write_items.side_effect = _cancel(0)
        with pytest.raises(TargetIntakeAnalysisError, match="spending safety limit"):
            analyzer._metered_post(client, {}, "A wooden table", True)  # pyright: ignore[reportPrivateUsage]
    assert count == 2


def test_provider_factories_cannot_lose_hosted_ledger(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both workflow and intake bind the configured safety control; unpriced intake fails closed."""
    from asset_shepherd.agent_runtime import build_environment_model
    from asset_shepherd.intake_analyzer import (
        OpenAITargetIntakeAnalyzer,
        TargetIntakeAnalysisError,
        build_target_intake_analyzer,
    )

    ledger, _ = _ledger()
    monkeypatch.setattr("asset_shepherd.spending.configured_ledger", lambda _values: ledger)
    monkeypatch.setattr("asset_shepherd.intake_analyzer.configured_ledger", lambda _values: ledger)
    values = {
        "ASSET_SHEPHERD_MODEL_PROVIDER": "openai",
        "ASSET_SHEPHERD_MODEL_ID": MODEL,
        "ASSET_SHEPHERD_INTAKE_PROVIDER": "openai",
        "OPENAI_API_KEY": "test-only",
    }
    model, _ = build_environment_model(values)
    assert isinstance(model, SpendingModel) and model.ledger is ledger
    intake = build_target_intake_analyzer(values)
    assert isinstance(intake, OpenAITargetIntakeAnalyzer) and intake.spending_ledger is ledger
    with pytest.raises(TargetIntakeAnalysisError, match="spending accounting"):
        build_target_intake_analyzer({**values, "ASSET_SHEPHERD_INTAKE_PROVIDER": "meta"})


def test_stream_failure_keeps_reservation_without_usage() -> None:
    """Missing usage after a failed stream never becomes a free request."""
    ledger, db = _ledger()
    inner = Mock()

    async def stream(*_args: object, **_kwargs: object) -> AsyncGenerator[StreamEvent, None]:
        raise RuntimeError("stream stopped")
        yield {}  # pragma: no cover

    inner.stream = stream
    wrapped = SpendingModel(cast(Model, inner), ledger, "openai", MODEL)

    async def collect() -> None:
        async for _event in wrapped.stream([]):
            pass

    with pytest.raises(RuntimeError, match="stream stopped"):
        asyncio.run(collect())
    refund = db.transact_write_items.call_args.kwargs["TransactItems"][1]
    assert refund["Update"]["ExpressionAttributeValues"][":refund"] == {"N": "0"}
