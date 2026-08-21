"""Strict version-1 records for the real-world validation corpus."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, JsonValue

from asset_shepherd.models import ActionClass, ContractModel

AssetId = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$")]
Sha256OrEmpty = Annotated[str, Field(pattern=r"^(?:[0-9a-f]{64})?$")]
NonNegativeMinutes = Annotated[float, Field(ge=0.0)]


class AssetProvenance(ContractModel):
    """Human-supplied generation facts plus immutable raw-file registration."""

    schema_version: Literal[1] = 1
    asset_id: AssetId
    display_name: str
    generator: Literal["Tripo"] = "Tripo"
    generation_date_utc: datetime | None
    prompt: str
    negative_prompt_or_constraints: str
    model_or_mode: str
    generation_settings: dict[str, JsonValue]
    selected_candidate_reason: str
    export_format: Literal["glb"] = "glb"
    export_settings: dict[str, JsonValue]
    raw_sha256: Sha256OrEmpty = ""
    public_use_confirmed: bool = False
    notes: str

    def registration_errors(self) -> tuple[str, ...]:
        """List missing human facts that must be resolved before raw registration."""
        errors: list[str] = []
        required_text = {
            "prompt": self.prompt,
            "model_or_mode": self.model_or_mode,
            "selected_candidate_reason": self.selected_candidate_reason,
        }
        errors.extend(name for name, value in required_text.items() if not value.strip())
        if self.generation_date_utc is None:
            errors.append("generation_date_utc")
        if not self.public_use_confirmed:
            errors.append("public_use_confirmed")
        return tuple(errors)


class MutationKind(StrEnum):
    """Controlled realistic mutation categories from the approved addendum."""

    SCALE_MISMATCH = "SCALE_MISMATCH"
    SIDEWAYS_ORIENTATION = "SIDEWAYS_ORIENTATION"
    FLOATING_GEOMETRY = "FLOATING_GEOMETRY"
    PIVOT_DISPLACEMENT = "PIVOT_DISPLACEMENT"
    NAME_CORRUPTION = "NAME_CORRUPTION"
    EMPTY_HIERARCHY = "EMPTY_HIERARCHY"
    MATERIAL_BLOAT = "MATERIAL_BLOAT"
    TEXTURE_BLOAT = "TEXTURE_BLOAT"
    NEGATIVE_SCALE = "NEGATIVE_SCALE"
    UNSUPPORTED_CONTENT = "UNSUPPORTED_CONTENT"


class MutationOperation(ContractModel):
    """One independently described mutation applied to a source copy."""

    kind: MutationKind
    description: str
    parameters: dict[str, JsonValue]
    affected_elements: tuple[str, ...]
    expected_finding_codes: tuple[str, ...]
    expected_action_classes: tuple[ActionClass, ...]


class MutationManifest(ContractModel):
    """Ground truth and preservation evidence for one realistic variant."""

    schema_version: Literal[1] = 1
    mutation_id: AssetId
    base_asset_id: AssetId
    source_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    variant_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    created_at: datetime
    tool_version: str
    operations: tuple[MutationOperation, ...]
    expected_post_repair_invariants: tuple[str, ...]
    source_unchanged_verified: bool
    variant_parse_verified: bool
    geometry_preserved: bool
    materials_preserved: bool
    textures_preserved: bool


class FindingClassification(StrEnum):
    """Allowed human adjudication outcomes for one product finding."""

    TRUE_POSITIVE = "TRUE_POSITIVE"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    USEFUL_WARNING = "USEFUL_WARNING"
    CORRECTLY_BLOCKED = "CORRECTLY_BLOCKED"
    INCORRECT_ACTION_CLASS = "INCORRECT_ACTION_CLASS"
    NOT_ADJUDICATED = "NOT_ADJUDICATED"


class FindingAdjudication(ContractModel):
    """Human classification of one frozen blind finding."""

    finding_code: str
    classification: FindingClassification
    human_notes: str
    downstream_evidence: tuple[str, ...]


class Adjudication(ContractModel):
    """Real-world findings, misses, safety results, and manual-effort evidence."""

    schema_version: Literal[1] = 1
    asset_id: AssetId
    product_version: str
    findings: tuple[FindingAdjudication, ...]
    missed_required_repairs: tuple[str, ...]
    false_severe_findings: tuple[str, ...]
    unsafe_automatic_repairs: tuple[str, ...]
    correctly_blocked_cases: tuple[str, ...]
    raw_unreal_result: str
    shepherd_unreal_result: str
    human_reference_unreal_result: str
    manual_minutes_raw_to_usable: NonNegativeMinutes | None
    manual_minutes_after_shepherd: NonNegativeMinutes | None
    visual_fidelity_assessment: str
    demo_candidate: bool
