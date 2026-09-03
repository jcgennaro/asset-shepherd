"""Typed minimum-information contract for conversational target intake."""

from __future__ import annotations

import math
import re
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from asset_shepherd.intent import normalize_intent_description, target_height_cm_from_meters
from asset_shepherd.models import AssetEndpoint, AssetTargetUse, AssetViewingUse, ContractModel

TargetField = Literal[
    "target_use",
    "endpoint",
    "target_dimensions_cm",
    "target_height_cm",
    "viewing_use",
]
MINIMUM_TARGET_FIELDS: tuple[TargetField, ...] = (
    "target_use",
    "endpoint",
    "target_dimensions_cm",
    "viewing_use",
)
MINIMUM_TARGET_CONFIDENCE = 0.8


class TargetEvidenceSource(StrEnum):
    """Auditable source of one proposed target field."""

    EXPLICIT_USER_TEXT = "EXPLICIT_USER_TEXT"
    MODEL_INFERENCE = "MODEL_INFERENCE"
    USER_CLARIFICATION = "USER_CLARIFICATION"
    DETERMINISTIC_FALLBACK = "DETERMINISTIC_FALLBACK"


class TargetFieldEvidence(ContractModel):
    """Concise evidence supporting one populated target field."""

    field: TargetField
    source: TargetEvidenceSource
    confidence: Annotated[float, Field(ge=MINIMUM_TARGET_CONFIDENCE, le=1.0)]
    evidence: Annotated[str, Field(min_length=1, max_length=160)]


class TargetIntakeContract(ContractModel):
    """Minimum typed state required before Asset Shepherd may offer target confirmation."""

    schema_version: Literal[1, 2, 3, 4, 5, 6] = 4
    description: Annotated[str, Field(min_length=12, max_length=600)]
    asset_name: Annotated[str, Field(min_length=2, max_length=48)] = "Untitled asset"
    analyzer_provider: Annotated[str, Field(min_length=1, max_length=40)] = "deterministic"
    analyzer_model: Annotated[str, Field(min_length=1, max_length=120)] = "explicit-text-v1"
    target_use: AssetTargetUse | None = None
    target_height_cm: Annotated[float, Field(gt=0.0, le=100000.0)] | None = None
    endpoint: AssetEndpoint | None = None
    endpoint_detail: Annotated[str, Field(min_length=2, max_length=80)] | None = None
    viewing_use: AssetViewingUse | None = None
    target_dimensions_cm: (
        tuple[
            Annotated[float, Field(gt=0.0, le=100000.0)],
            Annotated[float, Field(gt=0.0, le=100000.0)],
            Annotated[float, Field(gt=0.0, le=100000.0)],
        ]
        | None
    ) = None
    expected_piece_count: Annotated[int, Field(ge=1, le=64)] = 1
    expected_piece_count_evidence: Annotated[str, Field(min_length=1, max_length=160)] = (
        "A single asset is normally expected as one semantic piece."
    )
    evidence: tuple[TargetFieldEvidence, ...] = ()
    missing_fields: tuple[TargetField, ...]

    @model_validator(mode="after")
    def fields_and_evidence_are_consistent(self) -> TargetIntakeContract:
        """Require missing fields and evidence to describe the exact populated state."""
        expected_missing_values: list[TargetField] = []
        required_fields: tuple[TargetField, ...]
        if self.schema_version >= 6:
            required_fields = MINIMUM_TARGET_FIELDS
        elif self.schema_version >= 5:
            required_fields = ("target_use", "endpoint", "target_dimensions_cm")
        else:
            required_fields = ("target_use", "target_height_cm")
        for field_name in required_fields:
            if getattr(self, field_name) is None:
                expected_missing_values.append(field_name)
        expected_missing = tuple(expected_missing_values)
        if self.missing_fields != expected_missing:
            raise ValueError("missing_fields must exactly match the unpopulated required fields")
        cited_fields = tuple(item.field for item in self.evidence)
        if len(cited_fields) != len(set(cited_fields)):
            raise ValueError("Each populated target field may have only one evidence record")
        populated_fields = set(required_fields) - set(expected_missing)
        if set(cited_fields) != populated_fields:
            raise ValueError("Every populated target field requires one evidence record")
        if self.target_dimensions_cm is not None:
            if self.target_height_cm is None or not math.isclose(
                self.target_height_cm,
                self.target_dimensions_cm[1],
                rel_tol=0.0,
                abs_tol=1e-6,
            ):
                raise ValueError("target_height_cm must equal the Y target bound")
        if self.endpoint is AssetEndpoint.OTHER and self.endpoint_detail is None:
            raise ValueError("Other endpoint requires a short description")
        if self.endpoint is not None and self.endpoint is not AssetEndpoint.OTHER:
            if self.endpoint_detail is not None:
                raise ValueError("Canonical endpoints do not accept endpoint_detail")
        return self

    @property
    def ready_for_confirmation(self) -> bool:
        """Return whether the minimum contract is complete."""
        return not self.missing_fields


_USE_PATTERNS: dict[AssetTargetUse, tuple[re.Pattern[str], ...]] = {
    AssetTargetUse.PLAYABLE_CHARACTER: (
        re.compile(r"\bplayable(?:\s+(?:animated\s+)?character)?\b", re.IGNORECASE),
        re.compile(r"\bplayer[- ]character\b", re.IGNORECASE),
        re.compile(r"\bprotagonist\b", re.IGNORECASE),
    ),
    AssetTargetUse.RIG_READY_CHARACTER: (
        re.compile(r"\brig[- ]ready\b", re.IGNORECASE),
        re.compile(r"\bready (?:to|for) rig(?:ging)?\b", re.IGNORECASE),
        re.compile(r"\bfor rigging\b", re.IGNORECASE),
    ),
    AssetTargetUse.STATIC_GAME_ASSET: (
        re.compile(
            r"\bstatic(?:\s+(?:game\s+)?asset|\s+mesh|\s+statue)\b",
            re.IGNORECASE,
        ),
        re.compile(r"\b(?:environment|scene|game) prop\b", re.IGNORECASE),
        re.compile(r"\bset dressing\b", re.IGNORECASE),
        re.compile(r"\bdecorative prop\b", re.IGNORECASE),
    ),
}

_HEIGHT_PATTERN = re.compile(
    r"(?<![\w.])(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>met(?:er|re)s?|m|centimet(?:er|re)s?|cm|feet|foot|ft|inches|inch|in)\b",
    re.IGNORECASE,
)

_DIMENSIONS_PATTERN = re.compile(
    r"(?<![\w.])(?P<x>\d+(?:\.\d+)?)\s*[x\u00d7]\s*"
    r"(?P<y>\d+(?:\.\d+)?)\s*[x\u00d7]\s*(?P<z>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>met(?:er|re)s?|m|centimet(?:er|re)s?|cm|feet|foot|ft|inches|inch|in)\b",
    re.IGNORECASE,
)

_ENDPOINT_PATTERNS: dict[AssetEndpoint, re.Pattern[str]] = {
    AssetEndpoint.UNITY: re.compile(r"\bunity\b", re.IGNORECASE),
    AssetEndpoint.UNREAL: re.compile(r"\bunreal(?: engine)?\b", re.IGNORECASE),
    AssetEndpoint.GODOT: re.compile(r"\bgodot\b", re.IGNORECASE),
}

_NAME_PREFIX = re.compile(
    r"^(?:(?:i(?:'m| am) (?:making|working on|creating)|this is)\s+)?(?:a|an|the)\s+",
    re.IGNORECASE,
)
_NAME_STOP = re.compile(
    r"\b(?:used|intended|designed|made)\s+(?:as|for|to)\b|\b(?:for|with|that|which)\b",
    re.IGNORECASE,
)


def fallback_asset_name(description: str) -> str:
    """Derive a short deterministic gallery label when no semantic model is available."""
    normalized = normalize_intent_description(description)
    without_measurements = _HEIGHT_PATTERN.sub("", normalized)
    candidate = _NAME_PREFIX.sub("", without_measurements).strip(" ,.-")
    candidate = _NAME_STOP.split(candidate, maxsplit=1)[0].strip(" ,.-")
    words = re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", candidate)
    if not words:
        return "Untitled asset"
    useful = words[:5]
    if len(useful) == 1 and useful[0].isdigit():
        return "Untitled asset"
    return " ".join(useful).title()[:48].strip()


def _extract_target_use(
    description: str,
) -> tuple[AssetTargetUse | None, TargetFieldEvidence | None]:
    matches: list[tuple[AssetTargetUse, str]] = []
    for target_use, patterns in _USE_PATTERNS.items():
        for pattern in patterns:
            if match := pattern.search(description):
                matches.append((target_use, match.group(0)))
                break
    distinct = {target_use for target_use, _ in matches}
    if len(distinct) != 1:
        return None, None
    target_use, matched_text = matches[0]
    return target_use, TargetFieldEvidence(
        field="target_use",
        source=TargetEvidenceSource.EXPLICIT_USER_TEXT,
        confidence=1.0,
        evidence=f'Explicit phrase: "{matched_text}"',
    )


def _height_to_cm(value: float, unit: str) -> float:
    normalized = unit.casefold()
    if normalized in {"m", "meter", "meters", "metre", "metres"}:
        return value * 100.0
    if normalized in {"cm", "centimeter", "centimeters", "centimetre", "centimetres"}:
        return value
    if normalized in {"feet", "foot", "ft"}:
        return value * 30.48
    return value * 2.54


def _extract_target_height(description: str) -> tuple[float | None, TargetFieldEvidence | None]:
    matches: list[tuple[float, str]] = []
    for match in _HEIGHT_PATTERN.finditer(description):
        value = float(match.group("value"))
        height_cm = _height_to_cm(value, match.group("unit"))
        if math.isfinite(height_cm) and 0.0 < height_cm <= 100000.0:
            matches.append((round(height_cm, 6), match.group(0)))
    distinct = {height_cm for height_cm, _ in matches}
    if len(distinct) != 1:
        return None, None
    height_cm, matched_text = matches[0]
    return height_cm, TargetFieldEvidence(
        field="target_height_cm",
        source=TargetEvidenceSource.EXPLICIT_USER_TEXT,
        confidence=1.0,
        evidence=f'Explicit measurement: "{matched_text}"',
    )


def _extract_dimensions(
    description: str,
) -> tuple[tuple[float, float, float] | None, TargetFieldEvidence | None]:
    """Extract one explicit X/Y/Z target box from ordinary text."""
    matches: list[tuple[tuple[float, float, float], str]] = []
    for match in _DIMENSIONS_PATTERN.finditer(description):
        unit = match.group("unit")
        dimensions = (
            round(_height_to_cm(float(match.group("x")), unit), 6),
            round(_height_to_cm(float(match.group("y")), unit), 6),
            round(_height_to_cm(float(match.group("z")), unit), 6),
        )
        if all(math.isfinite(value) and 0.0 < value <= 100000.0 for value in dimensions):
            matches.append((dimensions, match.group(0)))
    distinct = {dimensions for dimensions, _ in matches}
    if len(distinct) != 1:
        return None, None
    dimensions, matched_text = matches[0]
    return dimensions, TargetFieldEvidence(
        field="target_dimensions_cm",
        source=TargetEvidenceSource.EXPLICIT_USER_TEXT,
        confidence=1.0,
        evidence=f'Explicit X/Y/Z bounds: "{matched_text}"',
    )


def _extract_endpoint(
    description: str,
) -> tuple[AssetEndpoint | None, TargetFieldEvidence | None]:
    matches = [
        endpoint for endpoint, pattern in _ENDPOINT_PATTERNS.items() if pattern.search(description)
    ]
    if len(matches) != 1:
        return None, None
    endpoint = matches[0]
    return endpoint, TargetFieldEvidence(
        field="endpoint",
        source=TargetEvidenceSource.EXPLICIT_USER_TEXT,
        confidence=1.0,
        evidence=f"Explicit destination: {endpoint.value.title()}",
    )


def draft_target_intake(description: str) -> TargetIntakeContract:
    """Extract only explicit required target fields from one normalized description."""
    normalized = normalize_intent_description(description)
    target_use, use_evidence = _extract_target_use(normalized)
    endpoint, endpoint_evidence = _extract_endpoint(normalized)
    if endpoint is None:
        endpoint = AssetEndpoint.OTHER
        endpoint_evidence = TargetFieldEvidence(
            field="endpoint",
            source=TargetEvidenceSource.DETERMINISTIC_FALLBACK,
            confidence=MINIMUM_TARGET_CONFIDENCE,
            evidence="Offline fallback; no named next tool was available.",
        )
    target_dimensions_cm, dimensions_evidence = _extract_dimensions(normalized)
    target_height_cm = target_dimensions_cm[1] if target_dimensions_cm is not None else None
    if target_dimensions_cm is None:
        target_height_cm, _ = _extract_target_height(normalized)
        if target_height_cm is not None:
            target_dimensions_cm = (target_height_cm, target_height_cm, target_height_cm)
            dimensions_evidence = TargetFieldEvidence(
                field="target_dimensions_cm",
                source=TargetEvidenceSource.DETERMINISTIC_FALLBACK,
                confidence=MINIMUM_TARGET_CONFIDENCE,
                evidence="Offline fallback expanded the explicit size anchor to X/Y/Z.",
            )
    evidence = (
        *(
            item
            for item in (use_evidence, endpoint_evidence, dimensions_evidence)
            if item is not None
        ),
        TargetFieldEvidence(
            field="viewing_use",
            source=TargetEvidenceSource.DETERMINISTIC_FALLBACK,
            confidence=MINIMUM_TARGET_CONFIDENCE,
            evidence="Normal gameplay is preselected for explicit target-stage confirmation.",
        ),
    )
    missing_values: list[TargetField] = []
    if target_use is None:
        missing_values.append("target_use")
    if target_dimensions_cm is None:
        missing_values.append("target_dimensions_cm")
    return TargetIntakeContract(
        schema_version=6,
        description=normalized,
        asset_name=fallback_asset_name(normalized),
        analyzer_provider="deterministic",
        analyzer_model="explicit-text-v1",
        target_use=target_use,
        target_height_cm=target_height_cm,
        endpoint=endpoint,
        endpoint_detail="Unspecified endpoint" if endpoint is AssetEndpoint.OTHER else None,
        viewing_use=AssetViewingUse.NORMAL_GAMEPLAY,
        target_dimensions_cm=target_dimensions_cm,
        expected_piece_count=1,
        expected_piece_count_evidence=(
            "The description does not clearly identify a multi-piece set or pair."
        ),
        evidence=evidence,
        missing_fields=tuple(missing_values),
    )


def clarify_target_intake(
    draft: TargetIntakeContract,
    *,
    target_use_value: str | None = None,
    endpoint_value: str | None = None,
    endpoint_detail: str | None = None,
    viewing_use_value: str | None = None,
    target_x_m: str | None = None,
    target_y_m: str | None = None,
    target_z_m: str | None = None,
    target_height_m: str | None = None,
) -> TargetIntakeContract:
    """Fill missing fields and retain an explicit viewing-use choice made beside them."""
    if draft.ready_for_confirmation:
        raise ValueError("The target proposal is already complete.")
    target_use = draft.target_use
    target_height_cm = draft.target_height_cm
    endpoint = draft.endpoint
    resolved_endpoint_detail = draft.endpoint_detail
    target_dimensions_cm = draft.target_dimensions_cm
    viewing_use = draft.viewing_use
    evidence = list(draft.evidence)
    if target_use is None:
        if target_use_value is None:
            raise ValueError("Choose what the asset should become.")
        try:
            target_use = AssetTargetUse(target_use_value)
        except ValueError as error:
            raise ValueError("Choose what the asset should become.") from error
        evidence.append(
            TargetFieldEvidence(
                field="target_use",
                source=TargetEvidenceSource.USER_CLARIFICATION,
                confidence=1.0,
                evidence="Explicit structured clarification",
            )
        )
    if endpoint is None:
        if endpoint_value is None:
            raise ValueError("Choose where the asset will be used next.")
        try:
            endpoint = AssetEndpoint(endpoint_value)
        except ValueError as error:
            raise ValueError("Choose Unity, Unreal, Godot, or Other.") from error
        resolved_endpoint_detail = endpoint_detail.strip() if endpoint_detail else None
        if endpoint is AssetEndpoint.OTHER and not resolved_endpoint_detail:
            raise ValueError("Name the other tool or destination.")
        evidence.append(
            TargetFieldEvidence(
                field="endpoint",
                source=TargetEvidenceSource.USER_CLARIFICATION,
                confidence=1.0,
                evidence="Explicit structured clarification",
            )
        )
    if target_dimensions_cm is None:
        if target_x_m is not None and target_y_m is not None and target_z_m is not None:
            target_dimensions_cm = (
                target_height_cm_from_meters(target_x_m),
                target_height_cm_from_meters(target_y_m),
                target_height_cm_from_meters(target_z_m),
            )
        elif target_height_m is not None:
            legacy_height_cm = target_height_cm_from_meters(target_height_m)
            target_dimensions_cm = (legacy_height_cm, legacy_height_cm, legacy_height_cm)
        else:
            raise ValueError("Provide approximate X, Y, and Z target dimensions.")
        target_height_cm = target_dimensions_cm[1]
        evidence.append(
            TargetFieldEvidence(
                field="target_dimensions_cm",
                source=TargetEvidenceSource.USER_CLARIFICATION,
                confidence=1.0,
                evidence="Explicit structured clarification",
            )
        )
    if viewing_use_value is not None:
        try:
            viewing_use = AssetViewingUse(viewing_use_value)
        except ValueError as error:
            raise ValueError("Choose one of the three asset viewing uses.") from error
        evidence = [item for item in evidence if item.field != "viewing_use"]
        evidence.append(
            TargetFieldEvidence(
                field="viewing_use",
                source=TargetEvidenceSource.USER_CLARIFICATION,
                confidence=1.0,
                evidence="Explicit structured use-case choice",
            )
        )
    elif viewing_use is None:
        raise ValueError("Choose how closely the asset will normally be viewed.")
    return TargetIntakeContract(
        schema_version=6,
        description=draft.description,
        asset_name=draft.asset_name,
        analyzer_provider=draft.analyzer_provider,
        analyzer_model=draft.analyzer_model,
        target_use=target_use,
        target_height_cm=target_height_cm,
        endpoint=endpoint,
        endpoint_detail=resolved_endpoint_detail,
        viewing_use=viewing_use,
        target_dimensions_cm=target_dimensions_cm,
        expected_piece_count=draft.expected_piece_count,
        expected_piece_count_evidence=draft.expected_piece_count_evidence,
        evidence=tuple(evidence),
        missing_fields=(),
    )


def confirm_target_viewing_use(
    draft: TargetIntakeContract,
    viewing_use_value: str | None,
) -> TargetIntakeContract:
    """Record the explicit use-case choice made on the target confirmation card."""
    if viewing_use_value is None:
        viewing_use = draft.viewing_use or AssetViewingUse.NORMAL_GAMEPLAY
    else:
        try:
            viewing_use = AssetViewingUse(viewing_use_value)
        except ValueError as error:
            raise ValueError("Choose one of the three asset viewing uses.") from error
    evidence = (
        *(item for item in draft.evidence if item.field != "viewing_use"),
        TargetFieldEvidence(
            field="viewing_use",
            source=TargetEvidenceSource.USER_CLARIFICATION,
            confidence=1.0,
            evidence="Explicit use-case choice at target confirmation",
        ),
    )
    return draft.model_copy(
        update={
            "schema_version": 6,
            "viewing_use": viewing_use,
            "evidence": evidence,
        }
    )


def revise_target_intake(
    draft: TargetIntakeContract,
    *,
    target_use_value: str,
    endpoint_value: str = AssetEndpoint.OTHER.value,
    endpoint_detail: str | None = None,
    viewing_use_value: str = AssetViewingUse.NORMAL_GAMEPLAY.value,
    target_x_m: str | None = None,
    target_y_m: str | None = None,
    target_z_m: str | None = None,
    target_height_m: str | None = None,
) -> TargetIntakeContract:
    """Replace an unconfirmed proposal with two explicit user-supplied target values."""
    try:
        target_use = AssetTargetUse(target_use_value)
    except ValueError as error:
        raise ValueError("Choose what the asset should become.") from error
    try:
        endpoint = AssetEndpoint(endpoint_value)
    except ValueError as error:
        raise ValueError("Choose Unity, Unreal, Godot, or Other.") from error
    resolved_endpoint_detail = endpoint_detail.strip() if endpoint_detail else None
    if endpoint is AssetEndpoint.OTHER and resolved_endpoint_detail is None:
        resolved_endpoint_detail = "Unspecified endpoint"
    try:
        viewing_use = AssetViewingUse(viewing_use_value)
    except ValueError as error:
        raise ValueError("Choose one of the three asset viewing uses.") from error
    if target_x_m is not None and target_y_m is not None and target_z_m is not None:
        target_dimensions_cm = (
            target_height_cm_from_meters(target_x_m),
            target_height_cm_from_meters(target_y_m),
            target_height_cm_from_meters(target_z_m),
        )
    elif target_height_m is not None:
        legacy_height_cm = target_height_cm_from_meters(target_height_m)
        target_dimensions_cm = (legacy_height_cm, legacy_height_cm, legacy_height_cm)
    else:
        raise ValueError("Provide approximate X, Y, and Z target dimensions.")
    target_height_cm = target_dimensions_cm[1]
    evidence = (
        TargetFieldEvidence(
            field="target_use",
            source=TargetEvidenceSource.USER_CLARIFICATION,
            confidence=1.0,
            evidence="Explicit target adjustment",
        ),
        TargetFieldEvidence(
            field="endpoint",
            source=TargetEvidenceSource.USER_CLARIFICATION,
            confidence=1.0,
            evidence="Explicit target adjustment",
        ),
        TargetFieldEvidence(
            field="target_dimensions_cm",
            source=TargetEvidenceSource.USER_CLARIFICATION,
            confidence=1.0,
            evidence="Explicit target adjustment",
        ),
        TargetFieldEvidence(
            field="viewing_use",
            source=TargetEvidenceSource.USER_CLARIFICATION,
            confidence=1.0,
            evidence="Explicit use-case adjustment",
        ),
    )
    return TargetIntakeContract(
        schema_version=6,
        description=draft.description,
        asset_name=draft.asset_name,
        analyzer_provider=draft.analyzer_provider,
        analyzer_model=draft.analyzer_model,
        target_use=target_use,
        target_height_cm=target_height_cm,
        endpoint=endpoint,
        endpoint_detail=resolved_endpoint_detail,
        viewing_use=viewing_use,
        target_dimensions_cm=target_dimensions_cm,
        expected_piece_count=draft.expected_piece_count,
        expected_piece_count_evidence=draft.expected_piece_count_evidence,
        evidence=evidence,
        missing_fields=(),
    )
