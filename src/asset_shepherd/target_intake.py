"""Typed minimum-information contract for conversational target intake."""

from __future__ import annotations

import math
import re
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from asset_shepherd.intent import normalize_intent_description, target_height_cm_from_meters
from asset_shepherd.models import AssetTargetUse, ContractModel

TargetField = Literal["target_use", "target_height_cm"]
MINIMUM_TARGET_FIELDS: tuple[TargetField, ...] = ("target_use", "target_height_cm")
MINIMUM_TARGET_CONFIDENCE = 0.8


class TargetEvidenceSource(StrEnum):
    """Auditable source of one proposed target field."""

    EXPLICIT_USER_TEXT = "EXPLICIT_USER_TEXT"
    MODEL_INFERENCE = "MODEL_INFERENCE"
    USER_CLARIFICATION = "USER_CLARIFICATION"


class TargetFieldEvidence(ContractModel):
    """Concise evidence supporting one populated target field."""

    field: TargetField
    source: TargetEvidenceSource
    confidence: Annotated[float, Field(ge=MINIMUM_TARGET_CONFIDENCE, le=1.0)]
    evidence: Annotated[str, Field(min_length=1, max_length=160)]


class TargetIntakeContract(ContractModel):
    """Minimum typed state required before Asset Shepherd may offer target confirmation."""

    schema_version: Literal[1, 2, 3] = 3
    description: Annotated[str, Field(min_length=12, max_length=600)]
    asset_name: Annotated[str, Field(min_length=2, max_length=48)] = "Untitled asset"
    analyzer_provider: Annotated[str, Field(min_length=1, max_length=40)] = "deterministic"
    analyzer_model: Annotated[str, Field(min_length=1, max_length=120)] = "explicit-text-v1"
    target_use: AssetTargetUse | None = None
    target_height_cm: Annotated[float, Field(gt=0.0, le=100000.0)] | None = None
    evidence: tuple[TargetFieldEvidence, ...] = ()
    missing_fields: tuple[TargetField, ...]

    @model_validator(mode="after")
    def fields_and_evidence_are_consistent(self) -> TargetIntakeContract:
        """Require missing fields and evidence to describe the exact populated state."""
        expected_missing_values: list[TargetField] = []
        if self.target_use is None:
            expected_missing_values.append("target_use")
        if self.target_height_cm is None:
            expected_missing_values.append("target_height_cm")
        expected_missing = tuple(expected_missing_values)
        if self.missing_fields != expected_missing:
            raise ValueError("missing_fields must exactly match the unpopulated required fields")
        cited_fields = tuple(item.field for item in self.evidence)
        if len(cited_fields) != len(set(cited_fields)):
            raise ValueError("Each populated target field may have only one evidence record")
        populated_fields = set(MINIMUM_TARGET_FIELDS) - set(expected_missing)
        if set(cited_fields) != populated_fields:
            raise ValueError("Every populated target field requires one evidence record")
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


def draft_target_intake(description: str) -> TargetIntakeContract:
    """Extract only explicit required target fields from one normalized description."""
    normalized = normalize_intent_description(description)
    target_use, use_evidence = _extract_target_use(normalized)
    target_height_cm, height_evidence = _extract_target_height(normalized)
    evidence = tuple(item for item in (use_evidence, height_evidence) if item is not None)
    missing_values: list[TargetField] = []
    if target_use is None:
        missing_values.append("target_use")
    if target_height_cm is None:
        missing_values.append("target_height_cm")
    return TargetIntakeContract(
        description=normalized,
        asset_name=fallback_asset_name(normalized),
        analyzer_provider="deterministic",
        analyzer_model="explicit-text-v1",
        target_use=target_use,
        target_height_cm=target_height_cm,
        evidence=evidence,
        missing_fields=tuple(missing_values),
    )


def clarify_target_intake(
    draft: TargetIntakeContract,
    *,
    target_use_value: str | None = None,
    target_height_m: str | None = None,
) -> TargetIntakeContract:
    """Fill only missing required fields from explicit structured clarification answers."""
    if draft.ready_for_confirmation:
        raise ValueError("The target proposal is already complete.")
    target_use = draft.target_use
    target_height_cm = draft.target_height_cm
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
    if target_height_cm is None:
        if target_height_m is None:
            raise ValueError("Provide the intended real-world height.")
        target_height_cm = target_height_cm_from_meters(target_height_m)
        evidence.append(
            TargetFieldEvidence(
                field="target_height_cm",
                source=TargetEvidenceSource.USER_CLARIFICATION,
                confidence=1.0,
                evidence="Explicit structured clarification",
            )
        )
    return TargetIntakeContract(
        description=draft.description,
        asset_name=draft.asset_name,
        analyzer_provider=draft.analyzer_provider,
        analyzer_model=draft.analyzer_model,
        target_use=target_use,
        target_height_cm=target_height_cm,
        evidence=tuple(evidence),
        missing_fields=(),
    )


def revise_target_intake(
    draft: TargetIntakeContract,
    *,
    target_use_value: str,
    target_height_m: str,
) -> TargetIntakeContract:
    """Replace an unconfirmed proposal with two explicit user-supplied target values."""
    try:
        target_use = AssetTargetUse(target_use_value)
    except ValueError as error:
        raise ValueError("Choose what the asset should become.") from error
    target_height_cm = target_height_cm_from_meters(target_height_m)
    evidence = (
        TargetFieldEvidence(
            field="target_use",
            source=TargetEvidenceSource.USER_CLARIFICATION,
            confidence=1.0,
            evidence="Explicit target adjustment",
        ),
        TargetFieldEvidence(
            field="target_height_cm",
            source=TargetEvidenceSource.USER_CLARIFICATION,
            confidence=1.0,
            evidence="Explicit target adjustment",
        ),
    )
    return TargetIntakeContract(
        description=draft.description,
        asset_name=draft.asset_name,
        analyzer_provider=draft.analyzer_provider,
        analyzer_model=draft.analyzer_model,
        target_use=target_use,
        target_height_cm=target_height_cm,
        evidence=evidence,
        missing_fields=(),
    )
