"""Canonical identity and rule citations for versioned project policies."""

import hashlib
import json
from typing import cast

from pydantic import JsonValue

from asset_shepherd.models import (
    FindingRuleProvenance,
    PolicyRuleSource,
    ProfilePolicyProvenance,
    ProjectProfile,
)

_RULE_PARAMETERS: dict[str, tuple[str, ...]] = {
    "expected_height_cm": (
        "expected_height_cm.target",
        "expected_height_cm.tolerance",
    ),
    "orientation.require_y_up_geometry": ("orientation.require_y_up_geometry",),
    "orientation.require_ground_contact": (
        "orientation.require_ground_contact",
        "orientation.ground_tolerance_cm",
    ),
    "naming.pattern": ("naming.pattern",),
    "naming.require_unique_node_names": ("naming.require_unique_node_names",),
    "naming.require_unique_mesh_names": ("naming.require_unique_mesh_names",),
    "budgets.max_triangles": ("budgets.max_triangles",),
    "budgets.max_materials": ("budgets.max_materials",),
    "budgets.max_textures": ("budgets.max_textures",),
    "budgets.max_texture_dimension": ("budgets.max_texture_dimension",),
}


def canonical_profile_sha256(profile: ProjectProfile) -> str:
    """Hash one resolved profile using stable canonical JSON bytes."""
    payload = json.dumps(
        profile.model_dump(mode="json"),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_profile_policy_provenance(
    profile: ProjectProfile,
    *,
    base_preset_id: str | None = None,
    policy_family_id: str | None = None,
    explicit_overrides: dict[str, JsonValue] | None = None,
    rule_sources: dict[str, PolicyRuleSource] | None = None,
) -> ProfilePolicyProvenance:
    """Freeze policy identity and derivation metadata for provenance."""
    return ProfilePolicyProvenance(
        frozen_profile_id=profile.profile_id,
        base_preset_id=base_preset_id or profile.profile_id,
        policy_family_id=policy_family_id,
        explicit_overrides=dict(explicit_overrides or {}),
        rule_sources=dict(rule_sources or {}),
        profile_version=profile.profile_version,
        canonical_sha256=canonical_profile_sha256(profile),
    )


def validate_profile_policy_provenance(
    profile: ProjectProfile,
    policy: ProfilePolicyProvenance,
) -> None:
    """Reject metadata that does not describe the exact resolved policy."""
    if policy.frozen_profile_id != profile.profile_id:
        raise ValueError("Frozen policy identifier does not match the resolved profile")
    if policy.profile_version != profile.profile_version:
        raise ValueError("Frozen policy version does not match the resolved profile")
    if policy.policy_family_id is not None and policy.base_preset_id != policy.policy_family_id:
        raise ValueError("Policy family identifier must match the legacy base policy identifier")
    if policy.canonical_sha256 != canonical_profile_sha256(profile):
        raise ValueError("Frozen policy hash does not match the resolved profile")


def _path_value(profile: ProjectProfile, path: str) -> JsonValue:
    value: object = profile.model_dump(mode="json")
    for component in path.split("."):
        if not isinstance(value, dict) or component not in value:
            raise ValueError(f"Unsupported profile-rule path: {path}")
        value = cast(dict[str, object], value)[component]
    return cast(JsonValue, value)


def finding_rule_provenance(
    profile: ProjectProfile,
    profile_rule: str | None,
    policy: ProfilePolicyProvenance | None = None,
) -> FindingRuleProvenance | None:
    """Resolve the active parameter values behind one primary finding rule."""
    if profile_rule is None:
        return None
    parameter_paths = _RULE_PARAMETERS.get(profile_rule, (profile_rule,))
    return FindingRuleProvenance(
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
        parameters={path: _path_value(profile, path) for path in parameter_paths},
        sources={
            path: source
            for path in parameter_paths
            if policy is not None and (source := policy.rule_sources.get(path)) is not None
        },
    )
