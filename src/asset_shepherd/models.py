"""Versioned JSON models shared by the deterministic core and agent boundary."""

from datetime import datetime
from enum import StrEnum
from re import compile as compile_pattern
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

NonNegativeInt = Annotated[int, Field(ge=0)]
PositiveInt = Annotated[int, Field(gt=0)]
UnitConfidence = Annotated[float, Field(ge=0.0, le=1.0)]
Vector3 = tuple[float, float, float]
Matrix4 = tuple[
    tuple[float, float, float, float],
    tuple[float, float, float, float],
    tuple[float, float, float, float],
    tuple[float, float, float, float],
]


class ContractModel(BaseModel):
    """Base for strict, closed contract models."""

    model_config = ConfigDict(extra="forbid", strict=True, validate_default=True)


class Severity(StrEnum):
    """Finding severity independent of repairability."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    BLOCKER = "BLOCKER"


class ActionClass(StrEnum):
    """Authorization class for a finding or candidate repair."""

    REPORT_ONLY = "REPORT_ONLY"
    AUTO_SAFE = "AUTO_SAFE"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    BLOCKED = "BLOCKED"


class RepairEligibility(StrEnum):
    """Whether inspection may proceed to structural repair."""

    ELIGIBLE_STATIC_MESH = "ELIGIBLE_STATIC_MESH"
    INSPECTION_ONLY_UNSUPPORTED_FEATURES = "INSPECTION_ONLY_UNSUPPORTED_FEATURES"
    INVALID_OR_UNREADABLE = "INVALID_OR_UNREADABLE"


class RepairKind(StrEnum):
    """Registered version-1 repair operations."""

    RENAME_NODE = "RENAME_NODE"
    RENAME_MESH = "RENAME_MESH"
    NORMALIZATION_TRANSFORM = "NORMALIZATION_TRANSFORM"


class DecisionValue(StrEnum):
    """Recorded authorization outcome."""

    AUTO_AUTHORIZED = "AUTO_AUTHORIZED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class DecisionSource(StrEnum):
    """Source of a repair authorization."""

    POLICY = "POLICY"
    USER_APPROVAL_FILE = "USER_APPROVAL_FILE"
    USER_INTERACTIVE = "USER_INTERACTIVE"


class CheckStatus(StrEnum):
    """Deterministic verification-check state."""

    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


class VerificationState(StrEnum):
    """Contracted final verification state."""

    PASSED_PROJECT_READY = "PASSED_PROJECT_READY"
    PASSED_WITH_REMAINING_WARNINGS = "PASSED_WITH_REMAINING_WARNINGS"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class JobState(StrEnum):
    """Top-level deterministic job state."""

    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


class ExpectedHeight(ContractModel):
    """Target physical height in the user-facing centimeter unit."""

    target: Annotated[float, Field(gt=0.0)]
    tolerance: Annotated[float, Field(ge=0.0)]


class OrientationPolicy(ContractModel):
    """Project rules for orientation and ground contact."""

    require_y_up_geometry: bool
    infer_vertical_from_dominant_extent: bool
    require_ground_contact: bool
    ground_tolerance_cm: Annotated[float, Field(ge=0.0)]


class NamingPolicy(ContractModel):
    """Project naming rules."""

    pattern: str
    require_unique_node_names: bool
    require_unique_mesh_names: bool

    @field_validator("pattern")
    @classmethod
    def pattern_must_compile(cls, value: str) -> str:
        """Reject invalid regular expressions when loading a profile."""
        compile_pattern(value)
        return value


class BudgetPolicy(ContractModel):
    """Static asset resource budgets."""

    max_triangles: NonNegativeInt
    max_materials: NonNegativeInt
    max_textures: NonNegativeInt
    max_texture_dimension: PositiveInt


class RepairPolicy(ContractModel):
    """Project authorization policy for version-1 repairs."""

    auto_rename: bool
    require_approval_for_normalization_transform: bool


class ProjectProfile(ContractModel):
    """Versioned target-project conventions."""

    profile_version: Literal[1] = 1
    profile_id: str
    name: str
    engine: str
    asset_type: Literal["static_mesh"]
    expected_height_cm: ExpectedHeight
    orientation: OrientationPolicy
    naming: NamingPolicy
    budgets: BudgetPolicy
    repair_policy: RepairPolicy


class Bounds3D(ContractModel):
    """World-space bounds represented in meters and centimeters."""

    minimum_m: Vector3
    maximum_m: Vector3
    dimensions_m: Vector3
    minimum_cm: Vector3
    maximum_cm: Vector3
    dimensions_cm: Vector3


class PackageFacts(ContractModel):
    """Container and glTF structure facts."""

    file_sha256: str
    byte_size: NonNegativeInt
    asset_version: str | None
    generator: str | None
    parse_success: bool
    scene_count: NonNegativeInt
    active_scene: int | None
    node_count: NonNegativeInt
    mesh_count: NonNegativeInt
    primitive_count: NonNegativeInt
    material_count: NonNegativeInt
    texture_count: NonNegativeInt
    image_count: NonNegativeInt
    skin_count: NonNegativeInt
    animation_count: NonNegativeInt
    camera_count: NonNegativeInt
    extensions_used: tuple[str, ...]
    extensions_required: tuple[str, ...]
    has_morph_targets: bool


class GeometryFacts(ContractModel):
    """Measured world-space geometry facts."""

    vertex_count: NonNegativeInt
    triangle_count: NonNegativeInt
    bounds: Bounds3D
    dominant_dimension_axis: Literal["X", "Y", "Z"]
    ground_relationship: Literal["INTERSECTS", "GROUNDED", "FLOATS_ABOVE", "EXTENDS_BELOW"]


class NodeTransformFact(ContractModel):
    """A node with a non-identity transform."""

    node_index: NonNegativeInt
    node_name: str | None
    translation: Vector3
    rotation: tuple[float, float, float, float]
    scale: Vector3
    determinant: float
    non_uniform_scale: bool
    negative_determinant: bool


class NodeHierarchyFact(ContractModel):
    """One node's parent-child relationship."""

    node_index: NonNegativeInt
    parent_index: int | None
    child_indices: tuple[int, ...]


class TransformFacts(ContractModel):
    """Scene hierarchy and transform facts."""

    root_nodes: tuple[int, ...]
    non_identity_transforms: tuple[NodeTransformFact, ...]
    negative_determinant_nodes: tuple[int, ...]
    non_uniform_scale_nodes: tuple[int, ...]
    hierarchy: tuple[NodeHierarchyFact, ...]


class NamingFacts(ContractModel):
    """Measured naming defects and deterministic proposed replacements."""

    missing_node_indices: tuple[int, ...]
    invalid_node_indices: tuple[int, ...]
    duplicate_node_names: dict[str, tuple[int, ...]]
    missing_mesh_indices: tuple[int, ...]
    invalid_mesh_indices: tuple[int, ...]
    duplicate_mesh_names: dict[str, tuple[int, ...]]
    proposed_replacements: dict[str, str]


class TextureFact(ContractModel):
    """Readable metadata for one embedded image resource."""

    image_index: NonNegativeInt
    name: str | None
    mime_type: str | None
    width: int | None
    height: int | None
    readable: bool
    detail: str | None


class ResourceFacts(ContractModel):
    """Material and texture inspection facts."""

    material_count: NonNegativeInt
    texture_count: NonNegativeInt
    image_count: NonNegativeInt
    textures: tuple[TextureFact, ...]
    budget_violations: tuple[str, ...]


class FindingEvidence(ContractModel):
    """Structured distinction between measurement and inference."""

    observation: str
    observed_value: JsonValue = None
    expected_value: JsonValue = None
    inference: str | None = None
    units: str | None = None


class Finding(ContractModel):
    """One evidence-backed inspection finding."""

    id: str
    code: str
    domain: str
    title: str
    description: str
    severity: Severity
    action_class: ActionClass
    confidence: UnitConfidence
    affected_components: tuple[str, ...]
    evidence: tuple[FindingEvidence, ...]
    profile_rule: str | None
    candidate_repairs: tuple[str, ...]


class InspectionResult(ContractModel):
    """Complete deterministic inspection output."""

    schema_version: Literal[1] = 1
    inspection_id: str
    source_filename: str
    profile_id: str
    profile_version: Literal[1]
    package: PackageFacts
    geometry: GeometryFacts | None
    transforms: TransformFacts | None
    naming: NamingFacts | None
    resources: ResourceFacts | None
    repair_eligibility: RepairEligibility
    findings: tuple[Finding, ...]


class RenamePayload(ContractModel):
    """Parameters for an index-preserving display-name repair."""

    payload_type: Literal["rename"] = "rename"
    component_type: Literal["node", "mesh"]
    component_index: NonNegativeInt
    before_name: str | None
    after_name: str


class NormalizationComponent(ContractModel):
    """Evidence for one component of a combined normalization transform."""

    component: Literal["scale", "orientation", "grounding"]
    evidence: str
    confidence: UnitConfidence


class NormalizationPayload(ContractModel):
    """Parameters and consequences for the approval-required root transform."""

    payload_type: Literal["normalization"] = "normalization"
    before_bounds: Bounds3D
    proposed_matrix: Matrix4
    expected_after_bounds: Bounds3D
    components: tuple[NormalizationComponent, ...]
    consequence_summary: str


class CandidateRepair(ContractModel):
    """A registered repair derived from one or more findings."""

    id: str
    kind: RepairKind
    action_class: ActionClass
    finding_ids: tuple[str, ...]
    description: str
    payload: Annotated[RenamePayload | NormalizationPayload, Field(discriminator="payload_type")]

    @model_validator(mode="after")
    def kind_matches_payload(self) -> "CandidateRepair":
        """Prevent a payload from being relabeled as another registered action."""
        if self.kind is RepairKind.NORMALIZATION_TRANSFORM:
            if not isinstance(self.payload, NormalizationPayload):
                raise ValueError("Normalization repair requires a normalization payload")
        elif not isinstance(self.payload, RenamePayload):
            raise ValueError("Rename repair requires a rename payload")
        return self


class RepairPlan(ContractModel):
    """Deterministic set of version-1 repair candidates."""

    schema_version: Literal[1] = 1
    plan_id: str
    inspection_id: str
    source_sha256: str
    profile_id: str
    profile_version: Literal[1]
    candidates: tuple[CandidateRepair, ...]
    auto_action_ids: tuple[str, ...]
    approval_action_ids: tuple[str, ...]
    blocked: bool
    blocked_reasons: tuple[str, ...]


class DecisionRecord(ContractModel):
    """Authorization or rejection of one candidate repair."""

    candidate_id: str
    decision: DecisionValue
    source: DecisionSource
    decided_at: datetime
    interrupt_id: str | None = None


class Decisions(ContractModel):
    """Versioned decision artifact for one repair plan."""

    schema_version: Literal[1] = 1
    plan_id: str
    records: tuple[DecisionRecord, ...]


class VerificationCheck(ContractModel):
    """One deterministic verification assertion."""

    code: str
    status: CheckStatus
    description: str
    expected: JsonValue = None
    actual: JsonValue = None


class VerificationResult(ContractModel):
    """Independent reload and verification output."""

    schema_version: Literal[1] = 1
    verification_id: str
    source_sha256: str
    output_sha256: str | None
    state: VerificationState
    checks: tuple[VerificationCheck, ...]
    remaining_warnings: tuple[str, ...]
    second_plan_candidate_count: NonNegativeInt


class ExecutedAction(ContractModel):
    """One repair action recorded in provenance."""

    candidate_id: str
    kind: RepairKind
    finding_ids: tuple[str, ...]
    authorization: DecisionValue


class Provenance(ContractModel):
    """Source, authorization, software, and timing provenance."""

    schema_version: Literal[1] = 1
    source_sha256: str
    output_sha256: str | None
    profile_id: str
    profile_version: Literal[1]
    application_version: str
    commit_sha: str
    library_versions: dict[str, str]
    executed_actions: tuple[ExecutedAction, ...]
    decisions: tuple[DecisionRecord, ...]
    started_at: datetime
    completed_at: datetime


class JobResult(ContractModel):
    """Summary and artifact inventory for a deterministic job."""

    schema_version: Literal[1] = 1
    job_id: str
    state: JobState
    verification_state: VerificationState
    ready_candidate: bool
    artifact_names: tuple[str, ...]
    result_zip: str | None
    message: str


class FixtureManifest(ContractModel):
    """Known facts and intended defects for a generated test fixture."""

    fixture_version: Literal[1] = 1
    fixture_id: str
    glb_filename: str
    sha256: str
    expected_bounds_m: Bounds3D
    expected_vertex_count: NonNegativeInt
    expected_triangle_count: NonNegativeInt
    expected_material_count: NonNegativeInt
    expected_defect_codes: tuple[str, ...]
    original_asset: bool
