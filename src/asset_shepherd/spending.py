"""Shared, conservative model-spend admission independent of asset retention.

Amounts are integer micro-USD. Reservations charge the full supported request envelope
before inference; only complete usage can refund it. Unknown outcomes remain charged.
This is an application safety estimate, not a provider invoice or an AWS billing cap.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, cast
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

LOGGER = logging.getLogger(__name__)
PAUSED_MESSAGE = (
    "Paid analysis is temporarily paused by the site's spending safety limit. "
    "Your saved assets and downloads remain available. Please try again later."
)
UNAVAILABLE_MESSAGE = "The spending safety check is unavailable. Try again later."
BUSY_MESSAGE = "The site is busy with other analyses. Please try again shortly."
UNPRICED_MESSAGE = "This model needs an approved spending rate before hosted use."
PUBLIC_SPEND_MESSAGES = (PAUSED_MESSAGE, UNAVAILABLE_MESSAGE, BUSY_MESSAGE, UNPRICED_MESSAGE)


class SpendLimitError(ValueError):
    """Safe, nonretryable failure before a provider request starts."""


@dataclass(frozen=True)
class Rate:
    """Conservative standard-service rates and maximum supported request envelope."""

    input_rate: Decimal  # USD per million tokens equals micro-USD per token.
    output_rate: Decimal
    max_input: int
    max_output: int
    cache_tokens_separate: bool = False

    def cost(self, input_tokens: int, output_tokens: int) -> int:
        """Round up without applying speculative cache discounts."""
        return math.ceil(input_tokens * self.input_rate + output_tokens * self.output_rate)

    @property
    def reservation(self) -> int:
        """Reserve the full context/output envelope, not a character-count guess."""
        return self.cost(self.max_input, self.max_output)


def rate_for(provider: str, model_id: str) -> Rate:
    """Reject unpriced providers rather than silently bypass the shared safety ledger."""
    if provider == "openai" and model_id == "gpt-5.6-luna":
        # Includes long-context 2x input / 1.5x output and 1.25x cache-write input.
        return Rate(Decimal("0.50"), Decimal("1.80"), 1_050_000, 8192)
    if provider == "bedrock-converse" and model_id == "moonshotai.kimi-k2.5":
        return Rate(Decimal("0.60"), Decimal("3.00"), 262_144, 16_384, cache_tokens_separate=True)
    raise SpendLimitError(UNPRICED_MESSAGE)


def usage_cost(rate: Rate, usage: object) -> int | None:
    """Read Responses/Converse usage including separately reported Bedrock cache tokens."""
    if not isinstance(usage, dict):
        return None
    fields = cast(dict[str, object], usage)
    incoming = fields.get("input_tokens", fields.get("inputTokens"))
    outgoing = fields.get("output_tokens", fields.get("outputTokens"))
    if type(incoming) is not int or type(outgoing) is not int or incoming < 0 or outgoing < 0:
        return None
    # Converse cached tokens are separate; OpenAI input_tokens already includes them.
    for key in ("cacheReadInputTokens", "cacheWriteInputTokens"):
        value = fields.get(key, 0)
        if type(value) is not int or value < 0:
            return None
        if rate.cache_tokens_separate:
            incoming += value
    if incoming > rate.max_input or outgoing > rate.max_output:
        return None  # Retain the reservation and require rate-envelope review.
    return rate.cost(incoming, outgoing)


class SpendLedger:
    """One UTC daily counter and three provider-call leases in the existing DynamoDB table."""

    def __init__(
        self,
        table: str,
        ceiling: int,
        *,
        client: Any,  # noqa: ANN401 — boto3 low-level DynamoDB boundary
        sns: Any = None,  # noqa: ANN401 — boto3 SNS boundary
        topic: str = "",
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind trusted deployment configuration; no user data enters ledger keys."""
        self.table, self.ceiling = table, ceiling
        self.client, self.sns, self.topic, self.clock = client, sns, topic, clock

    def reserve(self, provider: str, model_id: str) -> SpendReservation:
        """Atomically charge a request and acquire a bounded, expiring concurrency slot."""
        rate = rate_for(provider, model_id)
        if rate.reservation > self.ceiling:
            raise SpendLimitError(PAUSED_MESSAGE)
        now = self.clock().astimezone(UTC)
        day = now.strftime("%Y-%m-%d")
        call_id = uuid4().hex
        pk = f"SPEND#{day}"
        ttl = str(int((now + timedelta(days=45)).timestamp()))
        total_key = {"PK": {"S": pk}, "SK": {"S": "TOTAL"}}
        for slot in range(3):
            try:
                self.client.transact_write_items(
                    ClientRequestToken=call_id + str(slot),
                    TransactItems=[
                        {
                            "Update": {
                                "TableName": self.table,
                                "Key": total_key,
                                "UpdateExpression": (
                                    "SET expires_at_epoch = :ttl ADD charged :amount"
                                ),
                                "ConditionExpression": (
                                    "attribute_not_exists(charged) OR charged <= :room"
                                ),
                                "ExpressionAttributeValues": {
                                    ":ttl": {"N": ttl},
                                    ":amount": {"N": str(rate.reservation)},
                                    ":room": {"N": str(self.ceiling - rate.reservation)},
                                },
                            }
                        },
                        {
                            "Put": {
                                "TableName": self.table,
                                "Item": {
                                    "PK": {"S": pk},
                                    "SK": {"S": f"CALL#{call_id}"},
                                    "state": {"S": "RESERVED"},
                                    "amount": {"N": str(rate.reservation)},
                                    "provider": {"S": provider},
                                    "model": {"S": model_id},
                                    "expires_at_epoch": {"N": ttl},
                                },
                                "ConditionExpression": "attribute_not_exists(PK)",
                            }
                        },
                        {
                            "Put": {
                                "TableName": self.table,
                                "Item": {
                                    "PK": {"S": "SPEND#SLOTS"},
                                    "SK": {"S": str(slot)},
                                    "holder": {"S": call_id},
                                    "expires_at_epoch": {"N": str(int(now.timestamp()) + 1800)},
                                },
                                "ConditionExpression": (
                                    "attribute_not_exists(PK) OR expires_at_epoch < :now"
                                ),
                                "ExpressionAttributeValues": {
                                    ":now": {"N": str(int(now.timestamp()))}
                                },
                            }
                        },
                    ],
                )
                return SpendReservation(self, rate, pk, call_id, slot)
            except ClientError as error:
                if error.response.get("Error", {}).get("Code") == "TransactionCanceledException":
                    reasons = error.response.get("CancellationReasons", [])
                    if reasons and reasons[0].get("Code") == "ConditionalCheckFailed":
                        self.notify(day, 100)
                        raise SpendLimitError(PAUSED_MESSAGE) from None
                    if len(reasons) > 2 and reasons[2].get("Code") == "ConditionalCheckFailed":
                        continue
                raise SpendLimitError(UNAVAILABLE_MESSAGE) from None
            except BotoCoreError:
                raise SpendLimitError(UNAVAILABLE_MESSAGE) from None
        raise SpendLimitError(BUSY_MESSAGE)

    def notify(self, day: str, percent: int) -> None:
        """Send an owner-only alert without prompts, identities, or credentials."""
        if self.sns is None or not self.topic:
            return
        try:
            self.client.put_item(
                TableName=self.table,
                Item={
                    "PK": {"S": f"SPEND#{day}"},
                    "SK": {"S": f"ALERT#{percent}"},
                    "retry_after": {"N": str(int(self.clock().timestamp()) + 60)},
                    "expires_at_epoch": {"N": str(int(self.clock().timestamp()) + 45 * 86400)},
                },
                ConditionExpression=(
                    "attribute_not_exists(PK) OR "
                    "(attribute_not_exists(delivered) AND retry_after < :now)"
                ),
                ExpressionAttributeValues={":now": {"N": str(int(self.clock().timestamp()))}},
            )
            status = (
                "there is insufficient unreserved budget for another request"
                if percent == 100
                else f"estimated spending plus active reservations reached {percent}%"
            )
            self.sns.publish(
                TopicArn=self.topic,
                Subject=f"Asset Shepherd model-spend safety: {percent}%",
                Message=(
                    f"UTC day {day}: {status}. "
                    f"Daily safety ceiling: ${self.ceiling / 1_000_000:.2f}. "
                    "This excludes hosting and is not a provider invoice. Review the ledger "
                    "before raising the ceiling. Saved assets and downloads remain available."
                ),
            )
            self.client.update_item(
                TableName=self.table,
                Key={"PK": {"S": f"SPEND#{day}"}, "SK": {"S": f"ALERT#{percent}"}},
                UpdateExpression="SET delivered = :yes",
                ExpressionAttributeValues={":yes": {"BOOL": True}},
            )
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
                LOGGER.error("Model-spend notification failed; inspect the daily ledger.")
        except BotoCoreError:
            LOGGER.error("Model-spend notification transport failed; inspect the daily ledger.")


@dataclass
class SpendReservation:
    """A single request's admission and exactly-once conservative reconciliation."""

    ledger: SpendLedger
    rate: Rate
    day_key: str
    call_id: str
    slot: int

    def finish(self, usage: object = None) -> None:
        """Unknown/missing usage retains the maximum; duplicate settlement cannot refund twice."""
        amount = usage_cost(self.rate, usage)
        charged = self.rate.reservation if amount is None else amount
        c = self.ledger.client
        try:
            c.transact_write_items(
                TransactItems=[
                    {
                        "Update": {
                            "TableName": self.ledger.table,
                            "Key": {"PK": {"S": self.day_key}, "SK": {"S": f"CALL#{self.call_id}"}},
                            "UpdateExpression": "SET #s = :done, amount = :amount",
                            "ConditionExpression": "#s = :reserved",
                            "ExpressionAttributeNames": {"#s": "state"},
                            "ExpressionAttributeValues": {
                                ":done": {"S": "UNKNOWN" if amount is None else "SETTLED"},
                                ":reserved": {"S": "RESERVED"},
                                ":amount": {"N": str(charged)},
                            },
                        }
                    },
                    {
                        "Update": {
                            "TableName": self.ledger.table,
                            "Key": {"PK": {"S": self.day_key}, "SK": {"S": "TOTAL"}},
                            "UpdateExpression": "ADD charged :refund",
                            "ExpressionAttributeValues": {
                                ":refund": {"N": str(charged - self.rate.reservation)}
                            },
                        }
                    },
                ]
            )
        except (ClientError, BotoCoreError):
            LOGGER.error(
                "Model-spend settlement unavailable or already settled; reservation retained."
            )
        finally:
            try:
                c.delete_item(
                    TableName=self.ledger.table,
                    Key={"PK": {"S": "SPEND#SLOTS"}, "SK": {"S": str(self.slot)}},
                    ConditionExpression="holder = :holder",
                    ExpressionAttributeValues={":holder": {"S": self.call_id}},
                )
            except (ClientError, BotoCoreError):
                LOGGER.error("Model-spend slot release failed; its safety lease will expire.")
        try:
            item = c.get_item(
                TableName=self.ledger.table,
                Key={"PK": {"S": self.day_key}, "SK": {"S": "TOTAL"}},
                ConsistentRead=True,
            ).get("Item", {})
            total = int(item.get("charged", {}).get("N", "0"))
            for threshold in (50, 80):
                if total * 100 >= self.ledger.ceiling * threshold:
                    self.ledger.notify(self.day_key.removeprefix("SPEND#"), threshold)
        except (ClientError, BotoCoreError, ValueError):
            LOGGER.error("Model-spend alert check unavailable.")


def configured_ledger(values: Mapping[str, str]) -> SpendLedger | None:
    """Local/offline behavior is unchanged unless a ledger is explicitly configured."""
    table = values.get("ASSET_SHEPHERD_SPEND_TABLE", "")
    if not table:
        return None
    ceiling = int(Decimal(values.get("ASSET_SHEPHERD_DAILY_MODEL_USD", "10")) * 1_000_000)
    if not 1_000_000 <= ceiling <= 100_000_000:
        raise ValueError("Daily model ceiling must be between $1 and $100")
    session = boto3.Session(
        region_name=values.get("ASSET_SHEPHERD_AWS_REGION", values.get("AWS_REGION", "us-east-1"))
    )
    config = Config(connect_timeout=5, read_timeout=10, retries={"total_max_attempts": 2})
    topic = values.get("ASSET_SHEPHERD_SPEND_ALERT_TOPIC", "")
    return SpendLedger(
        table,
        ceiling,
        client=session.client("dynamodb", config=config),  # pyright: ignore[reportUnknownMemberType]
        sns=session.client("sns", config=config) if topic else None,  # pyright: ignore[reportUnknownMemberType]
        topic=topic,
    )


def billable_call[T](
    ledger: SpendLedger | None,
    provider: str,
    model_id: str,
    call: Callable[[], T],
    usage: Callable[[T], object],
) -> T:
    """Account for one non-streaming request even when parsing or transport fails."""
    if ledger is None:
        return call()
    reservation = ledger.reserve(provider, model_id)
    measured: object = None
    try:
        result = call()
        measured = usage(result)
        return result
    finally:
        reservation.finish(measured)
