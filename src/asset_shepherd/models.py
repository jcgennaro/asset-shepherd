"""Versioned JSON models shared by the deterministic core and agent boundary."""

from datetime import datetime
from enum import StrEnum
from re import compile as compile_pattern
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

NonNegativeInt = Annotated[int, Field(ge=0)]
PositiveInt = Annotated[int, Field(gt=0)]
UnitConfidence = Annotated[float, Field(ge=0.0, le=1.0)]
PolicyRuleSource = Literal[
    "CONFIRMED_INTENT",
    "DERIVED_INTENT",
    "FAMILY_DEFAULT",
    "USER_OVERRIDE",
]
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


class CheckBasis(StrEnum):
    """Authority behind a finding or verification assertion."""

    UNIVERSAL_INVARIANT = "UNIVERSAL_INVARIANT"
    FROZEN_PROJECT_POLICY = "FROZEN_PROJECT_POLICY"
    OBJECTIVE_SOURCE_DIAGNOSTIC = "OBJECTIVE_SOURCE_DIAGNOSTIC"
    EXTERNAL_CONSUMER_EVIDENCE = "EXTERNAL_CONSUMER_EVIDENCE"
    AGENT_ASSESSMENT = "AGENT_ASSESSMENT"


class AssetTargetUse(StrEnum):
    """User-confirmed destination for the uploaded asset."""

    STATIC_GAME_ASSET = "STATIC_GAME_ASSET"
    RIG_READY_CHARACTER = "RIG_READY_CHARACTER"
    PLAYABLE_CHARACTER = "PLAYABLE_CHARACTER"


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


class AgentDisposition(StrEnum):
    """The workflow agent's evidence-backed next-step judgment."""

    ACCEPT = "ACCEPT"
    REPAIR = "REPAIR"
    REPORT_ONLY = "REPORT_ONLY"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    RETURN_TO_CREATION_TOOL = "RETURN_TO_CREATION_TOOL"


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

    node_names: tuple[str | None, ...]
    missing_node_indices: tuple[int, ...]
    invalid_node_indices: tuple[int, ...]
    duplicate_node_names: dict[str, tuple[int, ...]]
    mesh_names: tuple[str | None, ...]
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


class MaterialFact(ContractModel):
    """Objective glTF material metadata available without visual interpretation."""

    material_index: NonNegativeInt
    name: str | None
    alpha_mode: str
    alpha_cutoff: float | None
    double_sided: bool
    base_color_factor: tuple[float, float, float, float]
    metallic_factor: float
    roughness_factor: float
    emissive_factor: Vector3


class PrimitiveAttributeDiagnostics(ContractModel):
    """Objective attribute and topology diagnostics for one mesh primitive."""

    mesh_index: NonNegativeInt
    primitive_index: NonNegativeInt
    position_count: NonNegativeInt
    index_count: NonNegativeInt
    has_normals: bool
    has_tangents: bool
    has_texcoord_0: bool
    attribute_count_mismatches: tuple[str, ...]
    non_finite_position_count: NonNegativeInt
    non_finite_normal_count: NonNegativeInt
    non_unit_normal_count: NonNegativeInt
    non_finite_tangent_count: NonNegativeInt
    invalid_tangent_handedness_count: NonNegativeInt
    non_finite_texcoord_0_count: NonNegativeInt
    out_of_range_index_count: NonNegativeInt
    degenerate_triangle_count: NonNegativeInt


class SourceDiagnostics(ContractModel):
    """Profile-free diagnostic facts that are informative but not user-authored policy."""

    primitives: tuple[PrimitiveAttributeDiagnostics, ...]
    empty_leaf_node_indices: tuple[int, ...]
    unreachable_node_indices: tuple[int, ...]
    unused_mesh_indices: tuple[int, ...]
    unused_material_indices: tuple[int, ...]
    unused_texture_indices: tuple[int, ...]
    unused_image_indices: tuple[int, ...]
    unused_sampler_indices: tuple[int, ...]
    duplicate_material_groups: tuple[tuple[int, ...], ...]
    duplicate_texture_groups: tuple[tuple[int, ...], ...]
    root_world_origins_m: tuple[Vector3, ...]
    bounds_ground_center_m: Vector3


class PreflightResult(ContractModel):
    """Profile-free measurements allowed before a user agrees to a target."""

    schema_version: Literal[1] = 1
    preflight_id: str
    source_filename: str
    package: PackageFacts
    geometry: GeometryFacts | None
    transforms: TransformFacts | None
    materials: tuple[MaterialFact, ...]
    structural_eligibility: RepairEligibility
    parse_error: str | None
    diagnostics: SourceDiagnostics | None = None


class FindingEvidence(ContractModel):
    """Structured distinction between measurement and inference."""

    observation: str
    observed_value: JsonValue = None
    expected_value: JsonValue = None
    inference: str | None = None
    units: str | None = None


class FindingRuleProvenance(ContractModel):
    """Exact versioned policy parameters that caused one finding."""

    profile_id: str
    profile_version: Literal[1]
    parameters: dict[str, JsonValue]
    sources: dict[str, PolicyRuleSource] = Field(default_factory=dict)


class Finding(ContractModel):
    """One evidence-backed inspection finding."""

    id: str
    code: str
    domain: str
    title: str
    description: str
    severity: Severity
    action_class: ActionClass
    basis: CheckBasis = CheckBasis.OBJECTIVE_SOURCE_DIAGNOSTIC
    confidence: UnitConfidence
    affected_components: tuple[str, ...]
    evidence: tuple[FindingEvidence, ...]
    profile_rule: str | None
    rule_provenance: FindingRuleProvenance | None = None
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
    diagnostics: SourceDiagnostics | None = None


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


class AgentRepairAssessment(ContractModel):
    """One model-authored assessment bound to objective observations and a confirmed target."""

    schema_version: Literal[1] = 1
    assessment_id: Annotated[str, Field(pattern=r"^assessment-[0-9a-f]{16}-v1$")]
    initiating_tool_call_id: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    disposition: AgentDisposition
    summary: Annotated[str, Field(min_length=12, max_length=1000)]
    evidence: tuple[Annotated[str, Field(min_length=4, max_length=500)], ...]
    confidence: UnitConfidence
    semantic_height_axis: Literal["X", "Y", "Z"] | None = None
    scale_to_confirmed_height: bool = False
    rotation_axis: Literal["X", "Y", "Z"] | None = None
    rotation_degrees: Literal[-180, -90, 0, 90, 180] = 0
    ground_to_y_zero: bool = False
    rename_invalid_display_names: bool = False
    source_views_used: tuple[str, ...] = ()

    @model_validator(mode="after")
    def action_fields_match_disposition(self) -> "AgentRepairAssessment":
        """Keep a model assessment internally coherent before a plan can be registered."""
        has_action = any(
            (
                self.scale_to_confirmed_height,
                self.rotation_degrees != 0,
                self.ground_to_y_zero,
                self.rename_invalid_display_names,
            )
        )
        if self.disposition is AgentDisposition.REPAIR and not has_action:
            raise ValueError("A REPAIR disposition must request at least one supported action")
        if self.disposition is not AgentDisposition.REPAIR and has_action:
            raise ValueError("Only a REPAIR disposition may request mutation")
        if self.scale_to_confirmed_height and self.semantic_height_axis is None:
            raise ValueError("Scaling requires the semantic height axis observed by the agent")
        if self.rotation_degrees != 0 and self.rotation_axis is None:
            raise ValueError("Rotation degrees require a rotation axis")
        return self


class AgentCandidateReassessment(ContractModel):
    """Model judgment after comparing standardized source and candidate views."""

    schema_version: Literal[1] = 1
    reassessment_id: Annotated[str, Field(pattern=r"^reassessment-[0-9a-f]{16}-v1$")]
    initiating_tool_call_id: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    source_assessment_id: Annotated[str, Field(pattern=r"^assessment-[0-9a-f]{16}-v1$")]
    candidate_satisfies_assessment: bool
    summary: Annotated[str, Field(min_length=12, max_length=1000)]
    evidence: tuple[Annotated[str, Field(min_length=4, max_length=500)], ...]
    confidence: UnitConfidence
    source_views_used: tuple[str, ...]
    candidate_views_used: tuple[str, ...]

    @model_validator(mode="after")
    def comparison_has_visual_evidence(self) -> "AgentCandidateReassessment":
        """Require both sides of the visual comparison and at least one stated observation."""
        if not self.source_views_used or not self.candidate_views_used:
            raise ValueError("Candidate reassessment requires source and candidate views")
        if not self.evidence:
            raise ValueError("Candidate reassessment requires explicit evidence")
        return self


class ConversationTurnRecord(ContractModel):
    """Immutable link from one completed repair turn to the next user-requested turn."""

    schema_version: Literal[1] = 1
    turn_index: NonNegativeInt
    source_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    output_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    plan_id: str
    agent_assessment_id: str | None = None
    candidate_reassessment_id: str | None = None
    verification_state: VerificationState
    result_zip_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    continuation_feedback: Annotated[str, Field(min_length=1, max_length=1000)]


class PlanSelection(ContractModel):
    """Agent selection of registered candidates from one deterministic plan."""

    schema_version: Literal[1] = 1
    plan_id: str
    candidate_ids: tuple[str, ...]


class ApprovalCard(ContractModel):
    """JSON-serializable human decision card for one normalization operation."""

    schema_version: Literal[1] = 1
    plan_id: str
    candidate_id: str
    finding_ids: tuple[str, ...]
    title: str
    consequence_summary: str
    before_bounds: Bounds3D
    before_target_extent_m: Annotated[float, Field(ge=0.0)]
    proposed_matrix: Matrix4
    expected_after_bounds: Bounds3D
    expected_target_extent_m: Annotated[float, Field(ge=0.0)]
    target_extent_label: str = "Height"
    components: tuple[NormalizationComponent, ...]
    options: tuple[Literal["APPROVE", "REJECT"], ...] = ("APPROVE", "REJECT")


class ApprovalResponse(ContractModel):
    """Validated human response returned through a Strands interrupt ID."""

    schema_version: Literal[1] = 1
    candidate_id: str
    approved: bool


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
    planning_authority: Literal["LEGACY_DETERMINISTIC", "AGENT_ORCHESTRATED"] = (
        "LEGACY_DETERMINISTIC"
    )
    agent_assessment_id: str | None = None

    @model_validator(mode="after")
    def authority_has_assessment(self) -> "RepairPlan":
        """Require a traceable assessment for every agent-authored repair plan."""
        if self.planning_authority == "AGENT_ORCHESTRATED" and self.agent_assessment_id is None:
            raise ValueError("Agent-orchestrated plans require an assessment identifier")
        if (
            self.planning_authority == "LEGACY_DETERMINISTIC"
            and self.agent_assessment_id is not None
        ):
            raise ValueError("Legacy deterministic plans cannot cite an agent assessment")
        return self


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
    basis: CheckBasis = CheckBasis.UNIVERSAL_INVARIANT
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


class ProfilePolicyProvenance(ContractModel):
    """Frozen identity and derivation record for one job's project policy."""

    frozen_profile_id: str
    base_preset_id: str
    policy_family_id: str | None = None
    explicit_overrides: dict[str, JsonValue]
    rule_sources: dict[str, PolicyRuleSource] = Field(default_factory=dict)
    profile_version: Literal[1]
    canonical_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class AssetIntentProvenance(ContractModel):
    """Immutable user-confirmed target story bound to one inspection job."""

    intent_version: Literal[1] = 1
    intent_id: Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]
    original_description: Annotated[str, Field(min_length=12, max_length=600)]
    target_use: AssetTargetUse
    target_height_cm: Annotated[float, Field(gt=0.0, le=100000.0)]
    confirmed_story: Annotated[str, Field(min_length=20, max_length=1000)]
    confirmed_at: datetime
    canonical_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class Provenance(ContractModel):
    """Source, authorization, software, and timing provenance."""

    schema_version: Literal[1] = 1
    source_sha256: str
    output_sha256: str | None
    profile_id: str
    profile_version: Literal[1]
    profile_policy: ProfilePolicyProvenance | None = None
    asset_intent: AssetIntentProvenance | None = None
    agent_assessment: AgentRepairAssessment | None = None
    candidate_reassessment: AgentCandidateReassessment | None = None
    conversation_turn_index: NonNegativeInt = 0
    prior_turns: tuple[ConversationTurnRecord, ...] = ()
    application_version: str
    commit_sha: str
    library_versions: dict[str, str]
    executed_actions: tuple[ExecutedAction, ...]
    decisions: tuple[DecisionRecord, ...]
    started_at: datetime
    completed_at: datetime

    @model_validator(mode="after")
    def policy_identity_matches_profile(self) -> "Provenance":
        """Keep the legacy profile fields aligned with the frozen policy record."""
        if self.profile_policy is not None:
            if self.profile_policy.frozen_profile_id != self.profile_id:
                raise ValueError("Frozen policy identifier must match profile_id")
            if self.profile_policy.profile_version != self.profile_version:
                raise ValueError("Frozen policy version must match profile_version")
        if self.candidate_reassessment is not None and self.agent_assessment is None:
            raise ValueError("Candidate reassessment requires its source agent assessment")
        if (
            self.candidate_reassessment is not None
            and self.agent_assessment is not None
            and self.candidate_reassessment.source_assessment_id
            != self.agent_assessment.assessment_id
        ):
            raise ValueError("Candidate reassessment must cite the packaged agent assessment")
        if any(turn.turn_index >= self.conversation_turn_index for turn in self.prior_turns):
            raise ValueError("Prior conversation turns must precede the current turn")
        if tuple(turn.turn_index for turn in self.prior_turns) != tuple(
            range(len(self.prior_turns))
        ):
            raise ValueError("Prior conversation turns must be contiguous and ordered")
        if self.conversation_turn_index != len(self.prior_turns):
            raise ValueError("Current conversation turn must follow the complete prior-turn chain")
        return self


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


class AgentTokenUsage(ContractModel):
    """Model token usage exposed by Strands when the provider reports it."""

    input_tokens: NonNegativeInt
    output_tokens: NonNegativeInt
    total_tokens: NonNegativeInt


class AgentToolMetric(ContractModel):
    """Aggregated execution metrics for one Strands tool."""

    name: str
    call_count: NonNegativeInt
    success_count: NonNegativeInt
    error_count: NonNegativeInt
    duration_seconds: Annotated[float, Field(ge=0.0)]


class AgentMetrics(ContractModel):
    """Observable metrics for one complete interrupted agent workflow."""

    schema_version: Literal[1] = 1
    provider: str
    model_id: str
    invocation_duration_seconds: Annotated[float, Field(ge=0.0)]
    token_usage: AgentTokenUsage | None
    tool_calls: tuple[AgentToolMetric, ...]
    interrupt_count: NonNegativeInt
    correction_attempts: Annotated[int, Field(ge=0, le=1)]
    final_verification_state: VerificationState


class AgentWorkflowResult(ContractModel):
    """Structured agent result kept outside the contracted deterministic ZIP."""

    schema_version: Literal[1] = 1
    prompt_version: Literal[1, 2, 3] = 3
    job_result: JobResult
    user_message: str
    metrics: AgentMetrics


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
