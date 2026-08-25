"""Tests for the bounded, user-confirmed target-story contract."""

from datetime import UTC, datetime

import pytest

from asset_shepherd.intent import build_asset_intent, validate_asset_intent
from asset_shepherd.models import AssetTargetUse


def test_asset_intent_is_canonical_and_reproducible() -> None:
    """The same confirmed fields produce the same immutable identity."""
    confirmed_at = datetime(2026, 8, 22, 16, 30, tzinfo=UTC)
    first = build_asset_intent(
        "  A shader lantern with warm light and translucent glass.  ",
        AssetTargetUse.STATIC_GAME_ASSET,
        120.0,
        expected_piece_count=2,
        expected_piece_count_evidence="The description identifies a matched lantern pair.",
        intent_id="a" * 32,
        confirmed_at=confirmed_at,
    )
    second = build_asset_intent(
        "  A shader lantern with warm light and translucent glass.  ",
        AssetTargetUse.STATIC_GAME_ASSET,
        120.0,
        expected_piece_count=2,
        expected_piece_count_evidence="The description identifies a matched lantern pair.",
        intent_id="a" * 32,
        confirmed_at=confirmed_at,
    )

    assert first == second
    assert first.original_description == ("A shader lantern with warm light and translucent glass.")
    assert "static game asset at 1.2 m tall" in first.confirmed_story
    assert first.expected_piece_count == 2
    validate_asset_intent(first)


def test_asset_intent_hash_rejects_tampering() -> None:
    """Changing confirmed target state invalidates the provenance identity."""
    intent = build_asset_intent(
        "A science-fiction armored character with orange emissive accents.",
        AssetTargetUse.PLAYABLE_CHARACTER,
        172.0,
        intent_id="b" * 32,
        confirmed_at=datetime(2026, 8, 22, 17, 0, tzinfo=UTC),
    )
    tampered = intent.model_copy(update={"target_height_cm": 180.0})

    with pytest.raises(ValueError, match="hash does not match"):
        validate_asset_intent(tampered)
