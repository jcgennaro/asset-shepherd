"""Resolve one bounded policy family into a frozen job-specific profile."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import cast

from pydantic import JsonValue, ValidationError

from asset_shepherd.models import (
    AssetTargetUse,
    PolicyRuleSource,
    ProfilePolicyProvenance,
    ProjectProfile,
)
from asset_shepherd.profile_policy import build_profile_policy_provenance

SUPPORTED_USER_OVERRIDE_PATHS = frozenset(
    {
        "expected_height_cm.tolerance",
        "orientation.require_y_up_geometry",
        "orientation.require_ground_contact",
        "orientation.ground_tolerance_cm",
        "naming.pattern",
        "budgets.max_triangles",
        "budgets.max_materials",
        "budgets.max_textures",
        "budgets.max_texture_dimension",
    }
)

_AIRBORNE_LANGUAGE = re.compile(
    r"\b(?:hang(?:ing|s)?|suspend(?:ed|ed from|ing)?|wall[- ]mounted|ceiling[- ]mounted|"
    r"float(?:ing|s)?|hover(?:ing|s)?|airborne)\b",
    re.IGNORECASE,
)
_GROUNDED_LANGUAGE = re.compile(
    r"\b(?:grounded|standing|stands on|resting on|placed on|sits on|floor[- ]standing)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ResolvedRule:
    """One active policy value plus the bounded evidence used to choose it."""

    path: str
    label: str
    value: JsonValue
    source: PolicyRuleSource
    rationale: str


@dataclass(frozen=True)
class PolicyResolution:
    """A validated, frozen ProjectProfile and its human-reviewable derivation."""

    family: ProjectProfile
    profile: ProjectProfile
    provenance: ProfilePolicyProvenance
    display_name: str
    rules: tuple[ResolvedRule, ...]


def _set_path(values: dict[str, object], path: str, value: JsonValue) -> None:
    section_name, field_name = path.split(".", maxsplit=1)
    section = values.get(section_name)
    if not isinstance(section, dict):
        raise ValueError(f"The policy family has no supported parameter {path}.")
    cast(dict[str, object], section)[field_name] = value


def _get_path(values: dict[str, JsonValue], path: str) -> JsonValue:
    current: JsonValue = values
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"The policy family has no supported parameter {path}.")
        current = current[part]
    return current


def _bounded_height_tolerance(target_height_cm: float) -> float:
    """Use five percent of intended height, bounded to a useful 1-10 cm band."""
    return round(max(1.0, min(10.0, target_height_cm * 0.05)), 6)


def _bounded_ground_tolerance(target_height_cm: float) -> float:
    """Use half a percent of intended height, bounded to 0.1-1 cm."""
    return round(max(0.1, min(1.0, target_height_cm * 0.005)), 6)


def _ground_contact_from_intent(description: str, family_default: bool) -> tuple[bool, str]:
    if _GROUNDED_LANGUAGE.search(description):
        return True, "The confirmed description explicitly places the asset on a support surface."
    if _AIRBORNE_LANGUAGE.search(description):
        return (
            False,
            "The confirmed description explicitly describes a suspended or airborne asset.",
        )
    return (
        family_default,
        "The description does not contradict the family's grounded-asset default.",
    )


def _validate_naming_pattern(pattern: str) -> None:
    if len(pattern) > 128:
        raise ValueError("The naming pattern must be at most 128 characters.")
    try:
        compiled = re.compile(pattern)
    except re.error as error:
        raise ValueError(f"The naming pattern is invalid: {error}.") from error
    if any(compiled.fullmatch(name) is None for name in ("Node_000", "Mesh_000")):
        raise ValueError(
            "The naming pattern must allow deterministic names such as Node_000 and Mesh_000."
        )


def resolve_policy_family(
    family: ProjectProfile,
    *,
    description: str,
    target_use: AssetTargetUse,
    target_height_cm: float,
    user_overrides: dict[str, JsonValue] | None = None,
) -> PolicyResolution:
    """Derive supported target rules, validate them, and freeze canonical provenance."""
    if not math.isfinite(target_height_cm) or target_height_cm <= 0.0:
        raise ValueError("Target height must be a positive finite number.")
    overrides = dict(user_overrides or {})
    unsupported = sorted(set(overrides) - SUPPORTED_USER_OVERRIDE_PATHS)
    if unsupported:
        raise ValueError(f"Unsupported policy override: {unsupported[0]}.")
    naming_pattern = overrides.get("naming.pattern", family.naming.pattern)
    if not isinstance(naming_pattern, str):
        raise ValueError("The naming pattern must be text.")
    _validate_naming_pattern(naming_pattern)

    require_ground_contact, grounding_rationale = _ground_contact_from_intent(
        description,
        family.orientation.require_ground_contact,
    )
    resolved_values: dict[str, JsonValue] = {
        "expected_height_cm.target": target_height_cm,
        "expected_height_cm.tolerance": _bounded_height_tolerance(target_height_cm),
        "orientation.require_ground_contact": require_ground_contact,
        "orientation.ground_tolerance_cm": _bounded_ground_tolerance(target_height_cm),
    }
    resolved_values.update(overrides)

    family_data = family.model_dump(mode="json")
    explicit_overrides = {
        path: value
        for path, value in resolved_values.items()
        if _get_path(family_data, path) != value
    }
    signature_payload = json.dumps(
        {
            "policy_family_id": family.profile_id,
            "explicit_overrides": explicit_overrides,
        },
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    signature = sha256(signature_payload).hexdigest()
    profile_data = family.model_dump(mode="python")
    for path, value in explicit_overrides.items():
        _set_path(profile_data, path, value)
    profile_data["profile_id"] = f"{family.profile_id}-resolved-{signature[:12]}"
    profile_data["name"] = f"Resolved Unreal static asset policy ({target_height_cm / 100:g} m)"
    try:
        profile = ProjectProfile.model_validate(profile_data)
    except ValidationError as error:
        first_error = error.errors(include_url=False)[0]
        location = ".".join(str(part) for part in first_error["loc"])
        raise ValueError(
            f"Resolved policy is invalid at {location}: {first_error['msg']}."
        ) from error

    sources: dict[str, PolicyRuleSource] = {
        "engine": "FAMILY_DEFAULT",
        "asset_type": "FAMILY_DEFAULT",
        "expected_height_cm.target": "CONFIRMED_INTENT",
        "expected_height_cm.tolerance": "DERIVED_INTENT",
        "orientation.require_y_up_geometry": "FAMILY_DEFAULT",
        "orientation.infer_vertical_from_dominant_extent": "FAMILY_DEFAULT",
        "orientation.require_ground_contact": (
            "DERIVED_INTENT"
            if _GROUNDED_LANGUAGE.search(description) or _AIRBORNE_LANGUAGE.search(description)
            else "FAMILY_DEFAULT"
        ),
        "orientation.ground_tolerance_cm": "DERIVED_INTENT",
        "naming.pattern": "FAMILY_DEFAULT",
        "naming.require_unique_node_names": "FAMILY_DEFAULT",
        "naming.require_unique_mesh_names": "FAMILY_DEFAULT",
        "budgets.max_triangles": "FAMILY_DEFAULT",
        "budgets.max_materials": "FAMILY_DEFAULT",
        "budgets.max_textures": "FAMILY_DEFAULT",
        "budgets.max_texture_dimension": "FAMILY_DEFAULT",
        "repair_policy.auto_rename": "FAMILY_DEFAULT",
        "repair_policy.require_approval_for_normalization_transform": "FAMILY_DEFAULT",
    }
    for path in overrides:
        sources[path] = "USER_OVERRIDE"

    profile_values = profile.model_dump(mode="json")
    rationales = {
        "engine": "The family targets Unreal static-asset import conventions.",
        "asset_type": (
            "The current deterministic repair domain remains static GLB meshes"
            if target_use is AssetTargetUse.STATIC_GAME_ASSET
            else "The requested character use narrows to the supported static-mesh handoff."
        ),
        "expected_height_cm.target": "This is the height already confirmed in the target story.",
        "expected_height_cm.tolerance": (
            "The resolver uses 5% of intended height, bounded to 1-10 cm."
        ),
        "orientation.require_y_up_geometry": "The Unreal policy family expects Y-up GLB geometry.",
        "orientation.infer_vertical_from_dominant_extent": (
            "Dominant-extent inference remains a fixed deterministic convention."
        ),
        "orientation.require_ground_contact": grounding_rationale,
        "orientation.ground_tolerance_cm": (
            "The resolver uses 0.5% of intended height, bounded to 0.1-1 cm."
        ),
        "naming.pattern": "The family permits deterministic Unreal-safe display names.",
        "naming.require_unique_node_names": "Safe node renaming requires unique display names.",
        "naming.require_unique_mesh_names": "Safe mesh renaming requires unique display names.",
        "budgets.max_triangles": (
            "No project-specific triangle budget was supplied; use the family default."
        ),
        "budgets.max_materials": (
            "No project-specific material budget was supplied; use the family default."
        ),
        "budgets.max_textures": (
            "No project-specific texture budget was supplied; use the family default."
        ),
        "budgets.max_texture_dimension": (
            "No project-specific texture limit was supplied; use the family default."
        ),
        "repair_policy.auto_rename": "Safe display-name repair remains fixed by the safety policy.",
        "repair_policy.require_approval_for_normalization_transform": (
            "Physical normalization always requires exact structured approval."
        ),
    }
    labels = {
        "engine": "Engine",
        "asset_type": "Asset type",
        "expected_height_cm.target": "Target height",
        "expected_height_cm.tolerance": "Height tolerance",
        "orientation.require_y_up_geometry": "Require Y-up geometry",
        "orientation.infer_vertical_from_dominant_extent": "Infer vertical from dominant extent",
        "orientation.require_ground_contact": "Require ground contact",
        "orientation.ground_tolerance_cm": "Ground tolerance",
        "naming.pattern": "Name pattern",
        "naming.require_unique_node_names": "Unique node names",
        "naming.require_unique_mesh_names": "Unique mesh names",
        "budgets.max_triangles": "Maximum triangles",
        "budgets.max_materials": "Maximum materials",
        "budgets.max_textures": "Maximum textures",
        "budgets.max_texture_dimension": "Maximum texture dimension",
        "repair_policy.auto_rename": "Automatic safe renaming",
        "repair_policy.require_approval_for_normalization_transform": (
            "Approval for physical normalization"
        ),
    }
    rules = tuple(
        ResolvedRule(
            path=path,
            label=label,
            value=_get_path(profile_values, path),
            source=sources[path],
            rationale=(
                "This supported value was explicitly adjusted by the user."
                if sources[path] == "USER_OVERRIDE"
                else rationales[path]
            ),
        )
        for path, label in labels.items()
    )
    provenance = build_profile_policy_provenance(
        profile,
        base_preset_id=family.profile_id,
        policy_family_id=family.profile_id,
        explicit_overrides=explicit_overrides,
        rule_sources=sources,
    )
    return PolicyResolution(
        family=family,
        profile=profile,
        provenance=provenance,
        display_name=f"Agent-resolved rules · {target_height_cm / 100:g} m target",
        rules=rules,
    )
