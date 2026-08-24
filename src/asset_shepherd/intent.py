"""Deterministic construction and validation of user-confirmed asset intent."""

import json
import math
import re
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from asset_shepherd.models import AssetIntentProvenance, AssetTargetUse

TARGET_USE_LABELS = {
    AssetTargetUse.STATIC_GAME_ASSET: "static game asset",
    AssetTargetUse.RIG_READY_CHARACTER: "rig-ready character",
    AssetTargetUse.PLAYABLE_CHARACTER: "playable animated character",
}


def normalize_intent_description(value: str) -> str:
    """Normalize benign whitespace and enforce the bounded plain-text intake contract."""
    normalized = re.sub(r"\s+", " ", value).strip()
    if len(normalized) < 12:
        raise ValueError("Describe what you were trying to make in at least 12 characters.")
    if len(normalized) > 600:
        raise ValueError("Keep the asset description to 600 characters or fewer.")
    if any(ord(character) < 32 for character in normalized):
        raise ValueError("The asset description contains unsupported control characters.")
    return normalized


def target_height_cm_from_meters(value: str) -> float:
    """Parse a user-facing meter value into the canonical centimeter target."""
    try:
        meters = float(value)
    except ValueError as error:
        raise ValueError("Intended height must be a number in meters.") from error
    if not math.isfinite(meters) or meters <= 0.0 or meters > 1000.0:
        raise ValueError("Intended height must be greater than 0 and no more than 1,000 meters.")
    return meters * 100.0


def craft_confirmed_story(
    description: str,
    target_use: AssetTargetUse,
    target_height_cm: float,
) -> str:
    """Turn bounded structured intent into the exact story the user will confirm."""
    description_text = description.rstrip(".?!")
    height_m = target_height_cm / 100.0
    return (
        f"Here is what I am trying to make: {description_text}. I need it prepared as a "
        f"{TARGET_USE_LABELS[target_use]} for Unreal at {height_m:g} m tall, while preserving "
        "the described appearance and surfacing any work Asset Shepherd cannot safely perform."
    )


def _canonical_payload(
    *,
    intent_version: int,
    intent_id: str,
    original_description: str,
    target_use: AssetTargetUse,
    target_height_cm: float,
    confirmed_story: str,
    confirmed_at: datetime,
    expected_piece_count: int,
    expected_piece_count_evidence: str,
) -> dict[str, object]:
    timestamp = confirmed_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
    payload: dict[str, object] = {
        "intent_version": intent_version,
        "intent_id": intent_id,
        "original_description": original_description,
        "target_use": target_use.value,
        "target_height_cm": target_height_cm,
        "confirmed_story": confirmed_story,
        "confirmed_at": timestamp,
    }
    if intent_version >= 2:
        payload["expected_piece_count"] = expected_piece_count
        payload["expected_piece_count_evidence"] = expected_piece_count_evidence
    return payload


def _canonical_sha256(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def build_asset_intent(
    description: str,
    target_use: AssetTargetUse,
    target_height_cm: float,
    *,
    expected_piece_count: int = 1,
    expected_piece_count_evidence: str = (
        "A single asset is normally expected as one semantic piece."
    ),
    intent_id: str | None = None,
    confirmed_at: datetime | None = None,
) -> AssetIntentProvenance:
    """Build one immutable, canonically hashed target story."""
    normalized = normalize_intent_description(description)
    resolved_id = intent_id or uuid4().hex
    resolved_time = confirmed_at or datetime.now(UTC)
    story = craft_confirmed_story(normalized, target_use, target_height_cm)
    payload = _canonical_payload(
        intent_version=2,
        intent_id=resolved_id,
        original_description=normalized,
        target_use=target_use,
        target_height_cm=target_height_cm,
        confirmed_story=story,
        confirmed_at=resolved_time,
        expected_piece_count=expected_piece_count,
        expected_piece_count_evidence=expected_piece_count_evidence,
    )
    return AssetIntentProvenance(
        intent_id=resolved_id,
        original_description=normalized,
        target_use=target_use,
        target_height_cm=target_height_cm,
        expected_piece_count=expected_piece_count,
        expected_piece_count_evidence=expected_piece_count_evidence,
        confirmed_story=story,
        confirmed_at=resolved_time,
        canonical_sha256=_canonical_sha256(payload),
    )


def validate_asset_intent(intent: AssetIntentProvenance) -> None:
    """Reject a target story whose canonical identity no longer matches its fields."""
    payload = _canonical_payload(
        intent_version=intent.intent_version,
        intent_id=intent.intent_id,
        original_description=intent.original_description,
        target_use=intent.target_use,
        target_height_cm=intent.target_height_cm,
        confirmed_story=intent.confirmed_story,
        confirmed_at=intent.confirmed_at,
        expected_piece_count=intent.expected_piece_count,
        expected_piece_count_evidence=intent.expected_piece_count_evidence,
    )
    if intent.canonical_sha256 != _canonical_sha256(payload):
        raise ValueError("Confirmed asset intent hash does not match its fields")
