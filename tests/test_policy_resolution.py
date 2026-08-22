"""Acceptance for intent-aware resolution of the one versioned policy family."""

from pathlib import Path

import pytest

from asset_shepherd.models import AssetTargetUse, ProjectProfile
from asset_shepherd.policy_resolution import resolve_policy_family

PROJECT_ROOT = Path(__file__).resolve().parents[1]


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


def test_confirmed_lantern_intent_drives_height_and_suspended_grounding() -> None:
    """The resolver uses provided target state instead of asking for a scale preset."""
    resolution = resolve_policy_family(
        _family(),
        description="A stylized lantern hanging from a ceiling bracket for a game scene.",
        target_use=AssetTargetUse.STATIC_GAME_ASSET,
        target_height_cm=120.0,
    )

    assert resolution.profile.expected_height_cm.target == 120.0
    assert resolution.profile.expected_height_cm.tolerance == 6.0
    assert not resolution.profile.orientation.require_ground_contact
    assert resolution.provenance.policy_family_id == _family().profile_id
    assert resolution.provenance.rule_sources["expected_height_cm.target"] == ("CONFIRMED_INTENT")
    assert resolution.provenance.rule_sources["orientation.require_ground_contact"] == (
        "DERIVED_INTENT"
    )


def test_unspecified_rules_use_family_defaults_and_supported_user_values_are_cited() -> None:
    """Missing project specifics stay conservative while explicit supported edits remain visible."""
    resolution = resolve_policy_family(
        _family(),
        description="A standing friendly repair robot used as a static Unreal game prop.",
        target_use=AssetTargetUse.STATIC_GAME_ASSET,
        target_height_cm=180.0,
        user_overrides={"budgets.max_triangles": 25000},
    )

    assert resolution.profile.orientation.require_ground_contact
    assert resolution.profile.budgets.max_triangles == 25000
    assert resolution.profile.budgets.max_materials == 8
    assert resolution.provenance.rule_sources["budgets.max_triangles"] == "USER_OVERRIDE"
    assert resolution.provenance.rule_sources["budgets.max_materials"] == "FAMILY_DEFAULT"


def test_policy_resolver_rejects_safety_and_unsupported_domains() -> None:
    """A model or advanced user cannot expand the editable ProjectProfile boundary."""
    with pytest.raises(ValueError, match="Unsupported policy override"):
        resolve_policy_family(
            _family(),
            description="A static game prop with a clear intended real-world target.",
            target_use=AssetTargetUse.STATIC_GAME_ASSET,
            target_height_cm=100.0,
            user_overrides={"repair_policy.require_approval_for_normalization_transform": False},
        )
