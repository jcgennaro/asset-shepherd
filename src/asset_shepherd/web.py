"""Local FastAPI product surface for the Asset Shepherd workflow."""

from __future__ import annotations

import json
import logging
import math
import mimetypes
import os
import re
import shutil
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path
from threading import RLock
from typing import Annotated, BinaryIO, Literal, cast
from uuid import uuid4

import numpy as np
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import JsonValue
from strands.agent import AgentResult

from asset_shepherd.agent_job import AgentJob, AgentWorkflowError, VerificationFunction
from asset_shepherd.agent_runtime import (
    AssetShepherdAgent,
    build_live_agent,
    build_scripted_agent,
    workflow_model_available,
)
from asset_shepherd.agentcore_dispatch import AgentCoreCommandDispatcher, AgentCoreDispatchError
from asset_shepherd.cloud_workspace import S3DynamoWorkspaceRepository
from asset_shepherd.glb import iter_world_matrices, load_glb, world_bounds
from asset_shepherd.hosted_models import (
    hosted_model_choices,
    hosted_model_values,
    resolve_hosted_model,
)
from asset_shepherd.hosted_workspace import (
    MAX_HOSTED_WORKSPACES,
    HostedWorkspace,
    HostedWorkspaceError,
    HostedWorkspaceStore,
    WorkspacePhase,
    WorkspaceRepository,
    copy_validated_upload,
)
from asset_shepherd.inspector import inspect_asset
from asset_shepherd.intake_analyzer import (
    DeterministicTargetIntakeAnalyzer,
    TargetIntakeAnalyzer,
    TargetIntakeContentRefusal,
    build_target_intake_analyzer,
)
from asset_shepherd.intent import (
    ENDPOINT_LABELS,
    TARGET_USE_LABELS,
    build_asset_intent,
    craft_confirmed_story,
    normalize_intent_description,
    validate_asset_intent,
)
from asset_shepherd.models import (
    AgentDisposition,
    AgentWorkflowResult,
    ApprovalCard,
    AssetEndpoint,
    AssetIntentProvenance,
    AssetTargetUse,
    AssetViewingUse,
    CheckStatus,
    ComponentRemovalPayload,
    ConversationTurnRecord,
    DecisionRecord,
    DecisionValue,
    DegenerateGeometryPayload,
    Finding,
    InspectionResult,
    MeshSimplificationPayload,
    NormalizationPayload,
    ProfilePolicyProvenance,
    ProjectProfile,
    ProposalDisposition,
    ProposalLane,
    ProposalResponse,
    RepairEligibility,
    RepairKind,
    Severity,
    VerificationState,
    WeldPayload,
)
from asset_shepherd.policy_resolution import PolicyResolution, resolve_policy_family
from asset_shepherd.profile_policy import canonical_profile_sha256
from asset_shepherd.spending import PUBLIC_SPEND_MESSAGES
from asset_shepherd.target_intake import (
    TargetEvidenceSource,
    TargetFieldEvidence,
    TargetIntakeContract,
    clarify_target_intake,
    confirm_target_viewing_use,
)
from asset_shepherd.upload_preflight import UploadPreflight
from asset_shepherd.verification import verify_repair
from asset_shepherd.web_auth import install_login

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
_PACKAGE_ROOT = Path(__file__).resolve().parent
_DEFAULT_PROJECT_ROOT = _PACKAGE_ROOT.parents[1]
_CONFIGURED_WORK_ROOT = os.environ.get("ASSET_SHEPHERD_WORK_ROOT", "").strip()
_DEFAULT_WORK_ROOT = (
    Path(_CONFIGURED_WORK_ROOT)
    if _CONFIGURED_WORK_ROOT
    else _DEFAULT_PROJECT_ROOT / "build" / "web" / "jobs"
)
if _CONFIGURED_WORK_ROOT and not _DEFAULT_WORK_ROOT.is_absolute():
    raise ValueError("ASSET_SHEPHERD_WORK_ROOT must be an absolute path")
mimetypes.add_type("model/gltf-binary", ".glb")
logger = logging.getLogger(__name__)


def _workspace_notebook_url(request: Request, workspace_id: str) -> str:
    """Return the newest visible notebook entry after a workflow transition."""
    return f"{request.url_for('hosted_workspace_page', workspace_id=workspace_id)}#current-turn"


def _asset_download_stem(asset_name: str) -> str:
    """Return a portable filename stem from the agent-assigned asset name."""
    ascii_name = unicodedata.normalize("NFKD", asset_name).encode("ascii", "ignore").decode()
    stem = re.sub(r"[^a-z0-9]+", "-", ascii_name.casefold()).strip("-")
    return stem[:64].rstrip("-") or "asset-shepherd-model"


def _shepherded_download_filename(
    asset_name: str,
    shepherded_on: date | None = None,
) -> str:
    """Return the user-facing verified-model filename."""
    resolved_date = shepherded_on or date.today()
    return f"{_asset_download_stem(asset_name)}_shepherded_{resolved_date:%m%d%y}.glb"


def _static_asset_version() -> str:
    """Return a content fingerprint so browsers cannot retain stale UI assets."""
    digest = sha256()
    for asset_name in (
        "app.css",
        "app.js",
        "navigation-tour.js",
        "banana-scale.glb",
        "favicon.svg",
        "vendor/model-viewer.min.js",
    ):
        digest.update((_PACKAGE_ROOT / "static" / asset_name).read_bytes())
    return digest.hexdigest()[:12]


class UploadValidationError(ValueError):
    """Raised when a browser upload violates the contracted GLB boundary."""


@dataclass(frozen=True)
class PolicyFamilyOption:
    """The one trusted parameterized family used to resolve new web jobs."""

    family_id: str
    path: Path
    profile: ProjectProfile
    canonical_sha256: str


@dataclass(frozen=True)
class PolicyProposalView:
    """Intent-derived policy proposal formatted for review before upload."""

    resolution: PolicyResolution
    summary: tuple[tuple[str, str], ...]
    review_rules: tuple[tuple[str, str], ...]
    form_defaults: dict[str, JsonValue]


@dataclass(frozen=True)
class ExpectationView:
    """One user-facing target assumption with its authority made explicit."""

    label: str
    value: str
    source: str
    detail: str


@dataclass(frozen=True)
class ExpectationGroupView:
    """One of three progressively disclosed target-review groups."""

    label: str
    summary: str
    items: tuple[ExpectationView, ...]


@dataclass(frozen=True)
class ComparisonBoundsView:
    """One model's placed bounds in the shared comparison scene."""

    minimum_m: tuple[float, float, float]
    maximum_m: tuple[float, float, float]
    dimensions_m: tuple[float, float, float]
    center_m: tuple[float, float, float]
    longest_m: float
    corners_m: tuple[tuple[float, float, float], ...]


@dataclass(frozen=True)
class MetricAxisTickView:
    """One projected meter tick anchored in the 3D scene."""

    slot_name: str
    label: str
    position_m: tuple[float, float, float]


@dataclass(frozen=True)
class MetricAxisView:
    """One X, Y, or Z metric ruler with approximately five major ticks."""

    axis: str
    ticks: tuple[MetricAxisTickView, ...]


@dataclass(frozen=True)
class ComponentBoundsView:
    """One exact component's world-space oriented box in the source viewer."""

    component_id: str
    label: str
    corners_m: tuple[tuple[float, float, float], ...]


@dataclass(frozen=True)
class ComparisonSceneView:
    """Geometry needed to stage before and after assets in one scene."""

    before: ComparisonBoundsView
    after: ComparisonBoundsView
    combined: ComparisonBoundsView
    after_offset_m: tuple[float, float, float]
    banana_offset_m: tuple[float, float, float]
    banana_anchor_m: tuple[float, float, float]
    axes: tuple[MetricAxisView, ...]
    client_data: dict[str, JsonValue]
    component_boxes: tuple[ComponentBoundsView, ...] = ()


@dataclass(frozen=True)
class SourceSceneView:
    """Geometry needed to frame one immutable uploaded asset."""

    before: ComparisonBoundsView
    combined: ComparisonBoundsView
    banana_offset_m: tuple[float, float, float]
    banana_anchor_m: tuple[float, float, float]
    axes: tuple[MetricAxisView, ...]
    client_data: dict[str, JsonValue]
    component_boxes: tuple[ComponentBoundsView, ...] = ()
    proposed_origin_m: tuple[float, float, float] | None = None


@dataclass(frozen=True)
class ComponentProposalView:
    """One exact disconnected component exposed for visual review."""

    component_id: str
    label: str
    detail: str
    proposed_removal: bool


@dataclass(frozen=True)
class InspectionCheckView:
    """One user-facing inspection lane with its result and phase-aware action."""

    label: str
    status: str
    status_label: str
    description: str
    action: str
    response_lane: ProposalLane | None = None
    action_heading: str = "Proposed action"
    component_proposals: tuple[ComponentProposalView, ...] = ()

    @property
    def detail(self) -> str:
        """Return the complete hover and accessibility explanation for this lane."""
        if self.action == "—":
            return self.description
        return f"{self.description} {self.action_heading}: {self.action}"


@dataclass(frozen=True)
class HostedStartDraft:
    """Short-lived validated upload state awaiting the user's description."""

    draft_id: str
    original_filename: str
    source_path: Path
    replace_workspace_id: str | None
    model_id: str | None = None
    initial_description: str = ""

    @property
    def display_name(self) -> str:
        """Return a readable temporary name until intake assigns the asset name."""
        words = re.sub(r"[_-]+", " ", Path(self.original_filename).stem).strip()
        return words.title()[:48] or "Uploaded asset"


@dataclass(frozen=True)
class GalleryStatusView:
    """Compact user-facing progress state for one persisted asset workspace."""

    label: str
    tone: str


def gallery_status(phase: WorkspacePhase, turn_index: int = 0) -> GalleryStatusView:
    """Translate an internal durable phase into concise workflow language."""
    if turn_index > 0:
        label, tone = {
            WorkspacePhase.TARGET_CONFIRMATION: ("Describe", "pending"),
            WorkspacePhase.APPROVAL: ("Review", "attention"),
            WorkspacePhase.COMPLETE: ("Ready", "success"),
            WorkspacePhase.BLOCKED: ("Blocked", "danger"),
            WorkspacePhase.ERROR: ("Failed", "danger"),
        }[phase]
        return GalleryStatusView(f"Step 4.{turn_index} · {label}", tone)
    return {
        WorkspacePhase.TARGET_CONFIRMATION: GalleryStatusView("Step 2 · Describe", "pending"),
        WorkspacePhase.APPROVAL: GalleryStatusView("Step 3 · Review", "attention"),
        WorkspacePhase.COMPLETE: GalleryStatusView("Step 3 · Ready", "success"),
        WorkspacePhase.BLOCKED: GalleryStatusView("Step 3 · Blocked", "danger"),
        WorkspacePhase.ERROR: GalleryStatusView("Step 3 · Failed", "danger"),
    }[phase]


@dataclass(frozen=True)
class InspectionSummaryView:
    """Agent-facing summary that foregrounds only measured basics and attention items."""

    headline: str
    basics: str
    normal: str
    attention: tuple[str, ...]


@dataclass(frozen=True)
class ResultPresentationView:
    """Concise result copy derived from verification and post-repair evidence."""

    kind: str
    headline: str
    state_label: str
    summary: str
    passed_title: str
    passed: str
    attention_title: str
    attention_detail: str
    next_step: str
    package_label: str
    download_label: str


@dataclass(frozen=True)
class NotebookTurnView:
    """One completed agent/user/model-state exchange in the scroll notebook."""

    turn: ConversationTurnRecord
    proposal_summary: str
    decision_summary: str | None
    outcome_summary: str


@dataclass(frozen=True)
class FrozenProfile:
    """Resolved immutable policy copy bound to one job workspace."""

    profile_id: str
    name: str
    path: Path
    policy_provenance: ProfilePolicyProvenance


def _yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def _profile_summary(profile: ProjectProfile) -> tuple[tuple[str, str], ...]:
    orientation = (
        "Y-up required" if profile.orientation.require_y_up_geometry else "No Y-up requirement"
    )
    grounding = (
        f"grounded within {profile.orientation.ground_tolerance_cm:g} cm"
        if profile.orientation.require_ground_contact
        else "no ground-contact requirement"
    )
    uniqueness: list[str] = []
    if profile.naming.require_unique_node_names:
        uniqueness.append("node")
    if profile.naming.require_unique_mesh_names:
        uniqueness.append("mesh")
    unique_text = f"unique {' + '.join(uniqueness)} names" if uniqueness else "duplicates allowed"
    authorization: list[str] = []
    if profile.repair_policy.auto_rename:
        authorization.append("display-name fixes automatic")
    if profile.repair_policy.require_approval_for_normalization_transform:
        authorization.append("physical normalization needs approval")
    return (
        (
            "Size",
            f"{profile.expected_height_cm.target / 100:g} m height "
            f"± {profile.expected_height_cm.tolerance / 100:g} m",
        ),
        ("Orientation", f"{orientation}; {grounding}"),
        ("Naming", f"Pattern {profile.naming.pattern}; {unique_text}"),
        (
            "Budgets",
            f"{profile.budgets.max_triangles:,} tris; {profile.budgets.max_materials} materials; "
            f"{profile.budgets.max_textures} textures at "
            f"{profile.budgets.max_texture_dimension}px max",
        ),
        ("Authorization", "; ".join(authorization)),
    )


def _profile_review_rules(
    profile: ProjectProfile,
    canonical_sha256: str,
) -> tuple[tuple[str, str], ...]:
    return (
        ("Policy ID", profile.profile_id),
        ("Version", str(profile.profile_version)),
        ("Canonical SHA-256", canonical_sha256),
        ("Engine", profile.engine),
        ("Asset type", profile.asset_type),
        ("Target height", f"{profile.expected_height_cm.target:g} cm"),
        ("Height tolerance", f"± {profile.expected_height_cm.tolerance:g} cm"),
        ("Require Y-up geometry", _yes_no(profile.orientation.require_y_up_geometry)),
        (
            "Infer vertical from dominant extent",
            _yes_no(profile.orientation.infer_vertical_from_dominant_extent),
        ),
        ("Require ground contact", _yes_no(profile.orientation.require_ground_contact)),
        ("Ground tolerance", f"{profile.orientation.ground_tolerance_cm:g} cm"),
        ("Name pattern", profile.naming.pattern),
        ("Unique node names", _yes_no(profile.naming.require_unique_node_names)),
        ("Unique mesh names", _yes_no(profile.naming.require_unique_mesh_names)),
        ("Maximum triangles", f"{profile.budgets.max_triangles:,}"),
        ("Maximum materials", str(profile.budgets.max_materials)),
        ("Maximum textures", str(profile.budgets.max_textures)),
        ("Maximum texture dimension", f"{profile.budgets.max_texture_dimension}px"),
        ("Automatic display-name repair", _yes_no(profile.repair_policy.auto_rename)),
        (
            "Approval for physical normalization",
            _yes_no(profile.repair_policy.require_approval_for_normalization_transform),
        ),
    )


def _profile_form_defaults(profile: ProjectProfile) -> dict[str, JsonValue]:
    return {
        "custom_height_tolerance_cm": profile.expected_height_cm.tolerance,
        "custom_require_y_up": profile.orientation.require_y_up_geometry,
        "custom_require_ground_contact": profile.orientation.require_ground_contact,
        "custom_ground_tolerance_cm": profile.orientation.ground_tolerance_cm,
        "custom_naming_pattern": profile.naming.pattern,
        "custom_max_triangles": profile.budgets.max_triangles,
        "custom_max_materials": profile.budgets.max_materials,
        "custom_max_textures": profile.budgets.max_textures,
        "custom_max_texture_dimension": profile.budgets.max_texture_dimension,
    }


def _required_custom_value(values: Mapping[str, str | None], key: str) -> str:
    value = values.get(key)
    if value is None or not value.strip():
        raise UploadValidationError("Complete every enabled custom-policy field.")
    return value.strip()


def _custom_float(values: Mapping[str, str | None], key: str, label: str) -> float:
    text = _required_custom_value(values, key)
    try:
        value = float(text)
    except ValueError as error:
        raise UploadValidationError(f"{label} must be a number.") from error
    if not math.isfinite(value):
        raise UploadValidationError(f"{label} must be finite.")
    return value


def _custom_int(values: Mapping[str, str | None], key: str, label: str) -> int:
    text = _required_custom_value(values, key)
    try:
        return int(text)
    except ValueError as error:
        raise UploadValidationError(f"{label} must be a whole number.") from error


def _custom_bool(values: Mapping[str, str | None], key: str, label: str) -> bool:
    text = _required_custom_value(values, key)
    if text not in {"true", "false"}:
        raise UploadValidationError(f"{label} must be yes or no.")
    return text == "true"


def _custom_overrides(values: Mapping[str, str | None]) -> dict[str, JsonValue]:
    """Parse the complete advanced form into supported ProjectProfile values."""
    naming_pattern = _required_custom_value(values, "custom_naming_pattern")
    return {
        "expected_height_cm.tolerance": _custom_float(
            values, "custom_height_tolerance_cm", "Height tolerance"
        ),
        "orientation.require_y_up_geometry": _custom_bool(
            values, "custom_require_y_up", "Y-up requirement"
        ),
        "orientation.require_ground_contact": _custom_bool(
            values, "custom_require_ground_contact", "Ground-contact requirement"
        ),
        "orientation.ground_tolerance_cm": _custom_float(
            values, "custom_ground_tolerance_cm", "Ground tolerance"
        ),
        "naming.pattern": naming_pattern,
        "budgets.max_triangles": _custom_int(values, "custom_max_triangles", "Triangle budget"),
        "budgets.max_materials": _custom_int(values, "custom_max_materials", "Material budget"),
        "budgets.max_textures": _custom_int(values, "custom_max_textures", "Texture budget"),
        "budgets.max_texture_dimension": _custom_int(
            values, "custom_max_texture_dimension", "Texture-dimension budget"
        ),
    }


def _rule_explanation(finding: Finding) -> str | None:
    rule = finding.rule_provenance
    if rule is None or finding.profile_rule is None:
        return None
    values = rule.parameters
    if finding.profile_rule == "expected_height_cm":
        return (
            f"Height target {values['expected_height_cm.target']} cm "
            f"± {values['expected_height_cm.tolerance']} cm"
        )
    if finding.profile_rule == "orientation.require_y_up_geometry":
        return "Y-up geometry is required"
    if finding.profile_rule == "orientation.require_ground_contact":
        return f"Ground contact is required within {values['orientation.ground_tolerance_cm']} cm"
    if finding.profile_rule == "naming.pattern":
        return f"Names must match {values['naming.pattern']}"
    if finding.profile_rule == "naming.require_unique_node_names":
        return "Node names must be unique"
    if finding.profile_rule == "naming.require_unique_mesh_names":
        return "Mesh names must be unique"
    value = values.get(finding.profile_rule)
    return f"{finding.profile_rule} = {value}"


@dataclass(frozen=True)
class StageView:
    """One named workflow stage and its current UI status."""

    name: str
    eyebrow: str
    status: str


@dataclass(frozen=True)
class JourneyStep:
    """One plain-language step in a story-specific product journey."""

    number: str
    title: str
    description: str


@dataclass(frozen=True)
class WorkflowStepView:
    """One user-facing workspace step and its deterministic progress state."""

    slug: str
    label: str
    status: str


@dataclass(frozen=True)
class StoryDefinition:
    """Presentation copy for one functionally equivalent user-story concept."""

    slug: str
    nav_label: str
    audience: str
    user_story: str
    headline: str
    promise: str
    intake_eyebrow: str
    intake_title: str
    profile_label: str
    upload_label: str
    upload_hint: str
    submit_label: str
    job_kicker: str
    job_question: str
    source_label: str
    candidate_label: str
    findings_heading: str
    verification_heading: str
    approval_eyebrow: str
    rejection_note: str
    landing_template: str
    steps: tuple[JourneyStep, ...]


STORIES = (
    StoryDefinition(
        slug="game-developer",
        nav_label="Game developer",
        audience="Indie game developer",
        user_story=(
            "I just acquired a model and need to know whether it can enter my game without "
            "surprise scale, orientation, or import cleanup."
        ),
        headline="From downloaded GLB to an import-ready package.",
        promise=(
            "Know what blocks the asset, make one meaningful call, and get evidence you can ship."
        ),
        intake_eyebrow="Start your import check",
        intake_title="Where should this asset work?",
        profile_label="Choose the target convention",
        upload_label="Add the GLB",
        upload_hint="One static mesh · embedded resources",
        submit_label="Check import readiness",
        job_kicker="Import readiness run",
        job_question="What did I find?",
        source_label="Downloaded asset",
        candidate_label="Import-ready candidate",
        findings_heading="What needs attention",
        verification_heading="Ready-to-import proof",
        approval_eyebrow="Your one project-impact decision",
        rejection_note=(
            "Rejecting leaves the physical normalization unresolved and records the decision."
        ),
        landing_template="story.html",
        steps=(
            JourneyStep(
                "01", "Choose the target", "Select the scale and naming rules your project expects."
            ),
            JourneyStep(
                "02",
                "Upload the GLB",
                "Add one static GLB for inspection.",
            ),
            JourneyStep(
                "03",
                "See import blockers",
                "Read measured problems in plain language, sorted by consequence.",
            ),
            JourneyStep(
                "04",
                "Make one call",
                "Approve or reject scale, upright orientation, and grounding together.",
            ),
            JourneyStep(
                "05",
                "Download with proof",
                "Get the candidate plus inspection, decisions, verification, and provenance.",
            ),
        ),
    ),
    StoryDefinition(
        slug="artist",
        nav_label="3D artist",
        audience="3D artist and asset creator",
        user_story=(
            "I want to hand off my work for technical cleanup without losing control of its look, "
            "materials, topology, or intended proportions."
        ),
        headline="See exactly what changes—and what stays yours.",
        promise=(
            "Keep the art direction. Let deterministic tools handle the reversible intake work."
        ),
        intake_eyebrow="Start a technical handoff",
        intake_title="Bring the model",
        profile_label="Choose the delivery target",
        upload_label="Choose your source GLB",
        upload_hint="GLB 2.0 · static mesh · embedded resources",
        submit_label="Preview the handoff",
        job_kicker="Artist handoff",
        job_question="What did I find?",
        source_label="Uploaded model",
        candidate_label="Verified delivery copy",
        findings_heading="Technical handoff notes",
        verification_heading="Verification checks",
        approval_eyebrow="Your artistic-intent checkpoint",
        rejection_note=(
            "Rejecting keeps your scale and orientation exactly as delivered. The decision and any "
            "remaining physical findings stay visible in the package."
        ),
        landing_template="story.html",
        steps=(
            JourneyStep("01", "Share the model", "Upload one static GLB."),
            JourneyStep(
                "02",
                "Inspect without editing",
                "Asset facts are measured before any candidate is written.",
            ),
            JourneyStep(
                "03",
                "Review every proposed change",
                "Display-name fixes are separated from physical changes.",
            ),
            JourneyStep(
                "04",
                "Keep artistic control",
                "Approve or reject the combined physical normalization card.",
            ),
            JourneyStep(
                "05",
                "Compare and deliver",
                "View source and candidate, then download the full evidence package.",
            ),
        ),
    ),
    StoryDefinition(
        slug="technical-artist",
        nav_label="Technical artist",
        audience="Technical artist and content lead",
        user_story=(
            "I need every incoming asset checked against a versioned policy, with bounded actions, "
            "explicit authorization, and reproducible evidence."
        ),
        headline="One GLB in. A policy decision and evidence trail out.",
        promise=(
            "Turn intake from tribal knowledge into an auditable, repeatable exception workflow."
        ),
        intake_eyebrow="Create a policy run",
        intake_title="Bind an asset to a profile",
        profile_label="Versioned project profile",
        upload_label="GLB file",
        upload_hint="GLB 2.0 · static mesh · isolated job workspace",
        submit_label="Run deterministic intake",
        job_kicker="Policy-bound intake",
        job_question="What does the evidence say, and what was authorized?",
        source_label="Registered source",
        candidate_label="Verified artifact",
        findings_heading="Policy findings",
        verification_heading="Invariant audit",
        approval_eyebrow="Interrupt-bound authorization",
        rejection_note=(
            "A rejection is durable job evidence: the normalization action is not executed, "
            "and its unresolved findings remain explicit in verification."
        ),
        landing_template="story.html",
        steps=(
            JourneyStep(
                "01", "Bind policy", "Select a trusted, versioned profile before inspection."
            ),
            JourneyStep(
                "02",
                "Measure facts",
                "Parse structure, transforms, bounds, names, resources, and budgets.",
            ),
            JourneyStep(
                "03",
                "Constrain the plan",
                "Choose only registered repair candidates backed by findings.",
            ),
            JourneyStep(
                "04",
                "Record authorization",
                "Resume the exact Strands interrupt with approve or reject.",
            ),
            JourneyStep(
                "05",
                "Audit the result",
                "Reload, re-plan, verify invariants, and package seven traceable artifacts.",
            ),
        ),
    ),
)


ADVANCED_STORY = StoryDefinition(
    slug="advanced",
    nav_label="Advanced user",
    audience="Advanced technical-art user",
    user_story=(
        "I already know the target policy and want direct access to every supported rule before "
        "I submit an asset."
    ),
    headline="Set the policy, then run the same workflow.",
    promise=(
        "Customize only rules the deterministic engine enforces; authorization and verification "
        "boundaries stay fixed."
    ),
    intake_eyebrow="Advanced policy intake",
    intake_title="Choose or customize the target rules",
    profile_label="Versioned project policy",
    upload_label="GLB file",
    upload_hint="GLB 2.0 · static mesh · isolated job workspace",
    submit_label="Run policy-bound inspection",
    job_kicker="Advanced policy run",
    job_question="What did the frozen policy find and authorize?",
    source_label="Registered source",
    candidate_label="Verified artifact",
    findings_heading="Policy findings",
    verification_heading="Invariant audit",
    approval_eyebrow="Interrupt-bound authorization",
    rejection_note=(
        "A rejection is durable job evidence: normalization does not execute, and unresolved "
        "physical findings remain explicit."
    ),
    landing_template="story.html",
    steps=(
        JourneyStep(
            "01",
            "Review policy",
            "Review the intent-derived family proposal or adjust supported target state.",
        ),
        JourneyStep("02", "Upload model", "Bind one GLB to the frozen policy copy."),
        JourneyStep("03", "Inspect", "Review deterministic facts and policy provenance."),
        JourneyStep("04", "Authorize", "Approve or reject the one grouped physical change."),
        JourneyStep("05", "Package", "Download the verified candidate and evidence trail."),
    ),
)

WORKFLOW_STORIES = (*STORIES, ADVANCED_STORY)
DEFAULT_STORY = STORIES[0]


@dataclass
class WebIntent:
    """One in-memory draft that must be explicitly confirmed before upload."""

    intent_id: str
    target: TargetIntakeContract
    confirmed: AssetIntentProvenance | None = None

    @property
    def original_description(self) -> str:
        """Return the normalized user description."""
        return self.target.description

    @property
    def ready_for_confirmation(self) -> bool:
        """Return whether the minimum target contract is complete."""
        return self.target.ready_for_confirmation

    @property
    def target_use(self) -> AssetTargetUse:
        """Return the complete intended use or fail before confirmation."""
        if self.target.target_use is None:
            raise UploadValidationError("The target use still needs clarification.")
        return self.target.target_use

    @property
    def target_height_cm(self) -> float:
        """Return the complete intended height or fail before confirmation."""
        if self.target.target_height_cm is None:
            raise UploadValidationError("The target height still needs clarification.")
        return self.target.target_height_cm

    @property
    def viewing_use(self) -> AssetViewingUse:
        """Return the complete user-facing viewing context."""
        if self.target.viewing_use is None:
            raise UploadValidationError("The typical viewing use still needs clarification.")
        return self.target.viewing_use

    @property
    def draft_story(self) -> str:
        """Build the reviewable story only from a complete minimum contract."""
        return craft_confirmed_story(
            self.original_description,
            self.target_use,
            self.target_height_cm,
            endpoint=self.target.endpoint,
            endpoint_detail=self.target.endpoint_detail,
            target_dimensions_cm=self.target.target_dimensions_cm,
            viewing_use=self.viewing_use,
        )


@dataclass
class WebJob:
    """In-memory browser session state bound to one isolated on-disk job."""

    job_id: str
    original_filename: str
    intent: AssetIntentProvenance
    target_intake: TargetIntakeContract
    story: StoryDefinition
    profile: FrozenProfile
    root: Path
    source_path: Path
    runtime: AssetShepherdAgent
    latest_result: AgentResult | None = None
    workflow_result: AgentWorkflowResult | None = None
    error: str | None = None
    inspection_acknowledged: bool = False
    accepted: bool = False
    lock: RLock = field(default_factory=RLock, repr=False)

    @property
    def output_dir(self) -> Path:
        """Return the confined deterministic output directory."""
        return self.runtime.job.output_dir

    @property
    def waiting_for_approval(self) -> bool:
        """Return whether this exact Strands job has a pending interrupt."""
        return self.runtime.job.pending_interrupt_id is not None

    @property
    def ready_candidate(self) -> bool:
        """Return whether deterministic verification marked a candidate ready."""
        return bool(
            self.workflow_result is not None
            and self.workflow_result.job_result.ready_candidate
            and (self.output_dir / "repaired.glb").is_file()
        )

    @property
    def state_label(self) -> str:
        """Return a concise user-facing job state."""
        if self.error is not None:
            return "Stopped"
        if self.waiting_for_approval:
            return "Approval needed"
        if self.workflow_result is None:
            return "Working"
        state = self.workflow_result.job_result.state.value
        return state.replace("_", " ").title()

    @property
    def state_class(self) -> str:
        """Return the visual state token used by the template."""
        if self.error is not None:
            return "danger"
        if self.waiting_for_approval:
            return "attention"
        if self.ready_candidate:
            return "success"
        if self.workflow_result is not None:
            return "neutral"
        return "active"

    def approval_card(self) -> ApprovalCard | None:
        """Return the deterministic card only while its interrupt is pending."""
        if not self.waiting_for_approval:
            return None
        return self.runtime.job.approval_card()

    def stages(self) -> tuple[StageView, ...]:
        """Derive the visible stage rail from deterministic state, not model prose."""
        core = self.runtime.job
        facts = (
            ("Intake", "01", True),
            ("Inspect", "02", core.inspection is not None),
            ("Plan", "03", core.selected_plan is not None),
            (
                "Approve",
                "04",
                core.selected_plan is not None
                and (not core.selected_plan.approval_action_ids or core.decisions is not None),
            ),
            (
                "Repair",
                "05",
                core.outcome is not None or bool(core.selected_plan and core.selected_plan.blocked),
            ),
            ("Verify", "06", core.last_verification is not None),
            ("Package", "07", core.result is not None),
        )
        first_pending_seen = False
        stages: list[StageView] = []
        for name, eyebrow, complete in facts:
            if complete:
                status = "complete"
            elif self.error is not None and not first_pending_seen:
                status = "error"
                first_pending_seen = True
            elif not first_pending_seen:
                status = "current"
                first_pending_seen = True
            else:
                status = "pending"
            stages.append(StageView(name=name, eyebrow=eyebrow, status=status))
        return tuple(stages)


def discover_policy_family(project_root: Path) -> PolicyFamilyOption:
    """Load the repository-owned parameterized family for new conversational jobs."""
    source_path = (
        project_root / "src" / "asset_shepherd" / "data" / "unreal_static_game_asset_family.json"
    )
    path = (
        source_path
        if source_path.is_file()
        else _PACKAGE_ROOT / "data" / "unreal_static_game_asset_family.json"
    )
    profile = ProjectProfile.model_validate_json(path.read_text(encoding="utf-8"))
    return PolicyFamilyOption(
        family_id=profile.profile_id,
        path=path.resolve(strict=True),
        profile=profile,
        canonical_sha256=canonical_profile_sha256(profile),
    )


def _policy_proposal(family: PolicyFamilyOption, intent: WebIntent) -> PolicyProposalView:
    """Resolve and format the current agreed intent without requesting duplicate input."""
    resolution = resolve_policy_family(
        family.profile,
        description=intent.original_description,
        target_use=intent.target_use,
        target_height_cm=intent.target_height_cm,
        viewing_use=intent.target.viewing_use or AssetViewingUse.NORMAL_GAMEPLAY,
    )
    complete_summary = _profile_summary(resolution.profile)
    return PolicyProposalView(
        resolution=resolution,
        summary=(complete_summary[0], complete_summary[1], complete_summary[4]),
        review_rules=_profile_review_rules(
            resolution.profile,
            resolution.provenance.canonical_sha256,
        ),
        form_defaults=_profile_form_defaults(resolution.profile),
    )


def _copy_validated_upload(stream: BinaryIO, destination: Path) -> None:
    """Copy one size-bounded GLB stream without trusting its browser filename."""
    total = 0
    header = b""
    with destination.open("xb") as target:
        while chunk := stream.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                raise UploadValidationError("The GLB exceeds the 50 MB local product limit.")
            if len(header) < 4:
                header = (header + chunk)[:4]
            target.write(chunk)
    if total < 12 or header != b"glTF":
        raise UploadValidationError("The upload is not a GLB 2.0 binary container.")


def _public_workflow_error(error: Exception) -> str:
    """Return useful diagnostics without exposing local filesystem or provider details."""
    if isinstance(error, AgentWorkflowError):
        return str(error)
    if isinstance(error, ValueError):
        return str(error)
    return "The workflow stopped unexpectedly. No output is ready."


def _persisted_workflow_error_message(error: str | None) -> str | None:
    """Translate a stored provider failure into concise, actionable product language."""
    if error is None:
        return None
    normalized = " ".join(error.split()).strip()
    for message in PUBLIC_SPEND_MESSAGES:
        if message in normalized:
            return message
    if "Standardized visual sensing" in normalized:
        if "asset is clipped" in normalized:
            return (
                "The evidence renderer cut off part of the asset. I stopped because those "
                "screenshots cannot support a reliable assessment. Your asset and target are saved."
            )
        return (
            "The evidence renderer could not produce usable screenshots. "
            "I stopped repeated attempts; your asset and target are saved."
        )
    if "maximum token limit" in normalized.lower():
        return (
            "I reached this model's response limit before I finished the assessment. "
            "No repair was applied; retry from the saved measurements."
        )
    return "I could not complete this workflow. No output is ready."


def _display_target_height(height_cm: float) -> str:
    """Format target scale in the most readable metric unit for confirmation."""
    if height_cm < 1.0:
        return f"{height_cm * 10:g} mm"
    if height_cm < 100.0:
        return f"{height_cm:g} cm"
    return f"{height_cm / 100:g} m"


def _display_target_bounds(dimensions_cm: tuple[float, float, float]) -> str:
    """Format one tight final-pose X/Y/Z target box in readable metric units."""
    return _display_dimensions_m(
        (dimensions_cm[0] / 100.0, dimensions_cm[1] / 100.0, dimensions_cm[2] / 100.0)
    )


def _display_dimensions_m(dimensions_m: tuple[float, float, float]) -> str:
    """Format X/Y/Z dimensions using one unit appropriate to the whole box."""
    largest = max(abs(value) for value in dimensions_m)
    if largest < 0.01:
        values = tuple(value * 1000.0 for value in dimensions_m)
        unit = "mm"
    elif largest < 1.0:
        values = tuple(value * 100.0 for value in dimensions_m)
        unit = "cm"
    else:
        values = dimensions_m
        unit = "m"
    return f"{values[0]:.3g} x {values[1]:.3g} x {values[2]:.3g} {unit}"


def _uploaded_asset_summary(
    dimensions_m: tuple[float, float, float] | None,
    triangle_count: int | None = None,
) -> str:
    """Describe the objective upload result as one notebook sentence."""
    if dimensions_m is None:
        return "The GLB parsed successfully."
    summary = f"The GLB parsed successfully at {_display_dimensions_m(dimensions_m)}"
    if triangle_count is not None:
        summary += f" with {triangle_count:,} triangles"
    return summary + "."


def _target_notebook_sentence(target: TargetIntakeContract | None) -> str | None:
    """Return the agent's persisted target proposal without regenerating it."""
    if target is None or not target.ready_for_confirmation:
        return None
    assert target.endpoint is not None
    assert target.target_dimensions_cm is not None
    endpoint = (
        target.endpoint_detail
        if target.endpoint is AssetEndpoint.OTHER
        else ENDPOINT_LABELS[target.endpoint]
    )
    bounds = _display_target_bounds(target.target_dimensions_cm)
    return f"I\u2019d shepherd this for {endpoint} within {bounds}."


UNIVERSAL_EXPECTATIONS: tuple[tuple[str, str], ...] = (
    (
        "Readable structure",
        "The file must be a parseable GLB 2.0 container with valid references.",
    ),
    (
        "Sound geometry data",
        "Positions, normals, tangents, UVs, and indices must be finite and internally consistent.",
    ),
    (
        "Supported repairs",
        "Display names and reversible root normalization are available when needed.",
    ),
    (
        "Normalization decision",
        "You decide whether to apply the proposed physical normalization.",
    ),
)

FEEDBACK_CONTEXTS = {
    "general": "Using Asset Shepherd",
    "target-confirmation": "Reviewing the proposed target",
    "rules-and-upload": "Reviewing rules or uploading a GLB",
    "inspection": "Reviewing inspection results",
    "approval": "Deciding whether to approve a repair",
    "download": "Downloading the result",
}

FEEDBACK_REASONS = (
    ("wrong-result", "The result is wrong"),
    ("confusing", "The explanation is confusing"),
    ("blocked", "I can\u2019t continue"),
    ("other", "Something else"),
)


def _safe_feedback_return_path(value: str) -> str:
    """Allow only an app-local path back from the shared feedback page."""
    if (
        not value.startswith("/")
        or value.startswith("//")
        or any(character in value for character in ("\r", "\n"))
    ):
        return "/"
    return value


def _write_feedback_record(
    feedback_root: Path,
    *,
    context: str,
    reference_id: str,
    reason: str,
    note: str,
) -> str:
    """Persist one local feedback record without introducing an external service."""
    feedback_root.mkdir(parents=True, exist_ok=True)
    feedback_id = uuid4().hex
    destination = feedback_root / f"{feedback_id}.json"
    temporary = destination.with_suffix(".tmp")
    payload = {
        "feedback_id": feedback_id,
        "created_at": datetime.now(UTC).isoformat(),
        "context": context,
        "context_label": FEEDBACK_CONTEXTS[context],
        "reference_id": reference_id,
        "reason": reason,
        "note": note,
    }
    temporary.write_text(
        f"{json.dumps(payload, indent=2, sort_keys=True)}\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(destination)
    return feedback_id


BASIS_LABELS = {
    "UNIVERSAL_INVARIANT": "Always-required invariant",
    "FROZEN_PROJECT_POLICY": "Target-specific expectation",
    "OBJECTIVE_SOURCE_DIAGNOSTIC": "Measured source fact",
    "EXTERNAL_CONSUMER_EVIDENCE": "Independent consumer evidence",
}


def _evidence_source_label(evidence: TargetFieldEvidence | None) -> str:
    """Translate typed intake provenance into compact public language."""
    if evidence is None:
        return "No assumption"
    labels = {
        "EXPLICIT_USER_TEXT": "Explicit in your description",
        "MODEL_INFERENCE": "Inferred from your description",
        "USER_CLARIFICATION": "Confirmed by you",
        "DETERMINISTIC_FALLBACK": "Offline test fallback",
    }
    return labels[evidence.source.value]


def _policy_source_label(value: str | None) -> str:
    """Translate one frozen rule source without presenting it as model fact."""
    labels = {
        "CONFIRMED_INTENT": "Confirmed target",
        "DERIVED_INTENT": "Derived from your description",
        "FAMILY_DEFAULT": "Universal project-family rule",
        "USER_OVERRIDE": "Advanced user adjustment",
    }
    return labels.get(value or "", "Always applied")


def _target_expectations(
    target: TargetIntakeContract,
    profile: ProjectProfile,
    policy_sources: Mapping[str, str],
) -> tuple[ExpectationView, ...]:
    """Expose every current target assumption separately from measured GLB facts."""
    if (
        target.target_use is None
        or target.target_dimensions_cm is None
        or target.endpoint is None
        or target.viewing_use is None
    ):
        return ()
    evidence = {item.field: item for item in target.evidence}
    use_evidence = evidence.get("target_use")
    dimensions_evidence = evidence.get("target_dimensions_cm")
    endpoint_evidence = evidence.get("endpoint")
    viewing_evidence = evidence.get("viewing_use")
    endpoint_label = (
        target.endpoint_detail
        if target.endpoint is AssetEndpoint.OTHER
        else ENDPOINT_LABELS[target.endpoint]
    )
    dimensions_m = tuple(value / 100.0 for value in target.target_dimensions_cm)
    full_static = target.target_use is AssetTargetUse.STATIC_GAME_ASSET
    orientation_value = (
        "Y-up; propose upright normalization if the measured dominant axis disagrees"
        if profile.orientation.require_y_up_geometry
        else "No target-specific upright requirement"
    )
    grounding_value = (
        f"Grounded within {profile.orientation.ground_tolerance_cm:g} cm"
        if profile.orientation.require_ground_contact
        else "No ground-contact requirement"
    )
    return (
        ExpectationView(
            label="Intended use",
            value=TARGET_USE_LABELS[target.target_use].capitalize(),
            source=_evidence_source_label(use_evidence),
            detail=use_evidence.evidence if use_evidence else "",
        ),
        ExpectationView(
            label="Next tool",
            value=endpoint_label or "Other",
            source=_evidence_source_label(endpoint_evidence),
            detail=endpoint_evidence.evidence if endpoint_evidence else "",
        ),
        ExpectationView(
            label="What happens here",
            value=(
                "Full static inspect → repair → verify workflow"
                if full_static
                else "Static inspection and handoff; no rigging or animation repair"
            ),
            source="Based on the model you described",
            detail=(
                "I can complete the static repair workflow."
                if full_static
                else (
                    "I can inspect the static mesh, but rigging and animation stay in your "
                    "creation tool."
                )
            ),
        ),
        ExpectationView(
            label="Typical viewing",
            value={
                AssetViewingUse.CLOSE_UP_SHOWCASE: "Hero / close-up",
                AssetViewingUse.NORMAL_GAMEPLAY: "Normal gameplay",
                AssetViewingUse.SMALL_DISTANT_REPEATED: "Background / repeated",
            }[target.viewing_use],
            source=_evidence_source_label(viewing_evidence),
            detail=(
                "Asset Shepherd uses this nontechnical choice when deciding whether mesh "
                "simplification is worth proposing. You can decline that proposal."
            ),
        ),
        ExpectationView(
            label="Tight X/Y/Z bounds",
            value=(f"{dimensions_m[0]:g} x {dimensions_m[1]:g} x {dimensions_m[2]:g} m"),
            source=_evidence_source_label(dimensions_evidence),
            detail=dimensions_evidence.evidence if dimensions_evidence else "",
        ),
        ExpectationView(
            label="Orientation",
            value=orientation_value,
            source=_policy_source_label(policy_sources.get("orientation.require_y_up_geometry")),
            detail="I\u2019ll measure the GLB before proposing any rotation.",
        ),
        ExpectationView(
            label="Grounding",
            value=grounding_value,
            source=_policy_source_label(policy_sources.get("orientation.require_ground_contact")),
            detail="I\u2019ll compare the asset\u2019s lowest point with the ground plane.",
        ),
        ExpectationView(
            label="Assembly",
            value=(
                f"{target.expected_piece_count} expected semantic "
                f"{'piece' if target.expected_piece_count == 1 else 'pieces'}"
            ),
            source="Inferred from your description",
            detail=target.expected_piece_count_evidence,
        ),
    )


def _expectation_groups(
    target: TargetIntakeContract,
    profile: ProjectProfile,
    policy_sources: Mapping[str, str],
) -> tuple[ExpectationGroupView, ...]:
    """Compress the review into three conclusions with details on demand."""
    expectations = _target_expectations(target, profile, policy_sources)
    if len(expectations) != 8:
        return ()
    assert target.target_dimensions_cm is not None
    placement = [
        _display_target_bounds(target.target_dimensions_cm),
        "Y-up" if profile.orientation.require_y_up_geometry else "orientation unrestricted",
        "grounded" if profile.orientation.require_ground_contact else "ground contact optional",
    ]
    piece_label = "piece" if target.expected_piece_count == 1 else "pieces"
    return (
        ExpectationGroupView(
            label="Purpose",
            summary=f"{expectations[0].value} → {expectations[1].value}",
            items=expectations[0:4],
        ),
        ExpectationGroupView(
            label="Scale and pose",
            summary=" · ".join(placement),
            items=expectations[4:7],
        ),
        ExpectationGroupView(
            label="Structure",
            summary=f"{target.expected_piece_count} expected semantic {piece_label}",
            items=(expectations[7],),
        ),
    )


class WebJobStore:
    """Thread-safe in-process job registry with isolated filesystem workspaces."""

    def __init__(
        self,
        work_root: Path,
        family: PolicyFamilyOption,
        intake_analyzer: TargetIntakeAnalyzer,
        max_agent_turns: int = 5,
    ) -> None:
        """Create a registry rooted in an ignored, caller-controlled directory."""
        self.work_root = work_root.resolve(strict=False)
        self.family = family
        self.intake_analyzer = intake_analyzer
        if not 1 <= max_agent_turns <= 50:
            raise ValueError("Agent turn limit must be between 1 and 50")
        self.max_agent_turns = max_agent_turns
        self._intents: dict[str, WebIntent] = {}
        self._jobs: dict[str, WebJob] = {}
        self._lock = RLock()

    def create_intent(
        self,
        description: str,
    ) -> WebIntent:
        """Extract and retain one minimum-information target contract."""
        target = self.intake_analyzer.analyze(description)
        intent_id = uuid4().hex
        intent = WebIntent(
            intent_id=intent_id,
            target=target,
        )
        with self._lock:
            self._intents[intent_id] = intent
        return intent

    def clarify_intent(
        self,
        intent: WebIntent,
        *,
        target_use_value: str | None,
        target_height_m: str | None,
        target_x_m: str | None = None,
        target_y_m: str | None = None,
        target_z_m: str | None = None,
        viewing_use_value: str | None = None,
    ) -> WebIntent:
        """Fill only fields that the minimum target contract could not extract."""
        with self._lock:
            if intent.confirmed is not None:
                raise UploadValidationError("This target story is already confirmed.")
            try:
                intent.target = clarify_target_intake(
                    intent.target,
                    target_use_value=target_use_value,
                    target_height_m=target_height_m,
                    target_x_m=target_x_m,
                    target_y_m=target_y_m,
                    target_z_m=target_z_m,
                    viewing_use_value=viewing_use_value,
                )
            except ValueError as error:
                raise UploadValidationError(str(error)) from error
            return intent

    def revise_intent(
        self,
        intent: WebIntent,
        *,
        description: str,
    ) -> WebIntent:
        """Reinterpret an edited natural-language description before confirmation."""
        with self._lock:
            if intent.confirmed is not None:
                raise UploadValidationError("This target story is already confirmed.")
            try:
                intent.target = self.intake_analyzer.analyze(description)
            except ValueError as error:
                raise UploadValidationError(str(error)) from error
            return intent

    def get_intent(self, intent_id: str) -> WebIntent | None:
        """Return a known intent draft without accepting caller-controlled paths."""
        with self._lock:
            return self._intents.get(intent_id)

    def confirm_intent(
        self,
        intent: WebIntent,
        *,
        viewing_use_value: str | None = None,
    ) -> AssetIntentProvenance:
        """Freeze the exact reviewed story once; repeated confirmation is idempotent."""
        with self._lock:
            if not intent.ready_for_confirmation:
                raise UploadValidationError(
                    "Answer the remaining target questions before confirming this story."
                )
            if intent.confirmed is None:
                try:
                    intent.target = confirm_target_viewing_use(intent.target, viewing_use_value)
                except ValueError as error:
                    raise UploadValidationError(str(error)) from error
                intent.confirmed = build_asset_intent(
                    intent.original_description,
                    intent.target_use,
                    intent.target_height_cm,
                    expected_piece_count=intent.target.expected_piece_count,
                    expected_piece_count_evidence=(intent.target.expected_piece_count_evidence),
                    intent_id=intent.intent_id,
                    endpoint=intent.target.endpoint,
                    endpoint_detail=intent.target.endpoint_detail,
                    target_dimensions_cm=intent.target.target_dimensions_cm,
                    viewing_use=(intent.target.viewing_use or AssetViewingUse.NORMAL_GAMEPLAY),
                )
            return intent.confirmed

    def create(
        self,
        original_filename: str,
        story: StoryDefinition,
        intent: AssetIntentProvenance,
        target_intake: TargetIntakeContract,
        stream: BinaryIO,
        *,
        profile_mode: str = "resolved",
        custom_values: Mapping[str, str | None] | None = None,
    ) -> WebJob:
        """Validate, isolate, start, and retain one browser-submitted job."""
        if Path(original_filename).suffix.lower() != ".glb":
            raise UploadValidationError("Choose exactly one file with a .glb extension.")
        validate_asset_intent(intent)
        if (
            not target_intake.ready_for_confirmation
            or target_intake.description != intent.original_description
            or target_intake.target_use is not intent.target_use
            or target_intake.target_height_cm != intent.target_height_cm
        ):
            raise UploadValidationError(
                "The minimum target contract does not match the agreed story."
            )
        if profile_mode == "resolved":
            user_overrides = None
        elif profile_mode == "custom":
            if custom_values is None:
                raise UploadValidationError("Complete the custom policy before uploading.")
            user_overrides = _custom_overrides(custom_values)
        else:
            raise UploadValidationError(
                "Use the proposed rules or a validated advanced adjustment."
            )
        try:
            resolution = resolve_policy_family(
                self.family.profile,
                description=intent.original_description,
                target_use=intent.target_use,
                target_height_cm=intent.target_height_cm,
                viewing_use=intent.viewing_use or AssetViewingUse.NORMAL_GAMEPLAY,
                user_overrides=user_overrides,
            )
        except ValueError as error:
            raise UploadValidationError(str(error)) from error
        resolved_profile = resolution.profile
        policy_provenance = resolution.provenance
        job_id = uuid4().hex
        job_root = self.work_root / job_id
        job_root.mkdir(parents=True, exist_ok=False)
        source_path = job_root / "source.glb"
        profile_path = job_root / "profile.json"
        intent_path = job_root / "intent.json"
        target_intake_path = job_root / "target_intake.json"
        try:
            _copy_validated_upload(stream, source_path)
            profile_payload = json.dumps(
                resolved_profile.model_dump(mode="json"),
                indent=2,
                sort_keys=True,
            )
            profile_path.write_text(
                f"{profile_payload}\n",
                encoding="utf-8",
                newline="\n",
            )
            intent_payload = json.dumps(intent.model_dump(mode="json"), indent=2, sort_keys=True)
            intent_path.write_text(f"{intent_payload}\n", encoding="utf-8", newline="\n")
            target_intake_payload = json.dumps(
                target_intake.model_dump(mode="json"),
                indent=2,
                sort_keys=True,
            )
            target_intake_path.write_text(
                f"{target_intake_payload}\n",
                encoding="utf-8",
                newline="\n",
            )
        except Exception:
            source_path.unlink(missing_ok=True)
            profile_path.unlink(missing_ok=True)
            intent_path.unlink(missing_ok=True)
            target_intake_path.unlink(missing_ok=True)
            job_root.rmdir()
            raise
        frozen_profile = FrozenProfile(
            profile_id=resolved_profile.profile_id,
            name=resolution.display_name,
            path=profile_path,
            policy_provenance=policy_provenance,
        )
        agent_mode = workflow_model_available()
        runtime_job = AgentJob(
            source_path,
            profile_path,
            job_root / "output",
            profile_policy=policy_provenance,
            asset_intent=intent,
            agent_orchestrated=agent_mode,
            max_turns=self.max_agent_turns,
        )
        runtime = build_live_agent(runtime_job) if agent_mode else build_scripted_agent(runtime_job)
        job = WebJob(
            job_id=job_id,
            original_filename=Path(original_filename).name,
            intent=intent,
            target_intake=target_intake,
            story=story,
            profile=frozen_profile,
            root=job_root,
            source_path=source_path,
            runtime=runtime,
        )
        with self._lock:
            self._jobs[job_id] = job
        self._start(job)
        return job

    def _start(self, job: WebJob) -> None:
        """Run one Strands job through completion or its first native interrupt."""
        with job.lock:
            try:
                self._settle_model_turn(job, job.runtime.start())
            except Exception as error:
                job.error = _public_workflow_error(error)

    @staticmethod
    def _settle_model_turn(job: WebJob, result: AgentResult) -> None:
        """Boundedly recover a provider early-end, then interrupt or complete the turn."""
        runtime_job = job.runtime.job
        if runtime_job.agent_orchestrated:
            if (
                result.stop_reason != "interrupt"
                and runtime_job.inspection is not None
                and runtime_job.agent_assessment is None
            ):
                result = job.runtime.retry_incomplete_planning()
            if (
                result.stop_reason != "interrupt"
                and runtime_job.selected_plan is not None
                and runtime_job.outcome is None
                and runtime_job.selected_plan.approval_action_ids
            ):
                result = job.runtime.continue_prepared_plan()
            if (
                result.stop_reason != "interrupt"
                and runtime_job.result is None
                and runtime_job.outcome is not None
                and runtime_job.outcome.executed_action_ids
            ):
                result = job.runtime.continue_incomplete_turn()
        job.latest_result = result
        if result.stop_reason != "interrupt":
            job.workflow_result = job.runtime.complete(result)

    def get(self, job_id: str) -> WebJob | None:
        """Return a known in-process job without inspecting arbitrary disk paths."""
        with self._lock:
            return self._jobs.get(job_id)

    def resume(self, job: WebJob, interrupt_id: str, approved: bool) -> None:
        """Resume the exact pending Strands interrupt and finalize its artifacts."""
        with job.lock:
            if job.error is not None:
                raise AgentWorkflowError("A stopped job cannot be resumed")
            result = job.runtime.resume(interrupt_id, approved=approved)
            self._settle_model_turn(job, result)

    def continue_after_feedback(self, job: WebJob, feedback: str) -> None:
        """Advance the current candidate into a fresh bounded agent turn."""
        with job.lock:
            if job.error is not None:
                raise AgentWorkflowError("A stopped job cannot continue")
            if job.waiting_for_approval:
                raise AgentWorkflowError("Resolve the current approval before continuing")
            result = job.runtime.continue_after_feedback(feedback)
            job.workflow_result = None
            job.inspection_acknowledged = False
            job.accepted = False
            self._settle_model_turn(job, result)


def _finding_groups(job: WebJob) -> tuple[tuple[str, tuple[Finding, ...]], ...]:
    """Group structured findings in decision-oriented severity order."""
    inspection = job.runtime.job.inspection
    if inspection is None:
        return ()
    order = (Severity.BLOCKER, Severity.ERROR, Severity.WARNING, Severity.INFO)
    groups: list[tuple[str, tuple[Finding, ...]]] = []
    for severity in order:
        findings = tuple(finding for finding in inspection.findings if finding.severity is severity)
        if findings:
            groups.append((severity.value, findings))
    return tuple(groups)


_SIZE_POSE_CODES = {"HEIGHT_OUT_OF_RANGE", "ORIENTATION_NOT_Y_UP", "NOT_GROUNDED"}
_TOPOLOGY_CODES = {
    "UNSUPPORTED_REPAIR_FEATURES",
    "MALFORMED_GEOMETRY_ATTRIBUTES",
    "DEGENERATE_TRIANGLES_DETECTED",
    "MESH_TOPOLOGY_DEFECTS_DETECTED",
    "ATTRIBUTE_SAFE_DUPLICATE_TUPLES_DETECTED",
    "UNUSED_VERTEX_DATA_DETECTED",
    "DISCONNECTED_COMPONENTS_DETECTED",
    "VERTEX_CACHE_LOCALITY_WARNING",
    "TRIANGLE_BUDGET_EXCEEDED",
}
_MATERIAL_CODES = {
    "MATERIAL_BUDGET_EXCEEDED",
    "TEXTURE_BUDGET_EXCEEDED",
    "TEXTURE_DIMENSION_EXCEEDED",
    "IMAGE_UNREADABLE",
}
_NAME_CODES = {
    "NODE_NAME_MISSING",
    "NODE_NAME_INVALID",
    "NODE_NAME_DUPLICATE",
    "MESH_NAME_MISSING",
    "MESH_NAME_INVALID",
    "MESH_NAME_DUPLICATE",
}


def _supported_component_recovery(core: AgentJob) -> bool:
    """Return whether a blocked pass can safely revisit an exact component selection."""
    assessment = core.agent_assessment
    intent = core.asset_intent
    diagnostics = core.inspection.diagnostics if core.inspection is not None else None
    if (
        assessment is None
        or assessment.disposition is not AgentDisposition.RETURN_TO_CREATION_TOOL
        or intent is None
        or diagnostics is None
    ):
        return False
    affected = tuple(
        primitive
        for primitive in diagnostics.primitives
        if len(primitive.disconnected_components) > 1
    )
    return bool(
        len(affected) == 1
        and affected[0].component_removal_safe
        and len(affected[0].disconnected_components) != intent.expected_piece_count
    )


def _validate_component_choices(
    components: tuple[ComponentProposalView, ...], choices: dict[str, str]
) -> None:
    """Reject an empty retained selection before dispatching any model work."""
    known = {component.component_id for component in components}
    if set(choices) - known:
        raise HostedWorkspaceError(
            "A component selection is no longer available. Reload this page."
        )
    if components and not any(
        choices.get(component.component_id, "accept") != "request_remove"
        and not (
            component.proposed_removal and choices.get(component.component_id, "accept") == "accept"
        )
        for component in components
    ):
        raise HostedWorkspaceError("Keep at least one component to continue.")


def _inspection_checks(core: AgentJob) -> tuple[InspectionCheckView, ...]:
    """Build one non-repeating table of findings and phase-aware actions."""
    inspection = core.inspection
    plan = core.selected_plan
    assessment = core.agent_assessment
    after_action = core.outcome is not None
    action_heading = "Action taken" if after_action else "Proposed action"
    if inspection is None:
        return (
            InspectionCheckView(
                "GLB structure",
                "checking",
                "Checking",
                "Inspection is running.",
                "—",
                action_heading=action_heading,
            ),
        )

    executed_ids: set[str] = (
        set(core.outcome.executed_action_ids) if core.outcome is not None else set()
    )
    rejected_ids: set[str] = (
        set(core.outcome.rejected_action_ids) if core.outcome is not None else set()
    )
    verification_checks = (
        {check.code: check.status for check in core.last_verification.checks}
        if core.last_verification is not None
        else {}
    )
    verification_passed = bool(
        core.last_verification is not None
        and core.last_verification.state
        in {
            VerificationState.PASSED_PROJECT_READY,
            VerificationState.PASSED_WITH_REMAINING_WARNINGS,
        }
    )
    verification_incomplete = after_action and core.last_verification is None

    def check_passed(code: str) -> bool:
        return verification_checks.get(code) is CheckStatus.PASS

    def has_attention(relevant_codes: set[str]) -> bool:
        return any(
            finding.code in relevant_codes and finding.severity is not Severity.INFO
            for finding in inspection.findings
        )

    size_pose_attention = bool(
        assessment
        and (
            assessment.scale_to_confirmed_height
            or assessment.rotation_degrees != 0
            or assessment.ground_to_y_zero
            or assessment.pivot_target != "PRESERVE"
        )
    )
    diagnostic_primitives = inspection.diagnostics.primitives if inspection.diagnostics else ()
    protected_duplicates = sum(
        primitive.protected_duplicate_count for primitive in diagnostic_primitives
    )
    projected_boundaries = sum(
        primitive.virtual_weld_boundary_edge_count for primitive in diagnostic_primitives
    )
    projected_non_manifold = sum(
        primitive.virtual_weld_non_manifold_edge_count for primitive in diagnostic_primitives
    )
    projected_winding = sum(
        primitive.virtual_weld_inconsistent_winding_edge_count
        for primitive in diagnostic_primitives
    )
    affected_component_counts = tuple(
        len(primitive.disconnected_components)
        for primitive in diagnostic_primitives
        if len(primitive.disconnected_components) > 1
    )
    selectable_component_count = sum(affected_component_counts)
    semantic_component_count = (
        affected_component_counts[0] if len(affected_component_counts) == 1 else None
    )
    component_removal_available = _supported_component_recovery(core)
    degenerate_triangles = sum(
        primitive.degenerate_triangle_count for primitive in diagnostic_primitives
    )
    unused_positions = sum(primitive.unused_position_count for primitive in diagnostic_primitives)
    source_triangle_count = inspection.geometry.triangle_count if inspection.geometry else None
    triangle_soft_cap = core.profile.budgets.max_triangles
    viewing_use = core.asset_intent.viewing_use if core.asset_intent is not None else None
    viewing_use_name = "selected use case"
    if viewing_use is not None:
        viewing_use_name = {
            AssetViewingUse.CLOSE_UP_SHOWCASE: "hero / close-up",
            AssetViewingUse.NORMAL_GAMEPLAY: "normal gameplay",
            AssetViewingUse.SMALL_DISTANT_REPEATED: "background / repeated",
        }[viewing_use]
    protected_attributes = sorted(
        {
            attribute
            for primitive in diagnostic_primitives
            for attribute in primitive.protected_attribute_conflicts
        }
    )

    normalization_action = ""
    normalization_id: str | None = None
    mesh_names: list[str] = []
    node_names: list[str] = []
    name_ids: list[str] = []
    weld_action = ""
    weld_ids: list[str] = []
    cleanup_action = ""
    cleanup_ids: list[str] = []
    component_action = ""
    component_ids: list[str] = []
    simplification_action = ""
    simplification_ids: list[str] = []
    simplification_source_triangles = 0
    if plan is not None:
        for candidate in plan.candidates:
            payload = candidate.payload
            if isinstance(payload, NormalizationPayload):
                normalization_id = candidate.id
                requested: list[str] = []
                if assessment is not None and assessment.scale_to_confirmed_height:
                    requested.append("fit proportionally")
                if assessment is not None and assessment.rotation_degrees:
                    requested.append(
                        f"rotate {assessment.rotation_axis} {assessment.rotation_degrees:+d}°"
                    )
                if assessment is not None and assessment.ground_to_y_zero:
                    requested.append("ground at Y=0")
                if assessment is not None and assessment.pivot_target == "BOUNDS_CENTER":
                    requested.append("center pivot in the bounds")
                elif (
                    assessment is not None and assessment.pivot_target == "FOOTPRINT_CENTER_BOTTOM"
                ):
                    requested.append("center pivot on the footprint")
                elif assessment is not None and assessment.pivot_target == "MEASURED_ANCHOR":
                    requested.append(
                        f"move the {assessment.pivot_anchor_label or 'measured anchor'} to origin"
                    )
                if not requested:
                    requested = [component.component for component in payload.components]
                normalization_action = (
                    f"Approval required — {', '.join(requested)}; "
                    f"{_display_dimensions_m(payload.before_bounds.dimensions_m)} → "
                    f"{_display_dimensions_m(payload.expected_after_bounds.dimensions_m)}"
                )
                continue
            if isinstance(payload, WeldPayload):
                weld_ids.append(candidate.id)
                merge_count = sum(primitive.merge_count for primitive in payload.primitives)
                weld_action = (
                    f"Automatic — compact {merge_count:,} byte-identical vertex tuple"
                    f"{'s' if merge_count != 1 else ''}."
                )
                continue
            if isinstance(payload, DegenerateGeometryPayload):
                cleanup_ids.append(candidate.id)
                removed_triangles = sum(
                    primitive.removed_degenerate_triangle_count for primitive in payload.primitives
                )
                removed_positions = sum(
                    primitive.removed_unused_position_count for primitive in payload.primitives
                )
                changes: list[str] = []
                if removed_triangles:
                    changes.append(
                        f"remove {removed_triangles:,} zero-area triangle"
                        f"{'s' if removed_triangles != 1 else ''}"
                    )
                if removed_positions:
                    changes.append(
                        f"compact {removed_positions:,} unreferenced vertex tuple"
                        f"{'s' if removed_positions != 1 else ''}"
                    )
                cleanup_action = f"Approval required — {' and '.join(changes)}."
                continue
            if isinstance(payload, ComponentRemovalPayload):
                component_ids.extend(
                    component_id
                    for primitive in payload.primitives
                    for component_id in primitive.removed_component_ids
                )
                removed_triangles = sum(
                    primitive.removed_triangle_count for primitive in payload.primitives
                )
                component_action = (
                    f"Approval required — remove {len(component_ids)} labeled component"
                    f"{'s' if len(component_ids) != 1 else ''} "
                    f"({removed_triangles:,} triangles)."
                )
                continue
            if isinstance(payload, MeshSimplificationPayload):
                simplification_ids.append(candidate.id)
                simplification_source_triangles = payload.source_triangle_count
                simplification_action = (
                    f"Approval required — optimize {payload.source_triangle_count:,} toward "
                    f"the {viewing_use_name} soft cap of {payload.target_triangle_count:,} "
                    "triangles; protect small components and preserve the original."
                )
                continue
            before_name = payload.before_name or "(unnamed)"
            item = f"“{before_name}” → “{payload.after_name}”"
            if candidate.kind is RepairKind.RENAME_MESH:
                mesh_names.append(item)
                name_ids.append(candidate.id)
            elif candidate.kind is RepairKind.RENAME_NODE:
                node_names.append(item)
                name_ids.append(candidate.id)

    geometry = inspection.geometry
    measured_dimensions = (
        _display_dimensions_m(geometry.bounds.dimensions_m)
        if geometry is not None
        else "unavailable"
    )
    target_dimensions = (
        _display_target_bounds(core.asset_intent.target_dimensions_cm)
        if core.asset_intent is not None and core.asset_intent.target_dimensions_cm is not None
        else "unspecified"
    )
    agent_requires_creation_tool = bool(
        assessment and assessment.disposition is AgentDisposition.RETURN_TO_CREATION_TOOL
    )
    expected_piece_count = (
        core.asset_intent.expected_piece_count if core.asset_intent is not None else None
    )
    assessment_evidence = " ".join(assessment.evidence).casefold() if assessment else ""
    component_mismatch = bool(
        agent_requires_creation_tool
        and expected_piece_count is not None
        and semantic_component_count is not None
        and semantic_component_count != expected_piece_count
        and any(
            phrase in assessment_evidence
            for phrase in ("connected component", "distinct", "extra visible", "separate")
        )
    )
    structure_blocked = bool(
        inspection.repair_eligibility is not RepairEligibility.ELIGIBLE_STATIC_MESH
        or agent_requires_creation_tool
    )
    structure_status = (
        "attention"
        if component_mismatch and component_removal_available
        else ("blocked" if structure_blocked else "pass")
    )
    structure_label = (
        "Agent stopped"
        if component_mismatch and component_removal_available
        else "Cannot repair"
        if agent_requires_creation_tool
        else ("Inspection only" if structure_blocked else "Pass")
    )
    if component_mismatch and component_removal_available:
        structure_action = (
            "No labeled components were selected in this pass — refine the current iteration "
            "to review a removal proposal."
        )
    elif component_mismatch:
        structure_action = "Cannot repair — this GLB layout is not eligible for component removal."
    elif agent_requires_creation_tool:
        structure_action = "Cannot repair — return to the creation tool."
    else:
        structure_action = "No repair available for this GLB." if structure_blocked else "—"

    size_warning = size_pose_attention or has_attention(_SIZE_POSE_CODES)
    size_status = "attention" if size_warning else "pass"
    size_label = (
        "Needs approval" if normalization_action else ("Attention" if size_warning else "Pass")
    )

    topology_warning = has_attention(_TOPOLOGY_CODES) or bool(
        weld_action or cleanup_action or component_action or simplification_action
    )
    topology_status = "attention" if topology_warning else "pass"
    topology_label = (
        "Needs approval"
        if cleanup_action or component_action or simplification_action
        else "Automatic"
        if weld_action
        else ("Report only" if topology_warning else "Pass")
    )
    if simplification_action:
        topology_action = simplification_action
    elif component_action:
        topology_action = component_action
    elif cleanup_action:
        topology_action = cleanup_action
    elif weld_action:
        topology_action = weld_action
    elif degenerate_triangles or unused_positions:
        unresolved: list[str] = []
        if degenerate_triangles:
            unresolved.append(
                f"{degenerate_triangles:,} degenerate triangle"
                f"{'s' if degenerate_triangles != 1 else ''}"
            )
        if unused_positions:
            unresolved.append(
                f"{unused_positions:,} unused vertex tuple{'s' if unused_positions != 1 else ''}"
            )
        topology_action = f"Report only — {' and '.join(unresolved)} not changed."
    elif protected_duplicates and topology_warning:
        seam_names = ", ".join(protected_attributes) or "vertex attribute"
        topology_action = (
            f"Report only — no weld; {protected_duplicates:,} coincident positions preserve "
            f"{seam_names} seams."
        )
    elif topology_warning:
        topology_action = "Report only — no supported topology change."
    else:
        topology_action = "—"

    material_warning = has_attention(_MATERIAL_CODES)
    material_status = "attention" if material_warning else "pass"
    material_label = "Report only" if material_warning else "Pass"
    material_action = "Report only — no material or texture change." if material_warning else "—"

    name_items = mesh_names + node_names
    name_warning = has_attention(_NAME_CODES) or bool(name_items)
    name_status = "attention" if name_warning else "pass"
    name_label = "Automatic" if name_items else ("Attention" if name_warning else "Pass")
    name_action = f"Automatic — {'; '.join(name_items)}" if name_items else "—"

    if after_action:
        if normalization_id is not None and normalization_id in executed_ids:
            normalized_detail = normalization_action.removeprefix("Approval required — ")
            if verification_passed:
                size_status = "repaired"
                size_label = "Addressed"
                normalization_action = f"Applied — {normalized_detail}"
            elif verification_incomplete:
                size_status = "attention"
                size_label = "Verification interrupted"
                normalization_action = (
                    f"Applied — verification has not completed; {normalized_detail}"
                )
            else:
                size_status = "attention"
                size_label = "Needs review"
                normalization_action = (
                    f"Attempted — verification did not confirm {normalized_detail}"
                )
        elif normalization_id is not None and normalization_id in rejected_ids:
            size_status = "attention"
            size_label = "Unresolved"
            normalization_action = "Not applied — rejected."
        elif size_warning:
            normalization_action = "No change — report only."

        if weld_ids and all(candidate_id in executed_ids for candidate_id in weld_ids):
            weld_detail = weld_action.removeprefix("Automatic — ")
            if check_passed("ATTRIBUTE_SAFE_WELD_EXHAUSTED"):
                topology_status = "repaired"
                topology_label = "Addressed"
                topology_action = f"Applied — {weld_detail}"
            elif verification_incomplete:
                topology_status = "attention"
                topology_label = "Verification interrupted"
                topology_action = f"Applied — verification has not completed; {weld_detail}"
            else:
                topology_status = "attention"
                topology_label = "Needs review"
                topology_action = f"Attempted — verification did not confirm {weld_detail}"
        elif cleanup_ids and all(candidate_id in executed_ids for candidate_id in cleanup_ids):
            cleanup_detail = cleanup_action.removeprefix("Approval required — ")
            if check_passed("DEGENERATE_GEOMETRY_CLEANUP_CONFIRMED"):
                topology_status = "repaired"
                topology_label = "Addressed"
                topology_action = f"Applied — {cleanup_detail}"
            elif verification_incomplete:
                topology_status = "attention"
                topology_label = "Verification interrupted"
                topology_action = f"Applied — verification has not completed; {cleanup_detail}"
            else:
                topology_status = "attention"
                topology_label = "Needs review"
                topology_action = f"Attempted — verification did not confirm {cleanup_detail}"
        elif cleanup_ids and any(candidate_id in rejected_ids for candidate_id in cleanup_ids):
            topology_status = "attention"
            topology_label = "Unresolved"
            topology_action = "Not applied — rejected."
        elif "remove-disconnected-components-v1" in executed_ids and component_action:
            component_detail = component_action.removeprefix("Approval required — ")
            if check_passed("DISCONNECTED_COMPONENT_REMOVAL_CONFIRMED"):
                topology_status = "repaired"
                topology_label = "Addressed"
                topology_action = f"Applied — {component_detail}"
            elif verification_incomplete:
                topology_status = "attention"
                topology_label = "Verification interrupted"
                topology_action = (
                    "Applied — verification has not completed for the component selection."
                )
            else:
                topology_status = "attention"
                topology_label = "Needs review"
                topology_action = (
                    "Attempted — verification did not confirm the component selection."
                )
        elif "remove-disconnected-components-v1" in rejected_ids and component_action:
            topology_status = "attention"
            topology_label = "Unresolved"
            topology_action = "Not applied — rejected."
        elif simplification_ids and all(
            candidate_id in executed_ids for candidate_id in simplification_ids
        ):
            if check_passed("MESH_SIMPLIFICATION_REDUCED_TRIANGLES"):
                actual_triangles = (
                    next(
                        (
                            check.actual
                            for check in core.last_verification.checks
                            if check.code == "MESH_SIMPLIFICATION_REDUCED_TRIANGLES"
                        ),
                        None,
                    )
                    if core.last_verification is not None
                    else None
                )
                candidate_bytes = (
                    next(
                        (
                            check.actual
                            for check in core.last_verification.checks
                            if check.code == "MESH_SIMPLIFICATION_FILE_SIZE_REDUCED"
                        ),
                        None,
                    )
                    if core.last_verification is not None
                    else None
                )
                topology_status = "repaired"
                topology_label = "Addressed"
                verified_triangles = actual_triangles if isinstance(actual_triangles, int) else 0
                topology_action = (
                    f"Mesh optimized — {simplification_source_triangles:,} → "
                    f"{verified_triangles:,} triangles"
                )
                if isinstance(candidate_bytes, int):
                    topology_action += (
                        f"; file size {inspection.package.byte_size / (1024 * 1024):.1f} MB → "
                        f"{candidate_bytes / (1024 * 1024):.1f} MB"
                    )
                topology_action += ". Original preserved."
            elif verification_incomplete:
                topology_status = "attention"
                topology_label = "Verification interrupted"
                topology_action = "Applied — mesh optimization verification has not completed."
            else:
                topology_status = "attention"
                topology_label = "Needs review"
                topology_action = "Attempted — verification did not confirm mesh optimization."
        elif simplification_ids and any(
            candidate_id in rejected_ids for candidate_id in simplification_ids
        ):
            topology_status = "attention"
            topology_label = "Original preserved"
            topology_action = "Not applied — the user chose to preserve original detail."
        elif topology_warning:
            topology_action = topology_action.replace("Report only —", "No change —", 1)

        if material_warning:
            material_action = "No change — report only."

        if name_ids and all(candidate_id in executed_ids for candidate_id in name_ids):
            name_detail = name_action.removeprefix("Automatic — ")
            if check_passed("NAMES_VALID_AND_UNIQUE"):
                name_status = "repaired"
                name_label = "Addressed"
                name_action = f"Applied — {name_detail}"
            elif verification_incomplete:
                name_status = "attention"
                name_label = "Verification interrupted"
                name_action = f"Applied — verification has not completed; {name_detail}"
            else:
                name_status = "attention"
                name_label = "Needs review"
                name_action = f"Attempted — verification did not confirm {name_detail}"
        elif name_warning:
            name_action = "No change — names remain unresolved."

    if source_triangle_count is not None and viewing_use is not None and not simplification_ids:
        if source_triangle_count <= triangle_soft_cap:
            complexity_action = (
                f"Mesh detail preserved — {source_triangle_count:,} triangles is within the "
                f"{triangle_soft_cap:,}-triangle {viewing_use_name} soft cap."
            )
        elif assessment is None:
            complexity_action = (
                f"Mesh complexity is still being evaluated — {source_triangle_count:,} "
                f"triangles exceeds the {triangle_soft_cap:,}-triangle {viewing_use_name} "
                "soft cap."
            )
        elif "SIMPLIFY_MESH" in assessment.deferred_repair_kinds:
            complexity_action = (
                f"Mesh optimization is queued as the next separate refinement — "
                f"{source_triangle_count:,} triangles exceeds the {triangle_soft_cap:,}-triangle "
                f"{viewing_use_name} soft cap."
            )
        elif any(primitive.mesh_simplification_safe for primitive in diagnostic_primitives):
            complexity_action = (
                f"Mesh detail preserved this turn — {source_triangle_count:,} triangles exceeds "
                f"the {triangle_soft_cap:,}-triangle {viewing_use_name} soft cap, but the agent "
                "did not propose optimization."
            )
        else:
            complexity_action = (
                f"Mesh optimization unavailable — {source_triangle_count:,} triangles exceeds "
                f"the {triangle_soft_cap:,}-triangle {viewing_use_name} soft cap, but this GLB "
                "layout cannot be simplified safely."
            )
        topology_action = (
            complexity_action
            if topology_action == "—"
            else f"{topology_action} {complexity_action}"
        )

    topology_facts: list[str] = []
    if selectable_component_count:
        topology_facts.append(
            f"{selectable_component_count:,} disconnected form"
            f"{'s' if selectable_component_count != 1 else ''}"
        )
    if degenerate_triangles:
        topology_facts.append(
            f"{degenerate_triangles:,} degenerate triangle"
            f"{'s' if degenerate_triangles != 1 else ''}"
        )
    if unused_positions:
        topology_facts.append(
            f"{unused_positions:,} unused vertex tuple{'s' if unused_positions != 1 else ''}"
        )
    topology_facts.extend(
        (
            f"{projected_boundaries:,} boundary",
            f"{projected_non_manifold:,} non-manifold",
            f"{projected_winding:,} winding",
        )
    )
    topology_description = (
        " · ".join(topology_facts) + " after position projection."
        if diagnostic_primitives
        else "No triangle topology diagnostics were available."
    )
    material_description = (
        f"{inspection.package.material_count:,} material"
        f"{'s' if inspection.package.material_count != 1 else ''} · "
        f"{inspection.package.texture_count:,} texture"
        f"{'s' if inspection.package.texture_count != 1 else ''} · "
        f"{inspection.package.image_count:,} image"
        f"{'s' if inspection.package.image_count != 1 else ''}."
    )
    name_finding_count = sum(
        finding.code in _NAME_CODES and finding.severity is not Severity.INFO
        for finding in inspection.findings
    )
    name_description = (
        f"{len(name_items)} display name{'s' if len(name_items) != 1 else ''} need cleanup."
        if name_items
        else (
            f"{name_finding_count} display name"
            f"{'s' if name_finding_count != 1 else ''} remain unresolved."
            if name_finding_count
            else "Node and mesh display names need no change."
        )
    )
    structure_description = (
        f"{semantic_component_count} disconnected forms detected; target "
        f"{expected_piece_count} semantic "
        f"{'piece' if expected_piece_count == 1 else 'pieces'}."
        if component_mismatch and expected_piece_count is not None
        else (
            f"{inspection.package.node_count:,} node"
            f"{'s' if inspection.package.node_count != 1 else ''} · "
            f"{inspection.package.mesh_count:,} mesh"
            f"{'es' if inspection.package.mesh_count != 1 else ''} · "
            f"{inspection.package.primitive_count:,} primitive"
            f"{'s' if inspection.package.primitive_count != 1 else ''}."
        )
    )
    proposed_component_ids = set(component_ids)
    component_proposals = tuple(
        ComponentProposalView(
            component_id=component.component_id,
            label=f"C{component.ordinal + 1}",
            detail=(f"{component.triangle_count:,} triangles · {component.triangle_fraction:.1%}"),
            proposed_removal=component.component_id in proposed_component_ids,
        )
        for primitive in diagnostic_primitives
        if primitive.component_removal_safe
        for component in primitive.disconnected_components
    )
    return (
        InspectionCheckView(
            "GLB structure",
            structure_status,
            structure_label,
            structure_description,
            structure_action,
            None,
            action_heading,
        ),
        InspectionCheckView(
            "Size and pose",
            size_status,
            size_label,
            f"Measured {measured_dimensions}; target approximately {target_dimensions}.",
            normalization_action or "—",
            ProposalLane.SIZE_AND_POSE if normalization_action and not after_action else None,
            action_heading,
        ),
        InspectionCheckView(
            "Topology",
            topology_status,
            topology_label,
            topology_description,
            topology_action,
            (
                ProposalLane.TOPOLOGY
                if (weld_action or cleanup_action) and not after_action
                else None
            ),
            action_heading,
            (
                component_proposals
                if not after_action
                and any(
                    primitive.component_removal_safe and len(primitive.disconnected_components) > 1
                    for primitive in diagnostic_primitives
                )
                else ()
            ),
        ),
        InspectionCheckView(
            "Materials and textures",
            material_status,
            material_label,
            material_description,
            material_action,
            None,
            action_heading,
        ),
        InspectionCheckView(
            "Display names",
            name_status,
            name_label,
            name_description,
            name_action,
            ProposalLane.DISPLAY_NAMES if name_items and not after_action else None,
            action_heading,
        ),
    )


def _inspection_summary(job: WebJob, cannot_repair: bool) -> InspectionSummaryView:
    """Create concise agent copy from structured measurements and findings."""
    inspection = job.runtime.job.inspection
    plan = job.runtime.job.selected_plan
    assessment = job.runtime.job.agent_assessment
    if inspection is None:
        return InspectionSummaryView(
            headline="I\u2019m checking the model.",
            basics="Measurements will appear here.",
            normal="",
            attention=(),
        )
    if inspection.geometry is None:
        basics = "The GLB did not provide usable geometry measurements."
    else:
        dimensions = inspection.geometry.bounds.dimensions_m
        basics = (
            f"{dimensions[0]:.3f} \u00d7 {dimensions[1]:.3f} \u00d7 {dimensions[2]:.3f} m · "
            f"{inspection.geometry.triangle_count:,} triangles · "
            f"{inspection.package.material_count} material"
            f"{'s' if inspection.package.material_count != 1 else ''} · "
            f"{inspection.package.texture_count} texture"
            f"{'s' if inspection.package.texture_count != 1 else ''}."
        )
    findings = inspection.findings
    codes = {finding.code for finding in findings}
    physical_assessment = bool(
        assessment
        and (
            assessment.scale_to_confirmed_height
            or assessment.rotation_degrees != 0
            or assessment.ground_to_y_zero
        )
    )
    normal_labels: list[str] = []
    if not codes & _SIZE_POSE_CODES and not physical_assessment:
        normal_labels.append("size and pose")
    if not codes & _TOPOLOGY_CODES:
        normal_labels.append("topology")
    if not codes & _MATERIAL_CODES:
        normal_labels.append("materials and textures")
    if len(normal_labels) == 1:
        normal = f"{normal_labels[0].capitalize()} looks good."
    elif len(normal_labels) == 2:
        normal = f"{normal_labels[0].capitalize()} and {normal_labels[1]} look good."
    elif normal_labels:
        normal = f"{', '.join(normal_labels[:-1]).capitalize()}, and {normal_labels[-1]} look good."
    else:
        normal = ""

    attention: list[str] = []
    if assessment is not None and assessment.disposition.value == "REPAIR":
        attention.append(assessment.summary.rstrip(".") + ".")
    size_findings = [finding for finding in findings if finding.code in _SIZE_POSE_CODES]
    if size_findings and len(attention) < 3:
        attention.append(
            "Size and pose: "
            + "; ".join(finding.title.rstrip(".").lower() for finding in size_findings)
            + "."
        )
    data_findings = [
        finding
        for finding in findings
        if (finding.code in _TOPOLOGY_CODES or finding.code in _MATERIAL_CODES)
        and finding.severity is not Severity.INFO
    ]
    if data_findings:
        attention.append(
            "Geometry and resources: "
            + "; ".join(finding.title.rstrip(".").lower() for finding in data_findings)
            + "."
        )
    name_findings = [finding for finding in findings if finding.code in _NAME_CODES]
    if name_findings:
        node_names = any(finding.code.startswith("NODE_") for finding in name_findings)
        mesh_names = any(finding.code.startswith("MESH_") for finding in name_findings)
        subject = "Node and mesh" if node_names and mesh_names else "Node" if node_names else "Mesh"
        attention.append(f"{subject} display names need cleanup.")
    known_codes = _SIZE_POSE_CODES | _TOPOLOGY_CODES | _MATERIAL_CODES | _NAME_CODES
    other_findings = [finding for finding in findings if finding.code not in known_codes]
    if other_findings:
        other_summary = "; ".join(finding.title.rstrip(".").lower() for finding in other_findings)
        if len(attention) < 3:
            attention.append(f"Other: {other_summary}.")
        else:
            attention[-1] = f"{attention[-1]} Other: {other_summary}."

    if cannot_repair:
        headline = "This model needs another export."
    elif attention:
        headline = f"I found {len(attention)} area{'s' if len(attention) != 1 else ''} to review."
    elif plan is not None and not plan.candidates:
        headline = "No changes are needed."
    else:
        headline = "The inspection is complete."
    return InspectionSummaryView(
        headline=headline,
        basics=basics,
        normal=normal,
        attention=tuple(attention),
    )


def _default_job_view(job: WebJob) -> str:
    """Choose the one workflow step that needs the user's attention now."""
    if job.waiting_for_approval and job.inspection_acknowledged:
        return "decide"
    if job.waiting_for_approval:
        return "inspect"
    if job.workflow_result is not None or job.error is not None:
        return "download"
    return "inspect"


def _failed_candidate_path(job: AgentJob) -> Path | None:
    """Return a downloadable rejected candidate after deterministic verification fails."""
    candidate_path = job.output_dir / "candidate.glb"
    if (
        job.last_verification is not None
        and job.last_verification.state is VerificationState.FAILED
        and job.outcome is not None
        and job.outcome.executed_action_ids
        and candidate_path.is_file()
    ):
        return candidate_path
    return None


def _decision_summary(job: AgentJob) -> str:
    """Describe recorded physical authorization without exposing interrupt internals."""
    if job.decisions is None:
        return "pending"
    user_records = tuple(
        record
        for record in job.decisions.records
        if record.decision is not DecisionValue.AUTO_AUTHORIZED
    )
    if not user_records:
        return "No physical decision needed"
    approved = sum(record.decision is DecisionValue.APPROVED for record in user_records)
    rejected = sum(record.decision is DecisionValue.REJECTED for record in user_records)
    if approved and not rejected:
        return "Physical plan approved"
    if rejected and not approved:
        return "Physical plan rejected"
    return f"{approved} approved · {rejected} rejected"


def _result_presentation(job: AgentJob) -> ResultPresentationView | None:
    """Translate structured verification into a concise, evidence-backed result."""
    verification = job.last_verification
    if verification is None or job.result is None:
        return None

    if verification.state is VerificationState.FAILED:
        failed_checks = tuple(
            check for check in verification.checks if check.status.value != "PASS"
        )
        candidate_path = _failed_candidate_path(job)
        candidate_findings: tuple[Finding, ...] = ()
        if candidate_path is not None:
            candidate_findings = inspect_asset(
                candidate_path,
                job.profile,
                policy=job.profile_policy,
            ).findings
        attention_title = "Independent verification rejected the candidate."
        attention_detail = (
            failed_checks[0].description
            if failed_checks
            else "The repaired GLB did not satisfy every required check."
        )
        grounding = next(
            (finding for finding in candidate_findings if finding.code == "NOT_GROUNDED"),
            None,
        )
        if grounding is not None:
            observation = (
                grounding.evidence[0].observation if grounding.evidence else grounding.title
            )
            attention_title = "Grounding is still wrong."
            attention_detail = (
                f"{observation} The lowest point must land on Y=0 within "
                f"{job.profile.orientation.ground_tolerance_cm:g} cm."
            )
        if failed_checks:
            first_failed = failed_checks[0]
            attention_detail += (
                f" Verification failed {first_failed.code}: expected "
                f"{first_failed.expected}, observed {first_failed.actual}."
            )
        passed_count = sum(check.status.value == "PASS" for check in verification.checks)
        return ResultPresentationView(
            kind="failed",
            headline="Repair ran, but the candidate is not ready.",
            state_label="Candidate rejected",
            summary="The requested changes were applied, then checked from a fresh disk reload.",
            passed_title=f"{passed_count} checks passed",
            passed="GLB validity, geometry, materials, and textures were preserved.",
            attention_title=attention_title,
            attention_detail=attention_detail,
            next_step=(
                "You can download the candidate for human review or ask the agent to try again. "
                "It is not labeled verified or project-ready."
            ),
            package_label="Diagnostics and recorded evidence",
            download_label="Download diagnostics ZIP",
        )

    if verification.state is VerificationState.BLOCKED:
        reason = (
            job.selected_plan.blocked_reasons[0]
            if job.selected_plan is not None and job.selected_plan.blocked_reasons
            else "The asset is outside the supported deterministic repair set."
        )
        return ResultPresentationView(
            kind="blocked",
            headline="This asset could not be repaired here.",
            state_label="Inspection only",
            summary="Inspection completed without creating a repair candidate.",
            passed_title="Inspection completed",
            passed="The measured source facts and policy findings are recorded in the package.",
            attention_title="Why repair stopped",
            attention_detail=reason,
            next_step="Correct the source in its creation or export tool, then inspect a new GLB.",
            package_label="Inspection and diagnostics",
            download_label="Download diagnostics ZIP",
        )

    warning = verification.remaining_warnings[0] if verification.remaining_warnings else None
    return ResultPresentationView(
        kind="ready",
        headline="The verified package is ready.",
        state_label="Verified",
        summary="Independent verification accepted the repaired model.",
        passed_title="All required checks passed",
        passed="Size, orientation, names, geometry, materials, and textures passed.",
        attention_title="Report-only note" if warning else "Ready to use",
        attention_detail=warning or "No repairable issue remains.",
        next_step="Compare the models, then download the repaired GLB and its evidence.",
        package_label="Verified model and evidence",
        download_label="Download result ZIP",
    )


def _one_sentence(value: str) -> str:
    """Normalize one model-authored message into a compact completion sentence."""
    compact = " ".join(value.split()).strip()
    if not compact:
        return "The asset conversation finished."
    match = re.search(r"[.!?](?:\s|$)", compact)
    sentence = compact[: match.end()].strip() if match else compact
    if sentence[-1] not in ".!?":
        sentence += "."
    return sentence


def _completion_sentence(workspace: HostedWorkspace, job: AgentJob | None) -> str | None:
    """Use the persisted workflow agent's response for the single completion message."""
    if job is None or job.result is None:
        return None
    if job.candidate_reassessment is not None:
        summary = _one_sentence(job.candidate_reassessment.summary)
        warnings = job.last_verification.remaining_warnings if job.last_verification else ()
        if warnings:
            labels = [
                warning.partition(":")[2].strip() or warning.partition(":")[0].strip()
                for warning in warnings
            ]
            return f"{summary.rstrip('.!?')}; remaining: {'; '.join(labels)}."
        return summary
    if job.agent_assessment is not None:
        summary = _one_sentence(job.agent_assessment.summary)
        if job.agent_assessment.disposition is AgentDisposition.RETURN_TO_CREATION_TOOL:
            if _supported_component_recovery(job):
                return (
                    "I stopped this pass before choosing which labeled forms to keep. Refine the "
                    "current iteration to review a component-removal proposal."
                )
            return f"I can't repair this asset — {summary[0].lower()}{summary[1:]}"
        return summary
    if workspace.workflow_result is not None:
        return _one_sentence(workspace.workflow_result.user_message)
    presentation = _result_presentation(job)
    return _one_sentence(presentation.summary if presentation else "The workflow stopped.")


def _current_turn_outcome_summary(
    workspace: HostedWorkspace,
    job: AgentJob | None,
) -> str | None:
    """Return the newest completed assessment without hiding its preceding proposal."""
    completed = _completion_sentence(workspace, job)
    if completed is not None:
        return completed
    if job is not None and job.candidate_reassessment is not None:
        return _one_sentence(job.candidate_reassessment.summary)
    return None


def _has_next_turn_candidate(job: AgentJob | None) -> bool:
    """Return whether a completed turn produced a candidate that can seed another turn."""
    if job is None:
        return False
    return (job.output_dir / "repaired.glb").is_file() or job.candidate_path.is_file()


def _workflow_steps(job: WebJob) -> tuple[WorkflowStepView, ...]:
    """Summarize inspect, decide, and download progress without duplicating content."""
    core = job.runtime.job
    if job.waiting_for_approval:
        decision_status = "attention"
    elif core.selected_plan is not None and core.selected_plan.blocked:
        decision_status = "blocked"
    elif core.decisions is not None or (
        core.selected_plan is not None and not core.selected_plan.approval_action_ids
    ):
        decision_status = "complete"
    else:
        decision_status = "pending"
    if core.result is not None:
        download_status = "complete"
    elif job.error is not None:
        download_status = "blocked"
    else:
        download_status = "pending"
    return (
        WorkflowStepView(
            slug="inspect",
            label="Inspect",
            status="complete" if core.inspection is not None else "pending",
        ),
        WorkflowStepView(slug="decide", label="Decide", status=decision_status),
        WorkflowStepView(slug="download", label="Download", status=download_status),
    )


def _comparison_bounds(
    minimum_m: tuple[float, float, float],
    maximum_m: tuple[float, float, float],
) -> ComparisonBoundsView:
    """Derive centers and corner anchors from one finite world-space AABB."""
    dimensions_m = tuple(maximum_m[index] - minimum_m[index] for index in range(3))
    center_m = tuple((minimum_m[index] + maximum_m[index]) / 2.0 for index in range(3))
    corners_m = tuple(
        (x_value, y_value, z_value)
        for x_value in (minimum_m[0], maximum_m[0])
        for y_value in (minimum_m[1], maximum_m[1])
        for z_value in (minimum_m[2], maximum_m[2])
    )
    return ComparisonBoundsView(
        minimum_m=minimum_m,
        maximum_m=maximum_m,
        dimensions_m=cast(tuple[float, float, float], dimensions_m),
        center_m=cast(tuple[float, float, float], center_m),
        longest_m=max(dimensions_m),
        corners_m=corners_m,
    )


def _nice_meter_step(span_m: float) -> float:
    """Choose a 1/2/5 meter interval that yields about five major ticks."""
    raw_step = max(span_m, 1e-9) / 4.0
    magnitude = 10.0 ** math.floor(math.log10(raw_step))
    fraction = raw_step / magnitude
    if fraction <= 1.0:
        multiplier = 1.0
    elif fraction <= 2.0:
        multiplier = 2.0
    elif fraction <= 5.0:
        multiplier = 5.0
    else:
        multiplier = 10.0
    return multiplier * magnitude


def _metric_axis(
    axis: str,
    axis_index: int,
    origin_m: tuple[float, float, float],
    span_m: float,
    fallback_span_m: float,
) -> MetricAxisView:
    """Create one meter ruler beginning at the displayed model origin."""
    displayed_span = span_m if span_m > 1e-9 else fallback_span_m
    step_m = _nice_meter_step(displayed_span)
    ticks: list[MetricAxisTickView] = []
    for index in range(5):
        value_m = index * step_m
        position = list(origin_m)
        position[axis_index] += value_m
        label = f"{value_m:.3g} m"
        if index == 0:
            label = f"{axis.upper()} · {label}"
        ticks.append(
            MetricAxisTickView(
                slot_name=f"hotspot-axis-{axis}-{index}",
                label=label,
                position_m=(position[0], position[1], position[2]),
            )
        )
    return MetricAxisView(axis=axis, ticks=tuple(ticks))


def _comparison_scene(source_path: Path, candidate_path: Path) -> ComparisonSceneView:
    """Place source and candidate side by side without changing either model's scale."""
    source_bounds = world_bounds(load_glb(source_path))
    candidate_bounds = world_bounds(load_glb(candidate_path))
    before_minimum = tuple(float(source_bounds.minimum[index]) for index in range(3))
    before_maximum = tuple(float(source_bounds.maximum[index]) for index in range(3))
    candidate_minimum = tuple(float(candidate_bounds.minimum[index]) for index in range(3))
    candidate_maximum = tuple(float(candidate_bounds.maximum[index]) for index in range(3))
    before = _comparison_bounds(
        cast(tuple[float, float, float], before_minimum),
        cast(tuple[float, float, float], before_maximum),
    )
    candidate = _comparison_bounds(
        cast(tuple[float, float, float], candidate_minimum),
        cast(tuple[float, float, float], candidate_maximum),
    )

    comparison_scale = max(before.longest_m, candidate.longest_m, 1e-6)
    gap_m = comparison_scale * 0.15
    after_offset_m = (
        before.maximum_m[0] - candidate.minimum_m[0] + gap_m,
        0.0,
        0.0,
    )
    after = _comparison_bounds(
        (
            candidate.minimum_m[0] + after_offset_m[0],
            candidate.minimum_m[1],
            candidate.minimum_m[2],
        ),
        (
            candidate.maximum_m[0] + after_offset_m[0],
            candidate.maximum_m[1],
            candidate.maximum_m[2],
        ),
    )
    combined = _comparison_bounds(
        (
            min(before.minimum_m[0], after.minimum_m[0]),
            min(before.minimum_m[1], after.minimum_m[1]),
            min(before.minimum_m[2], after.minimum_m[2]),
        ),
        (
            max(before.maximum_m[0], after.maximum_m[0]),
            max(before.maximum_m[1], after.maximum_m[1]),
            max(before.maximum_m[2], after.maximum_m[2]),
        ),
    )
    fallback_axis_span = max(before.longest_m * 0.1, 1e-6)
    axes = tuple(
        _metric_axis(
            axis,
            index,
            (0.0, 0.0, 0.0),
            before.dimensions_m[index],
            fallback_axis_span,
        )
        for index, axis in enumerate(("x", "y", "z"))
    )

    banana_minimum_y = -0.015916550531983376
    banana_maximum_z = 0.015987513586878777
    banana_gap_m = max(combined.longest_m * 0.08, 0.02)
    banana_offset_m = (
        combined.center_m[0],
        combined.minimum_m[1] - banana_minimum_y,
        combined.minimum_m[2] - banana_gap_m - banana_maximum_z,
    )
    banana_anchor_m = (
        banana_offset_m[0],
        banana_offset_m[1] + 0.025,
        banana_offset_m[2],
    )
    client_data: dict[str, JsonValue] = {
        "origins": {"before": [0.0, 0.0, 0.0], "after": list(after_offset_m)},
        "before": cast(
            JsonValue,
            {
                "minimum": list(before.minimum_m),
                "maximum": list(before.maximum_m),
                "center": list(before.center_m),
                "longest": before.longest_m,
            },
        ),
        "after": cast(
            JsonValue,
            {
                "minimum": list(after.minimum_m),
                "maximum": list(after.maximum_m),
                "center": list(after.center_m),
                "longest": after.longest_m,
            },
        ),
        "both": cast(
            JsonValue,
            {
                "minimum": list(combined.minimum_m),
                "maximum": list(combined.maximum_m),
                "center": list(combined.center_m),
                "longest": combined.longest_m,
            },
        ),
    }
    return ComparisonSceneView(
        before=before,
        after=after,
        combined=combined,
        after_offset_m=after_offset_m,
        banana_offset_m=banana_offset_m,
        banana_anchor_m=banana_anchor_m,
        axes=axes,
        client_data=client_data,
    )


def _source_scene(
    source_path: Path,
    inspection: InspectionResult | None = None,
    *,
    proposed_origin_m: tuple[float, float, float] | None = None,
) -> SourceSceneView:
    """Measure and frame one uploaded source asset without mutating it."""
    gltf = load_glb(source_path)
    source_bounds = world_bounds(gltf)
    before = _comparison_bounds(
        cast(tuple[float, float, float], tuple(float(value) for value in source_bounds.minimum)),
        cast(tuple[float, float, float], tuple(float(value) for value in source_bounds.maximum)),
    )
    fallback_axis_span = max(before.longest_m * 0.1, 1e-6)
    axes = tuple(
        _metric_axis(
            axis,
            index,
            (0.0, 0.0, 0.0),
            before.dimensions_m[index],
            fallback_axis_span,
        )
        for index, axis in enumerate(("x", "y", "z"))
    )
    banana_minimum_y = -0.015916550531983376
    banana_maximum_z = 0.015987513586878777
    banana_gap_m = max(before.longest_m * 0.08, 0.02)
    banana_offset_m = (
        before.center_m[0],
        before.minimum_m[1] - banana_minimum_y,
        before.minimum_m[2] - banana_gap_m - banana_maximum_z,
    )
    banana_anchor_m = (
        banana_offset_m[0],
        banana_offset_m[1] + 0.025,
        banana_offset_m[2],
    )
    client_bounds = cast(
        JsonValue,
        {
            "minimum": list(before.minimum_m),
            "maximum": list(before.maximum_m),
            "center": list(before.center_m),
            "longest": before.longest_m,
        },
    )
    component_boxes: list[ComponentBoundsView] = []
    diagnostics = inspection.diagnostics if inspection is not None else None
    primitives = diagnostics.primitives if diagnostics is not None else ()
    primitive_components = {
        (primitive.mesh_index, primitive.primitive_index): primitive.disconnected_components
        for primitive in primitives
        if primitive.disconnected_components
    }
    if primitive_components:
        for node_index, world in iter_world_matrices(gltf):
            mesh_index = gltf.nodes[node_index].mesh
            if mesh_index is None:
                continue
            for primitive_index, _ in enumerate(gltf.meshes[mesh_index].primitives):
                for component in primitive_components.get((mesh_index, primitive_index), ()):
                    local_corners = np.asarray(
                        [
                            (x_value, y_value, z_value)
                            for x_value in (
                                component.local_minimum_m[0],
                                component.local_maximum_m[0],
                            )
                            for y_value in (
                                component.local_minimum_m[1],
                                component.local_maximum_m[1],
                            )
                            for z_value in (
                                component.local_minimum_m[2],
                                component.local_maximum_m[2],
                            )
                        ],
                        dtype=np.float64,
                    )
                    homogeneous = np.column_stack(
                        (local_corners, np.ones(len(local_corners), dtype=np.float64))
                    )
                    transformed = (world @ homogeneous.T).T[:, :3]
                    component_boxes.append(
                        ComponentBoundsView(
                            component_id=component.component_id,
                            label=f"C{component.ordinal + 1}",
                            corners_m=tuple(
                                (float(point[0]), float(point[1]), float(point[2]))
                                for point in transformed
                            ),
                        )
                    )
    client_data: dict[str, JsonValue] = {"before": client_bounds, "both": client_bounds}
    client_data["origins"] = {"before": [0.0, 0.0, 0.0]}
    if proposed_origin_m is not None:
        client_data["proposedOrigin"] = cast(JsonValue, list(proposed_origin_m))
    if component_boxes:
        client_data["components"] = cast(
            JsonValue,
            [
                {"id": item.component_id, "label": item.label, "index": index}
                for index, item in enumerate(component_boxes)
            ],
        )
    return SourceSceneView(
        before=before,
        combined=before,
        banana_offset_m=banana_offset_m,
        banana_anchor_m=banana_anchor_m,
        axes=axes,
        client_data=client_data,
        component_boxes=tuple(component_boxes),
        proposed_origin_m=proposed_origin_m,
    )


def _proposed_pivot_marker(job: AgentJob | None) -> tuple[float, float, float] | None:
    """Locate the exact point on the current asset that an approved pivot would adopt."""
    if job is None or job.pending_interrupt_id is None or job.selected_plan is None:
        return None
    for candidate in job.selected_plan.candidates:
        payload = candidate.payload
        if not isinstance(payload, NormalizationPayload):
            continue
        if not any(component.component == "pivot" for component in payload.components):
            continue
        bounds = payload.before_bounds
        center = tuple(
            (minimum + maximum) / 2.0
            for minimum, maximum in zip(bounds.minimum_m, bounds.maximum_m, strict=True)
        )
        if payload.pivot_target == "BOUNDS_CENTER":
            return cast(tuple[float, float, float], center)
        if payload.pivot_target == "FOOTPRINT_CENTER_BOTTOM":
            return (center[0], bounds.minimum_m[1], center[2])
        if payload.pivot_target == "MEASURED_ANCHOR":
            return payload.pivot_anchor_position_m
    return None


def _hosted_workspace_scene(
    workspace: HostedWorkspace,
) -> tuple[ComparisonSceneView | SourceSceneView | None, bool, bool, str, str]:
    """Build the current turn's one authoritative interactive scene."""
    runtime_job = workspace.runtime.job if workspace.runtime is not None else None
    comparison_scene: ComparisonSceneView | SourceSceneView | None = None
    comparison_candidate_ready = False
    comparison_source_only = True
    if workspace.ready_candidate and runtime_job is not None:
        # A verified packaged candidate is durable; the in-memory execution outcome is not.
        # Build the comparison from the artifact after a server restart as well as immediately
        # after the repair turn.
        comparison_candidate_path = workspace.output_dir / "repaired.glb"
        comparison_scene = _comparison_scene(runtime_job.source, comparison_candidate_path)
        comparison_candidate_ready = True
        comparison_source_only = False
    elif (
        runtime_job is not None
        and runtime_job.outcome is not None
        and runtime_job.outcome.executed_action_ids
    ):
        comparison_candidate_path = _failed_candidate_path(runtime_job)
        if comparison_candidate_path is not None:
            comparison_scene = _comparison_scene(runtime_job.source, comparison_candidate_path)
            comparison_source_only = False
    current_source_path = runtime_job.source if runtime_job is not None else workspace.source_path
    if comparison_scene is None and current_source_path.is_file():
        inspection = runtime_job.inspection if runtime_job is not None else None
        comparison_scene = _source_scene(
            current_source_path,
            inspection,
            proposed_origin_m=_proposed_pivot_marker(runtime_job),
        )
    refine_iteration = runtime_job.turn_index if runtime_job is not None else 0
    before_label = f"Iteration {refine_iteration}" if refine_iteration else "Uploaded model"
    after_label = f"Iteration {refine_iteration + 1}" if refine_iteration else "Candidate"
    return (
        comparison_scene,
        comparison_candidate_ready,
        comparison_source_only,
        before_label,
        after_label,
    )


def _archived_turn_summary(workspace: HostedWorkspace, turn_index: int) -> str:
    """Recover concise agent-authored outcome evidence for one notebook turn."""
    turn_root = workspace.root / "turns" / f"turn-{turn_index:03d}"
    verification_path = turn_root / "output" / "verification.json"
    try:
        verification = cast(
            dict[str, object],
            json.loads(verification_path.read_text(encoding="utf-8")),
        )
        checks = verification.get("checks")
        if isinstance(checks, list):
            for check_value in cast(list[object], checks):
                if not isinstance(check_value, dict):
                    continue
                check = cast(dict[str, object], check_value)
                if check.get("code") != "AGENT_VISUAL_REASSESSMENT":
                    continue
                actual = check.get("actual")
                if isinstance(actual, str) and actual.strip():
                    return _one_sentence(actual)
                description = check.get("description")
                if isinstance(description, str) and description.strip():
                    return _one_sentence(description)
    except (OSError, TypeError, json.JSONDecodeError):
        pass
    assessment_path = turn_root / "agent_assessment.json"
    try:
        assessment = json.loads(assessment_path.read_text(encoding="utf-8"))
        summary = assessment.get("summary")
        if isinstance(summary, str) and summary.strip():
            return _one_sentence(summary)
    except (OSError, TypeError, json.JSONDecodeError):
        pass
    return "This iteration is saved with its verification record."


def _summary_from_json(path: Path, field: str) -> str | None:
    """Read one compact model-authored summary from a trusted workspace artifact."""
    try:
        payload = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
        value = payload.get(field)
        return _one_sentence(value) if isinstance(value, str) and value.strip() else None
    except (OSError, TypeError, json.JSONDecodeError):
        return None


def _decision_sentence(approved: int, rejected: int) -> str | None:
    """Turn structured authorization records into one user-side notebook message."""
    if approved and not rejected:
        return "Approved the proposed repair."
    if rejected and not approved:
        return "Rejected the proposed repair."
    if approved or rejected:
        return f"Approved {approved} proposed changes and rejected {rejected}."
    return None


def _decision_sentence_from_records(records: object) -> str | None:
    """Read only explicit user decisions from a serialized Decisions record list."""
    if not isinstance(records, list):
        return None
    approved = 0
    rejected = 0
    for raw_record in cast(list[object], records):
        if not isinstance(raw_record, dict):
            continue
        record = cast(dict[str, object], raw_record)
        decision = record.get("decision")
        if decision == DecisionValue.APPROVED.value:
            approved += 1
        elif decision == DecisionValue.REJECTED.value:
            rejected += 1
    return _decision_sentence(approved, rejected)


def _current_turn_decision_summary(job: AgentJob | None) -> str | None:
    """Return the current turn's explicit human authorization as notebook copy."""
    if job is None or job.decisions is None:
        return None
    approved = sum(record.decision is DecisionValue.APPROVED for record in job.decisions.records)
    rejected = sum(record.decision is DecisionValue.REJECTED for record in job.decisions.records)
    return _decision_sentence(approved, rejected)


def _archived_turn_view(
    workspace: HostedWorkspace,
    turn: ConversationTurnRecord,
) -> NotebookTurnView:
    """Recover the proposal, decision, and outcome for one immutable archived turn."""
    turn_root = workspace.root / "turns" / f"turn-{turn.turn_index:03d}"
    proposal = _summary_from_json(turn_root / "agent_assessment.json", "summary")
    decision: str | None = None
    decisions_path = turn_root / "output" / "decisions.json"
    try:
        decisions = cast(
            dict[str, object],
            json.loads(decisions_path.read_text(encoding="utf-8")),
        )
        decision = _decision_sentence_from_records(decisions.get("records"))
    except (OSError, TypeError, json.JSONDecodeError):
        pass
    return NotebookTurnView(
        turn=turn,
        proposal_summary=proposal or "Asset Shepherd assessed this iteration.",
        decision_summary=decision,
        outcome_summary=_archived_turn_summary(workspace, turn.turn_index),
    )


def _approval_assessment_sentence(job: AgentJob | None) -> str | None:
    """Keep pre-approval agent language explicitly prospective."""
    if job is None or job.agent_assessment is None:
        return None
    sentence = _one_sentence(job.agent_assessment.summary)
    if job.agent_assessment.disposition is not AgentDisposition.REPAIR:
        return sentence
    if sentence.casefold().startswith(("i propose", "i recommend")):
        return sentence
    return f"I propose this change: {sentence[0].lower()}{sentence[1:]}"


def _job_context(job: WebJob, requested_view: str | None = None) -> dict[str, object]:
    """Build the template context solely from structured job state."""
    core = job.runtime.job
    verification = core.last_verification
    if requested_view == "decide" and job.waiting_for_approval and not job.inspection_acknowledged:
        requested_view = "inspect"
    active_view = (
        requested_view
        if requested_view in {"inspect", "decide", "download"}
        else _default_job_view(job)
    )
    decision_records: tuple[DecisionRecord, ...] = ()
    if core.decisions is not None:
        decision_records = tuple(
            record
            for record in core.decisions.records
            if record.decision is not DecisionValue.AUTO_AUTHORIZED
        )
    plan = core.selected_plan
    cannot_repair = bool(
        (plan is not None and plan.blocked)
        or (
            core.inspection is not None
            and core.inspection.repair_eligibility is not RepairEligibility.ELIGIBLE_STATIC_MESH
        )
    )
    inspection_checks = _inspection_checks(core)
    comparison_scene = None
    comparison_candidate_path = (
        job.output_dir / "repaired.glb" if job.ready_candidate else _failed_candidate_path(core)
    )
    if (
        comparison_candidate_path is not None
        and core.outcome is not None
        and core.outcome.executed_action_ids
    ):
        comparison_scene = _comparison_scene(
            core.source,
            comparison_candidate_path,
        )
    return {
        "job": job,
        "story": job.story,
        "active_mode": active_view,
        "active_style": active_view.capitalize(),
        "active_view": active_view,
        "workflow_steps": _workflow_steps(job),
        "stages": job.stages(),
        "inspection_checks": inspection_checks,
        "inspection_summary": _inspection_summary(job, cannot_repair),
        "comparison_source_only": False,
        "inspection_needs_confirmation": bool(
            job.waiting_for_approval and not job.inspection_acknowledged
        ),
        "finding_groups": _finding_groups(job),
        "basis_labels": BASIS_LABELS,
        "target_expectations": _target_expectations(
            job.target_intake,
            core.profile,
            job.profile.policy_provenance.rule_sources,
        ),
        "universal_expectations": UNIVERSAL_EXPECTATIONS,
        "cannot_repair": cannot_repair,
        "rule_explanations": {
            finding.id: explanation
            for finding in (core.inspection.findings if core.inspection is not None else ())
            if (explanation := _rule_explanation(finding)) is not None
        },
        "approval_card": job.approval_card(),
        "interrupt_id": core.pending_interrupt_id,
        "inspection": core.inspection,
        "plan": plan,
        "verification": verification,
        "workflow_result": job.workflow_result,
        "comparison_scene": comparison_scene,
        "comparison_candidate_ready": job.ready_candidate,
        "shepherded_download_filename": _shepherded_download_filename(job.target_intake.asset_name),
        "result_presentation": _result_presentation(core),
        "decision_summary": _decision_summary(core),
        "decision_records": decision_records,
        "turn_index": core.turn_index,
        "turns_remaining": core.turns_remaining,
        "can_continue": (
            core.agent_orchestrated and core.turns_remaining > 0 and _has_next_turn_candidate(core)
        ),
        "prior_turns": core.prior_turns,
        "accepted": job.accepted,
        "is_blocked": bool(
            verification is not None and verification.state is VerificationState.BLOCKED
        ),
    }


def create_app(
    *,
    project_root: Path = _DEFAULT_PROJECT_ROOT,
    work_root: Path = _DEFAULT_WORK_ROOT,
    intake_analyzer: TargetIntakeAnalyzer | None = None,
    max_agent_turns: int | None = None,
    verification_function: VerificationFunction = verify_repair,
    agentcore_dispatcher: AgentCoreCommandDispatcher | None = None,
) -> FastAPI:
    """Create a local Asset Shepherd web application and isolated job store."""
    family = discover_policy_family(project_root.resolve(strict=True))
    analyzer = intake_analyzer or DeterministicTargetIntakeAnalyzer()
    workspace_bucket = os.environ.get("ASSET_SHEPHERD_WORKSPACE_BUCKET")
    workspace_table = os.environ.get("ASSET_SHEPHERD_WORKSPACE_TABLE")
    workspace_owner = os.environ.get("ASSET_SHEPHERD_WORKSPACE_OWNER_ID")
    cloud_values = (workspace_bucket, workspace_table, workspace_owner)
    if any(cloud_values) and not all(cloud_values):
        raise ValueError(
            "Cloud workspace storage requires ASSET_SHEPHERD_WORKSPACE_BUCKET, "
            "ASSET_SHEPHERD_WORKSPACE_TABLE, and ASSET_SHEPHERD_WORKSPACE_OWNER_ID"
        )
    workspace_repository: WorkspaceRepository | None = None
    workspace_region: str | None = None
    if workspace_bucket and workspace_table and workspace_owner:
        workspace_region = (
            os.environ.get("ASSET_SHEPHERD_AWS_REGION")
            or os.environ.get("AWS_REGION")
            or os.environ.get("AWS_DEFAULT_REGION")
        )
        if not workspace_region:
            raise ValueError("Cloud workspace storage requires an AWS region")
        workspace_repository = S3DynamoWorkspaceRepository(
            bucket=workspace_bucket,
            table=workspace_table,
            owner_id=workspace_owner,
            region=workspace_region,
            aws_profile=os.environ.get("AWS_PROFILE"),
        )
    command_queue_url = os.environ.get("ASSET_SHEPHERD_AGENT_COMMAND_QUEUE_URL", "").strip()
    remote_dispatcher = agentcore_dispatcher
    if command_queue_url and remote_dispatcher is None:
        if not workspace_table or not workspace_owner or not workspace_region:
            raise ValueError("Remote AgentCore dispatch requires complete cloud workspace settings")
        remote_dispatcher = AgentCoreCommandDispatcher(
            queue_url=command_queue_url,
            table=workspace_table,
            actor_id=workspace_owner,
            region=workspace_region,
            workspace_repository=cast(S3DynamoWorkspaceRepository, workspace_repository),
        )
    runtime_actor_id = remote_dispatcher.actor_id if remote_dispatcher is not None else None
    agent_model_choices = hosted_model_choices(os.environ)
    default_agent_model = next(
        (model for model in agent_model_choices if model.recommended),
        agent_model_choices[0] if agent_model_choices else None,
    )
    configured_model_id = os.environ.get("ASSET_SHEPHERD_MODEL_ID")
    if configured_model_id and agent_model_choices:
        try:
            configured_model = resolve_hosted_model(configured_model_id)
        except ValueError:
            configured_model = None
        if configured_model in agent_model_choices:
            default_agent_model = configured_model

    # Prefer the deployed, secret-backed Luna adapter for new uploads only.
    # Saved workspaces retain their explicit model selection.
    default_agent_model = next(
        (model for model in agent_model_choices if model.model_id == "gpt-5.6-luna"),
        default_agent_model,
    )

    def model_values(model_id: str) -> Mapping[str, str]:
        """Bind one allowlisted workspace model to deployment-owned provider settings."""
        capability = resolve_hosted_model(model_id)
        if capability not in agent_model_choices:
            raise ValueError("Choose an available Asset Shepherd model.")
        return hosted_model_values(model_id, os.environ)

    configured_turns = max_agent_turns
    if configured_turns is None:
        try:
            configured_turns = int(os.environ.get("ASSET_SHEPHERD_MAX_TURNS", "5"))
        except ValueError as error:
            raise ValueError("ASSET_SHEPHERD_MAX_TURNS must be an integer") from error
    store = WebJobStore(work_root, family, analyzer, configured_turns)
    hosted_store = HostedWorkspaceStore(
        work_root / "hosted",
        family.profile,
        analyzer,
        configured_turns,
        verification_function,
        model_values if agent_model_choices else None,
        workspace_repository,
    )
    hosted_start_drafts: dict[str, HostedStartDraft] = {}
    hosted_start_lock = RLock()
    gallery_mutation_lock = RLock()
    hosted_staging_root = (work_root / "hosted-start").resolve(strict=False)
    upload_checks = UploadPreflight()
    feedback_root = work_root / "feedback"
    templates = Jinja2Templates(directory=_PACKAGE_ROOT / "templates")
    cast(dict[str, object], templates.env.globals)["static_version"] = _static_asset_version()
    app = FastAPI(
        title="Asset Shepherd",
        description="Inspect, approve, repair, verify, and package one static GLB.",
        docs_url=None,
        redoc_url=None,
    )
    app.state.job_store = store
    install_login(app)
    app.state.hosted_workspace_store = hosted_store
    app.state.upload_checks = upload_checks
    app.state.agentcore_dispatcher = remote_dispatcher
    app.mount("/static", StaticFiles(directory=_PACKAGE_ROOT / "static"), name="static")

    def persist_hosted_start_draft(draft: HostedStartDraft) -> None:
        """Persist one resumable upload/description draft atomically."""
        destination = draft.source_path.parent / "draft.json"
        temporary = destination.with_suffix(".tmp")
        payload = {
            "draft_id": draft.draft_id,
            "original_filename": draft.original_filename,
            "replace_workspace_id": draft.replace_workspace_id,
            "initial_description": draft.initial_description,
            "model_id": draft.model_id,
        }
        temporary.write_text(
            f"{json.dumps(payload, indent=2, sort_keys=True)}\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary.replace(destination)

    def load_hosted_start_draft(draft_id: str) -> HostedStartDraft | None:
        """Load one validated staged draft after application restart."""
        if re.fullmatch(r"[0-9a-f]{32}", draft_id) is None:
            return None
        root = hosted_staging_root / draft_id
        source_path = root / "source.glb"
        metadata_path = root / "draft.json"
        if not source_path.is_file() or not metadata_path.is_file():
            return None
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            if payload.get("draft_id") != draft_id:
                return None
            return HostedStartDraft(
                draft_id=draft_id,
                original_filename=str(payload["original_filename"]),
                source_path=source_path,
                replace_workspace_id=payload.get("replace_workspace_id"),
                initial_description=str(payload.get("initial_description", "")),
                model_id=(str(payload["model_id"]) if payload.get("model_id") else None),
            )
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def list_hosted_start_drafts() -> tuple[HostedStartDraft, ...]:
        """Return resumable upload drafts, including drafts restored after restart."""
        hosted_staging_root.mkdir(parents=True, exist_ok=True)
        with hosted_start_lock:
            for metadata_path in hosted_staging_root.glob("*/draft.json"):
                draft = load_hosted_start_draft(metadata_path.parent.name)
                if draft is not None:
                    hosted_start_drafts[draft.draft_id] = draft
            return tuple(hosted_start_drafts.values())

    def render_intent_home(
        request: Request,
        error: str | None = None,
        status_code: int = 200,
        values: Mapping[str, str] | None = None,
        *,
        refusal: bool = False,
    ) -> Response:
        """Render the single intent-first entry point."""
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "error": error,
                "refusal": refusal,
                "values": values or {},
                "active_mode": "describe",
                "active_style": "Describe",
            },
            status_code=status_code,
            headers={"Cache-Control": "no-store"},
        )

    def render_hosted_home(
        request: Request,
        error: str | None = None,
        status_code: int = 200,
        description: str = "",
        *,
        refusal: bool = False,
    ) -> Response:
        """Render the versioned D019 conversation-led entry point."""
        records = hosted_store.list_records()
        drafts = list_hosted_start_drafts()
        new_drafts = tuple(draft for draft in drafts if draft.replace_workspace_id is None)
        redo_drafts = {
            draft.replace_workspace_id: draft
            for draft in drafts
            if draft.replace_workspace_id is not None
        }
        gallery_full = len(records) + len(new_drafts) >= MAX_HOSTED_WORKSPACES
        return templates.TemplateResponse(
            request=request,
            name="hosted_home.html",
            context={
                "error": error,
                "refusal": refusal,
                "description": description,
                "workspace_records": records,
                "workspace_statuses": {
                    record.workspace_id: gallery_status(
                        record.phase,
                        hosted_store.turn_index(record.workspace_id),
                    )
                    for record in records
                },
                "new_drafts": new_drafts,
                "redo_drafts": redo_drafts,
                "gallery_full": gallery_full,
                "can_add_asset": not gallery_full,
                "workspace_limit": MAX_HOSTED_WORKSPACES,
                "active_mode": "conversation",
                "active_style": "Gallery",
                "hosted_step": "gallery",
                "agent_model_choices": agent_model_choices,
                "default_agent_model": default_agent_model,
            },
            status_code=status_code,
            headers={"Cache-Control": "no-store"},
        )

    def render_hosted_describe(
        request: Request,
        draft: HostedStartDraft | None,
        error: str | None = None,
        status_code: int = 200,
        description: str = "",
        *,
        refusal: bool = False,
    ) -> Response:
        """Render the description step after one GLB has passed objective preflight."""
        source_scene = _source_scene(draft.source_path) if draft else None
        return templates.TemplateResponse(
            request=request,
            name="hosted_describe.html",
            context={
                "error": error,
                "refusal": refusal,
                "description": description or (draft.initial_description if draft else ""),
                "draft": draft,
                "comparison_scene": source_scene,
                "upload_summary": (
                    _uploaded_asset_summary(source_scene.before.dimensions_m)
                    if source_scene is not None
                    else None
                ),
                "comparison_source_url": (
                    request.url_for("hosted_draft_source_asset", draft_id=draft.draft_id)
                    if draft
                    else None
                ),
                "comparison_source_only": True,
                "active_mode": "conversation",
                "active_style": "Describe",
                "hosted_step": "describe",
            },
            status_code=status_code,
            headers={"Cache-Control": "no-store"},
        )

    def render_hosted_upload(
        request: Request,
        error: str | None = None,
        status_code: int = 200,
        replace_workspace_id: str | None = None,
    ) -> Response:
        """Render the first new-asset step: one GLB upload."""
        return templates.TemplateResponse(
            request=request,
            name="hosted_upload.html",
            context={
                "error": error,
                "replace_workspace_id": replace_workspace_id,
                "active_mode": "conversation",
                "active_style": "Upload",
                "hosted_step": "upload",
                "agent_model_choices": agent_model_choices,
                "selected_agent_model": default_agent_model,
                "default_agent_model": default_agent_model,
            },
            status_code=status_code,
            headers={"Cache-Control": "no-store"},
        )

    def render_hosted_workspace(
        request: Request,
        workspace: HostedWorkspace,
        error: str | None = None,
        status_code: int = 200,
    ) -> Response:
        """Render conversation and structured Job Contract from durable state."""
        runtime_job = workspace.runtime.job if workspace.runtime is not None else None
        inspection = runtime_job.inspection if runtime_job is not None else None
        finding_groups: list[tuple[str, tuple[Finding, ...]]] = []
        if inspection is not None:
            for severity in (
                Severity.BLOCKER,
                Severity.ERROR,
                Severity.WARNING,
                Severity.INFO,
            ):
                findings = tuple(
                    finding for finding in inspection.findings if finding.severity is severity
                )
                if findings:
                    finding_groups.append((severity.value, findings))
        policy_rules: tuple[tuple[str, str], ...] = ()
        if runtime_job is not None and workspace.record.profile_policy is not None:
            policy_rules = _profile_review_rules(
                runtime_job.profile,
                workspace.record.profile_policy.canonical_sha256,
            )
        approval_card = None
        if runtime_job is not None and runtime_job.pending_interrupt_id is not None:
            approval_card = runtime_job.approval_card()
        (
            comparison_scene,
            comparison_candidate_ready,
            comparison_source_only,
            comparison_before_label,
            comparison_after_label,
        ) = _hosted_workspace_scene(workspace)
        refine_iteration = runtime_job.turn_index if runtime_job is not None else 0
        expectation_groups: tuple[ExpectationGroupView, ...] = ()
        target_draft = workspace.record.target_draft
        if target_draft is not None and target_draft.ready_for_confirmation:
            if runtime_job is not None and workspace.record.profile_policy is not None:
                expectation_profile = runtime_job.profile
                expectation_sources = workspace.record.profile_policy.rule_sources
            else:
                assert target_draft.target_use is not None
                assert target_draft.target_height_cm is not None
                expectation_resolution = resolve_policy_family(
                    family.profile,
                    description=target_draft.description,
                    target_use=target_draft.target_use,
                    target_height_cm=target_draft.target_height_cm,
                    viewing_use=(target_draft.viewing_use or AssetViewingUse.NORMAL_GAMEPLAY),
                )
                expectation_profile = expectation_resolution.profile
                expectation_sources = expectation_resolution.provenance.rule_sources
            expectation_groups = _expectation_groups(
                target_draft,
                expectation_profile,
                expectation_sources,
            )
        cannot_repair = bool(
            runtime_job
            and runtime_job.result
            and runtime_job.agent_assessment is not None
            and runtime_job.agent_assessment.disposition is AgentDisposition.RETURN_TO_CREATION_TOOL
        )
        preflight_geometry = workspace.record.preflight.geometry
        workflow_failure_message = _persisted_workflow_error_message(workspace.record.error)
        return templates.TemplateResponse(
            request=request,
            name="hosted_workspace.html",
            context={
                "workspace": workspace,
                "record": workspace.record,
                "workflow_failure_message": workflow_failure_message,
                "preflight": workspace.record.preflight,
                "job": runtime_job,
                "inspection": inspection,
                "inspection_checks": (
                    _inspection_checks(runtime_job) if runtime_job is not None else ()
                ),
                "plan": runtime_job.selected_plan if runtime_job is not None else None,
                "verification": (
                    runtime_job.last_verification if runtime_job is not None else None
                ),
                "comparison_scene": comparison_scene,
                "comparison_candidate_ready": comparison_candidate_ready,
                "shepherded_download_filename": _shepherded_download_filename(
                    workspace.record.asset_name
                ),
                "comparison_source_only": comparison_source_only,
                "comparison_before_label": comparison_before_label,
                "comparison_after_label": comparison_after_label,
                "result_presentation": (
                    _result_presentation(runtime_job) if runtime_job is not None else None
                ),
                "completion_sentence": _completion_sentence(workspace, runtime_job),
                "current_turn_outcome_summary": _current_turn_outcome_summary(
                    workspace, runtime_job
                ),
                "agent_assessment_sentence": _approval_assessment_sentence(runtime_job),
                "current_turn_decision_summary": _current_turn_decision_summary(runtime_job),
                "decision_summary": (
                    _decision_summary(runtime_job) if runtime_job is not None else "pending"
                ),
                "approval_card": approval_card,
                "finding_groups": tuple(finding_groups),
                "policy_rules": policy_rules,
                "target_draft": workspace.record.target_draft,
                "upload_summary": _uploaded_asset_summary(
                    preflight_geometry.bounds.dimensions_m if preflight_geometry else None,
                    preflight_geometry.triangle_count if preflight_geometry else None,
                ),
                "target_notebook_sentence": _target_notebook_sentence(target_draft),
                "expectation_groups": expectation_groups,
                "basis_labels": BASIS_LABELS,
                "target_use_label": (
                    TARGET_USE_LABELS[workspace.record.target_draft.target_use]
                    if workspace.record.target_draft is not None
                    and workspace.record.target_draft.target_use is not None
                    else None
                ),
                "target_height_label": (
                    _display_target_height(workspace.record.target_draft.target_height_cm)
                    if workspace.record.target_draft is not None
                    and workspace.record.target_draft.target_height_cm is not None
                    else None
                ),
                "target_bounds_label": (
                    _display_target_bounds(workspace.record.target_draft.target_dimensions_cm)
                    if workspace.record.target_draft is not None
                    and workspace.record.target_draft.target_dimensions_cm is not None
                    else None
                ),
                "endpoint_label": (
                    workspace.record.target_draft.endpoint_detail
                    if workspace.record.target_draft is not None
                    and workspace.record.target_draft.endpoint is AssetEndpoint.OTHER
                    else ENDPOINT_LABELS.get(workspace.record.target_draft.endpoint)
                    if workspace.record.target_draft is not None
                    and workspace.record.target_draft.endpoint is not None
                    else None
                ),
                "viewing_use_label": (
                    {
                        AssetViewingUse.CLOSE_UP_SHOWCASE: "Hero / close-up",
                        AssetViewingUse.NORMAL_GAMEPLAY: "Normal gameplay",
                        AssetViewingUse.SMALL_DISTANT_REPEATED: "Background / repeated",
                    }[workspace.record.target_draft.viewing_use]
                    if workspace.record.target_draft is not None
                    and workspace.record.target_draft.viewing_use is not None
                    else None
                ),
                "ask_viewing_use": bool(
                    target_draft
                    and not any(
                        item.field == "viewing_use"
                        and item.source
                        in {
                            TargetEvidenceSource.EXPLICIT_USER_TEXT,
                            TargetEvidenceSource.USER_CLARIFICATION,
                        }
                        for item in target_draft.evidence
                    )
                ),
                "command_id": uuid4().hex,
                "remote_commands_enabled": remote_dispatcher is not None,
                "can_continue": bool(
                    runtime_job
                    and runtime_job.agent_orchestrated
                    and runtime_job.turns_remaining > 0
                ),
                "has_candidate": bool(runtime_job and _has_next_turn_candidate(runtime_job)),
                "deferred_simplification": bool(
                    runtime_job
                    and runtime_job.agent_assessment is not None
                    and "SIMPLIFY_MESH" in runtime_job.agent_assessment.deferred_repair_kinds
                ),
                "can_retry_iteration": bool(
                    runtime_job
                    and runtime_job.agent_orchestrated
                    and runtime_job.pending_interrupt_id is None
                    and runtime_job.result is None
                    and (
                        (
                            runtime_job.outcome is not None
                            and runtime_job.outcome.executed_action_ids
                        )
                        or (
                            runtime_job.agent_assessment is None
                            and runtime_job.inspection is not None
                        )
                    )
                ),
                "retry_is_planning": bool(
                    runtime_job
                    and runtime_job.agent_assessment is None
                    and runtime_job.inspection is not None
                ),
                "cannot_repair": cannot_repair,
                "turns_remaining": runtime_job.turns_remaining if runtime_job else 0,
                "prior_turns": runtime_job.prior_turns if runtime_job else (),
                "prior_turn_views": (
                    tuple(_archived_turn_view(workspace, turn) for turn in runtime_job.prior_turns)
                    if runtime_job
                    else ()
                ),
                "error": error,
                "active_mode": "conversation",
                "active_style": workspace.record.asset_name,
                "hosted_step": "refine" if refine_iteration else "shepherd",
                "refine_iteration": refine_iteration,
            },
            status_code=status_code,
            headers={"Cache-Control": "no-store"},
        )

    def require_intent(intent_id: str) -> WebIntent:
        """Resolve only opaque intent IDs created in this local process."""
        intent = store.get_intent(intent_id)
        if intent is None:
            raise UploadValidationError(
                "This intent draft is unavailable. Start again and describe the asset."
            )
        return intent

    def render_intent_clarification(
        request: Request,
        intent: WebIntent,
        error: str | None = None,
        status_code: int = 200,
    ) -> Response:
        """Ask only for required target fields absent from the typed intake contract."""
        target_use_label = (
            TARGET_USE_LABELS[intent.target.target_use]
            if intent.target.target_use is not None
            else None
        )
        return templates.TemplateResponse(
            request=request,
            name="intent_clarify.html",
            context={
                "intent": intent,
                "target_use_label": target_use_label,
                "error": error,
                "active_mode": "confirm",
                "active_style": "Clarify",
            },
            status_code=status_code,
            headers={"Cache-Control": "no-store"},
        )

    def render_intent_confirmation(
        request: Request,
        intent: WebIntent,
        error: str | None = None,
        status_code: int = 200,
    ) -> Response:
        """Render one concise, adjustable proposal before explicit agreement."""
        policy_proposal = _policy_proposal(family, intent)
        return templates.TemplateResponse(
            request=request,
            name="intent.html",
            context={
                "intent": intent,
                "target_use_label": TARGET_USE_LABELS[intent.target_use],
                "target_height_label": _display_target_height(intent.target_height_cm),
                "target_bounds_label": _display_target_bounds(
                    cast(tuple[float, float, float], intent.target.target_dimensions_cm)
                ),
                "endpoint_label": (
                    intent.target.endpoint_detail
                    if intent.target.endpoint is AssetEndpoint.OTHER
                    else ENDPOINT_LABELS[cast(AssetEndpoint, intent.target.endpoint)]
                ),
                "expectation_groups": _expectation_groups(
                    intent.target,
                    policy_proposal.resolution.profile,
                    policy_proposal.resolution.provenance.rule_sources,
                ),
                "error": error,
                "active_mode": "confirm",
                "active_style": "Confirm",
            },
            status_code=status_code,
            headers={"Cache-Control": "no-store"},
        )

    def render_story_home(
        request: Request,
        story: StoryDefinition,
        intent: WebIntent,
        error: str | None = None,
        status_code: int = 200,
    ) -> Response:
        """Render a story-specific intake over the shared workflow."""
        return templates.TemplateResponse(
            request=request,
            name=story.landing_template,
            context={
                "policy_proposal": _policy_proposal(family, intent),
                "stories": STORIES,
                "story": story,
                "intent": intent,
                "target_use_label": TARGET_USE_LABELS[intent.target_use],
                "error": error,
                "max_upload_mb": 50,
                "active_mode": "intake",
                "active_style": "Shepherd",
            },
            status_code=status_code,
            headers={"Cache-Control": "no-store"},
        )

    def require_job(job_id: str) -> WebJob:
        """Resolve only opaque job IDs already present in this process."""
        job = store.get(job_id)
        if job is None:
            raise UploadValidationError(
                "This local job is unavailable. Jobs survive refreshes, not server restarts."
            )
        return job

    def home(request: Request) -> Response:
        """Send public entry traffic to the authoritative hosted workspace."""
        return RedirectResponse(request.url_for("hosted_home"), status_code=303)

    def how_it_works(request: Request) -> Response:
        """Explain the user journey in three concise steps."""
        return templates.TemplateResponse(
            request=request,
            name="how_it_works.html",
            context={
                "active_mode": "help",
                "active_style": "How it works",
            },
            headers={"Cache-Control": "no-store"},
        )

    def what_it_does(request: Request) -> Response:
        """Summarize the three asset-worker problems covered by inspection."""
        return templates.TemplateResponse(
            request=request,
            name="what_it_does.html",
            context={
                "active_mode": "capabilities",
                "active_style": "What it does",
            },
            headers={"Cache-Control": "no-store"},
        )

    def faq(request: Request) -> Response:
        """Answer common product and troubleshooting questions."""
        return templates.TemplateResponse(
            request=request,
            name="faq.html",
            context={
                "active_mode": "faq",
                "active_style": "FAQ",
            },
            headers={"Cache-Control": "no-store"},
        )

    def render_feedback(
        request: Request,
        *,
        context: str,
        reference_id: str,
        return_path: str,
        error: str | None = None,
        note: str = "",
        submitted: bool = False,
        status_code: int = 200,
    ) -> Response:
        """Render the shared contextual feedback page."""
        safe_context = context if context in FEEDBACK_CONTEXTS else "general"
        return templates.TemplateResponse(
            request=request,
            name="feedback.html",
            context={
                "feedback_context": safe_context,
                "feedback_context_label": FEEDBACK_CONTEXTS[safe_context],
                "feedback_reasons": FEEDBACK_REASONS,
                "reference_id": reference_id[:128],
                "return_path": _safe_feedback_return_path(return_path),
                "error": error,
                "note": note,
                "submitted": submitted,
                "active_mode": "feedback",
                "active_style": "Feedback",
            },
            status_code=status_code,
            headers={"Cache-Control": "no-store"},
        )

    def feedback_page(
        request: Request,
        context: str = "general",
        reference_id: str = "",
        return_path: str = "/",
    ) -> Response:
        """Accept feedback links from any workflow surface."""
        return render_feedback(
            request,
            context=context,
            reference_id=reference_id,
            return_path=return_path,
        )

    def submit_feedback(
        request: Request,
        context: Annotated[str, Form(max_length=64)],
        reference_id: Annotated[str, Form(max_length=128)],
        return_path: Annotated[str, Form(max_length=512)],
        reason: Annotated[str, Form(max_length=64)],
        note: Annotated[str, Form(max_length=1000)] = "",
    ) -> Response:
        """Validate and locally record one reusable contextual feedback submission."""
        safe_context = context if context in FEEDBACK_CONTEXTS else "general"
        valid_reasons = {value for value, _ in FEEDBACK_REASONS}
        if reason not in valid_reasons:
            return render_feedback(
                request,
                context=safe_context,
                reference_id=reference_id,
                return_path=return_path,
                error="Choose the option that comes closest.",
                note=note,
                status_code=400,
            )
        _write_feedback_record(
            feedback_root,
            context=safe_context,
            reference_id=reference_id,
            reason=reason,
            note=note.strip(),
        )
        return render_feedback(
            request,
            context=safe_context,
            reference_id=reference_id,
            return_path=return_path,
            submitted=True,
        )

    def create_intent(
        request: Request,
        description: Annotated[str, Form()],
    ) -> Response:
        """Extract a bounded target draft without starting an inspection."""
        values = {"description": description}
        try:
            intent = store.create_intent(description)
        except TargetIntakeContentRefusal as error:
            return render_intent_home(
                request,
                str(error),
                status_code=400,
                refusal=True,
            )
        except (UploadValidationError, ValueError) as error:
            return render_intent_home(request, str(error), status_code=400, values=values)
        return RedirectResponse(
            request.url_for("intent_review", intent_id=intent.intent_id),
            status_code=303,
        )

    def intent_review(request: Request, intent_id: str) -> Response:
        """Show the exact target story awaiting explicit agreement."""
        try:
            intent = require_intent(intent_id)
        except UploadValidationError as error:
            return render_intent_home(request, str(error), status_code=404)
        if not intent.ready_for_confirmation:
            return render_intent_clarification(request, intent)
        return render_intent_confirmation(request, intent)

    def clarify_intent(
        request: Request,
        intent_id: str,
        description: Annotated[str | None, Form()] = None,
        target_use: Annotated[str | None, Form()] = None,
        target_height_m: Annotated[str | None, Form()] = None,
        target_x_m: Annotated[str | None, Form()] = None,
        target_y_m: Annotated[str | None, Form()] = None,
        target_z_m: Annotated[str | None, Form()] = None,
        viewing_use: Annotated[str | None, Form()] = None,
    ) -> Response:
        """Complete only missing minimum target fields and return to proposal review."""
        try:
            intent = require_intent(intent_id)
            if description is not None:
                store.revise_intent(intent, description=description)
            else:
                store.clarify_intent(
                    intent,
                    target_use_value=target_use,
                    target_height_m=target_height_m,
                    target_x_m=target_x_m,
                    target_y_m=target_y_m,
                    target_z_m=target_z_m,
                    viewing_use_value=viewing_use,
                )
        except UploadValidationError as error:
            intent = store.get_intent(intent_id)
            if intent is None:
                return render_intent_home(request, str(error), status_code=404)
            return render_intent_clarification(request, intent, str(error), status_code=400)
        return RedirectResponse(
            request.url_for("intent_review", intent_id=intent_id),
            status_code=303,
        )

    def revise_intent(
        request: Request,
        intent_id: str,
        description: Annotated[str, Form()],
    ) -> Response:
        """Reinterpret an edited description without exposing implementation categories."""
        try:
            intent = require_intent(intent_id)
            store.revise_intent(intent, description=description)
        except UploadValidationError as error:
            intent = store.get_intent(intent_id)
            if intent is None:
                return render_intent_home(request, str(error), status_code=404)
            return render_intent_confirmation(request, intent, str(error), status_code=400)
        return RedirectResponse(
            request.url_for("intent_review", intent_id=intent_id),
            status_code=303,
        )

    def confirm_intent(
        request: Request,
        intent_id: str,
        viewing_use: Annotated[str | None, Form()] = None,
    ) -> Response:
        """Freeze the reviewed target story before exposing upload controls."""
        try:
            intent = require_intent(intent_id)
            store.confirm_intent(intent, viewing_use_value=viewing_use)
        except (UploadValidationError, ValueError) as error:
            intent = store.get_intent(intent_id)
            if intent is None:
                return render_intent_home(request, str(error), status_code=404)
            return render_intent_clarification(request, intent, str(error), status_code=400)
        return RedirectResponse(
            request.url_for("intent_intake", intent_id=intent.intent_id),
            status_code=303,
        )

    def intent_intake(request: Request, intent_id: str) -> Response:
        """Expose policy and upload only after the target story is confirmed."""
        try:
            intent = require_intent(intent_id)
            if intent.confirmed is None:
                return RedirectResponse(
                    request.url_for("intent_review", intent_id=intent.intent_id),
                    status_code=303,
                )
        except UploadValidationError as error:
            return render_intent_home(request, str(error), status_code=404)
        return render_story_home(request, DEFAULT_STORY, intent)

    def story_home(request: Request, story_slug: str) -> Response:
        """Preserve old bookmarks while replacing the role-selector modality."""
        del story_slug
        return RedirectResponse(request.url_for("home"), status_code=303)

    def health() -> dict[str, str]:
        """Return a minimal liveness response without job or credential data."""
        return {"status": "ok"}

    def create_intent_job(
        request: Request,
        intent_id: str,
        asset: Annotated[UploadFile, File()],
        profile_mode: Annotated[str, Form()] = "resolved",
        custom_height_tolerance_cm: Annotated[str | None, Form()] = None,
        custom_require_y_up: Annotated[str | None, Form()] = None,
        custom_require_ground_contact: Annotated[str | None, Form()] = None,
        custom_ground_tolerance_cm: Annotated[str | None, Form()] = None,
        custom_naming_pattern: Annotated[str | None, Form()] = None,
        custom_max_triangles: Annotated[str | None, Form()] = None,
        custom_max_materials: Annotated[str | None, Form()] = None,
        custom_max_textures: Annotated[str | None, Form()] = None,
        custom_max_texture_dimension: Annotated[str | None, Form()] = None,
    ) -> Response:
        """Accept one bounded GLB and advance it to approval or completion."""
        filename = asset.filename or ""
        try:
            intent_draft = require_intent(intent_id)
            if intent_draft.confirmed is None:
                raise UploadValidationError("Agree on the target story before uploading a GLB.")
            custom_values = {
                "custom_height_tolerance_cm": custom_height_tolerance_cm,
                "custom_require_y_up": custom_require_y_up,
                "custom_require_ground_contact": custom_require_ground_contact,
                "custom_ground_tolerance_cm": custom_ground_tolerance_cm,
                "custom_naming_pattern": custom_naming_pattern,
                "custom_max_triangles": custom_max_triangles,
                "custom_max_materials": custom_max_materials,
                "custom_max_textures": custom_max_textures,
                "custom_max_texture_dimension": custom_max_texture_dimension,
            }
            job = store.create(
                filename,
                DEFAULT_STORY,
                intent_draft.confirmed,
                intent_draft.target,
                asset.file,
                profile_mode=profile_mode,
                custom_values=custom_values,
            )
        except UploadValidationError as error:
            intent_draft = store.get_intent(intent_id)
            if intent_draft is None:
                return render_intent_home(request, str(error), status_code=404)
            return render_story_home(
                request,
                DEFAULT_STORY,
                intent_draft,
                str(error),
                status_code=400,
            )
        finally:
            asset.file.close()
        return RedirectResponse(
            f"{request.url_for('job_page', job_id=job.job_id)}?view=inspect",
            status_code=303,
        )

    def job_page(request: Request, job_id: str, view: str | None = None) -> Response:
        """Render refresh-safe in-process state for one opaque job ID."""
        try:
            job = require_job(job_id)
        except UploadValidationError as error:
            return render_intent_home(request, str(error), status_code=404)
        return templates.TemplateResponse(
            request=request,
            name="job.html",
            context=_job_context(job, view),
            headers={"Cache-Control": "no-store"},
        )

    def confirm_inspection(request: Request, job_id: str) -> Response:
        """Acknowledge the inspection summary before exposing the repair decision."""
        try:
            job = require_job(job_id)
        except UploadValidationError as error:
            return render_intent_home(request, str(error), status_code=404)
        if job.runtime.job.inspection is None or job.runtime.job.selected_plan is None:
            return RedirectResponse(
                f"{request.url_for('job_page', job_id=job.job_id)}?view=inspect",
                status_code=303,
            )
        job.inspection_acknowledged = True
        next_view = "decide" if job.waiting_for_approval else "download"
        return RedirectResponse(
            f"{request.url_for('job_page', job_id=job.job_id)}?view={next_view}",
            status_code=303,
        )

    def decide_job(
        request: Request,
        job_id: str,
        interrupt_id: Annotated[str, Form()],
        decision: Annotated[str, Form()],
    ) -> Response:
        """Bind an explicit approve/reject choice to the exact pending interrupt."""
        job: WebJob | None = None
        try:
            job = require_job(job_id)
            if job.waiting_for_approval and not job.inspection_acknowledged:
                return RedirectResponse(
                    f"{request.url_for('job_page', job_id=job.job_id)}?view=inspect",
                    status_code=303,
                )
            if decision not in {"approve", "reject"}:
                raise UploadValidationError("Choose approve or reject for this repair.")
            store.resume(job, interrupt_id, approved=decision == "approve")
        except (UploadValidationError, AgentWorkflowError) as error:
            if job is None:
                return render_intent_home(request, str(error), status_code=404)
            job.error = _public_workflow_error(error)
            return templates.TemplateResponse(
                request=request,
                name="job.html",
                context=_job_context(job, "decide"),
                status_code=409,
                headers={"Cache-Control": "no-store"},
            )
        return RedirectResponse(
            f"{request.url_for('job_page', job_id=job.job_id)}?view=download",
            status_code=303,
        )

    def review_job_result(
        request: Request,
        job_id: str,
        decision: Annotated[str, Form()],
        feedback: Annotated[str, Form()] = "",
    ) -> Response:
        """Accept the result or start another agent turn from concise user feedback."""
        inline_accept = request.headers.get("x-asset-shepherd-transition") == "accept"
        try:
            job = require_job(job_id)
            if job.workflow_result is None or job.runtime.job.result is None:
                raise UploadValidationError("Finish the current repair turn first.")
            if job.accepted or job.runtime.job.accepted:
                if decision == "accept":
                    if inline_accept:
                        return Response(status_code=204, headers={"Cache-Control": "no-store"})
                    return RedirectResponse(
                        f"{request.url_for('job_page', job_id=job.job_id)}?view=download",
                        status_code=303,
                    )
                raise UploadValidationError("This conversation is already accepted.")
            if decision == "accept":
                job.runtime.job.record_user_acceptance()
                job.accepted = True
                if inline_accept:
                    return Response(status_code=204, headers={"Cache-Control": "no-store"})
                return RedirectResponse(
                    f"{request.url_for('job_page', job_id=job.job_id)}?view=download",
                    status_code=303,
                )
            if decision != "continue":
                raise UploadValidationError("Choose whether the result is right.")
            store.continue_after_feedback(job, feedback)
            return RedirectResponse(
                f"{request.url_for('job_page', job_id=job.job_id)}?view=inspect",
                status_code=303,
            )
        except (UploadValidationError, AgentWorkflowError) as error:
            job = store.get(job_id)
            if job is None:
                return render_intent_home(request, str(error), status_code=404)
            context = _job_context(job, "download")
            context["continuation_error"] = str(error)
            return templates.TemplateResponse(
                request=request,
                name="job.html",
                context=context,
                status_code=400,
                headers={"Cache-Control": "no-store"},
            )

    def source_asset(job_id: str) -> Response:
        """Serve the immutable input to the current repair turn for before preview."""
        job = store.get(job_id)
        if job is None:
            return Response(status_code=404)
        return FileResponse(
            job.runtime.job.source,
            media_type="model/gltf-binary",
            headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
        )

    def repaired_asset(job_id: str) -> Response:
        """Serve only a deterministically verified ready candidate."""
        job = store.get(job_id)
        if job is None or not job.ready_candidate:
            return Response(status_code=404)
        return FileResponse(
            job.output_dir / "repaired.glb",
            media_type="model/gltf-binary",
            filename=_shepherded_download_filename(job.target_intake.asset_name),
            headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
        )

    def rejected_candidate_asset(job_id: str) -> Response:
        """Serve an executed candidate even when automated verification rejected it."""
        job = store.get(job_id)
        if job is None:
            return Response(status_code=404)
        candidate_path = _failed_candidate_path(job.runtime.job)
        if candidate_path is None:
            return Response(status_code=404)
        return FileResponse(
            candidate_path,
            media_type="model/gltf-binary",
            filename=f"{_asset_download_stem(job.target_intake.asset_name)}-candidate.glb",
            headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
        )

    def download_result(job_id: str) -> Response:
        """Download the contracted result ZIP after packaging."""
        job = store.get(job_id)
        if job is None:
            return Response(status_code=404)
        result_zip = job.output_dir / "result.zip"
        if job.runtime.job.result is None or not result_zip.is_file():
            return Response(status_code=404)
        return FileResponse(
            result_zip,
            media_type="application/zip",
            filename=f"{_asset_download_stem(job.target_intake.asset_name)}-evidence.zip",
            headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
        )

    def hosted_home(request: Request) -> Response:
        """Choose an existing asset workspace or a new slot."""
        return render_hosted_home(request)

    def _validate_hosted_replacement(
        replace_workspace_id: str | None,
    ) -> tuple[bool, str | None]:
        records = hosted_store.list_records()
        draft_count = sum(
            draft.replace_workspace_id is None for draft in list_hosted_start_drafts()
        )
        record_ids = {record.workspace_id for record in records}
        if (
            len(records) + draft_count >= MAX_HOSTED_WORKSPACES
            and replace_workspace_id not in record_ids
        ):
            return False, "Choose which existing asset to replace."
        if replace_workspace_id is not None and replace_workspace_id not in record_ids:
            return False, "That asset slot is unavailable."
        return True, None

    def hosted_upload(
        request: Request,
        replace_workspace_id: str | None = None,
    ) -> Response:
        """Begin one new slot by accepting the GLB before semantic intake."""
        valid, error = _validate_hosted_replacement(replace_workspace_id)
        if not valid:
            return render_hosted_home(request, error, status_code=400)
        return render_hosted_upload(
            request,
            replace_workspace_id=replace_workspace_id,
        )

    def upload_hosted_asset(
        request: Request,
        asset: Annotated[UploadFile, File()],
        replace_workspace_id: Annotated[str | None, Form()] = None,
        replace_draft_id: Annotated[str | None, Form()] = None,
        agent_model: Annotated[str | None, Form()] = None,
    ) -> Response:
        """Validate and stage one GLB, then advance to description."""
        with gallery_mutation_lock:
            replaced_draft: HostedStartDraft | None = None
            if replace_draft_id:
                try:
                    replaced_draft = require_hosted_start_draft(replace_draft_id)
                except HostedWorkspaceError as draft_error:
                    asset.file.close()
                    return render_hosted_upload(request, str(draft_error), status_code=404)
                replace_workspace_id = replaced_draft.replace_workspace_id
                if agent_model is None:
                    agent_model = replaced_draft.model_id
            valid, error = _validate_hosted_replacement(replace_workspace_id)
            if not valid:
                asset.file.close()
                return render_hosted_home(request, error, status_code=400)
            filename = asset.filename or ""
            if Path(filename).suffix.lower() != ".glb":
                asset.file.close()
                return render_hosted_upload(
                    request,
                    "Choose exactly one file with a .glb extension.",
                    status_code=400,
                    replace_workspace_id=replace_workspace_id,
                )
            selected_model_id: str | None = None
            if agent_model_choices:
                selected_model_id = agent_model or (
                    default_agent_model.model_id if default_agent_model is not None else None
                )
                try:
                    selected_capability = resolve_hosted_model(selected_model_id or "")
                    if selected_capability not in agent_model_choices:
                        raise ValueError
                except ValueError:
                    asset.file.close()
                    return render_hosted_upload(
                        request,
                        "Choose an available Asset Shepherd model.",
                        status_code=400,
                        replace_workspace_id=replace_workspace_id,
                    )
            draft_id = uuid4().hex
            draft_root = hosted_staging_root / draft_id
            source_path = draft_root / "source.glb"
            try:
                draft_root.mkdir(parents=True, exist_ok=False)
                copy_validated_upload(asset.file, source_path)
                draft = HostedStartDraft(
                    draft_id=draft_id,
                    original_filename=Path(filename).name,
                    source_path=source_path,
                    replace_workspace_id=replace_workspace_id,
                    model_id=selected_model_id,
                )
                persist_hosted_start_draft(draft)
                with hosted_start_lock:
                    hosted_start_drafts[draft_id] = draft

                def retire_previous_upload() -> None:
                    if replaced_draft is not None:
                        discard_hosted_start_draft(replaced_draft)

                upload_checks.start(draft_root, retire_previous_upload)
                check = upload_checks.status(draft_root)
                if check is not None and check.state == "FAILED":
                    raise HostedWorkspaceError(check.error or "This GLB could not be checked.")
            except (HostedWorkspaceError, ValueError, OSError) as upload_error:
                with hosted_start_lock:
                    hosted_start_drafts.pop(draft_id, None)
                source_path.unlink(missing_ok=True)
                for name in ("draft.json", "upload-check.json"):
                    (draft_root / name).unlink(missing_ok=True)
                if draft_root.is_dir():
                    draft_root.rmdir()
                return render_hosted_upload(
                    request,
                    str(upload_error),
                    status_code=400,
                    replace_workspace_id=replace_workspace_id,
                )
            finally:
                asset.file.close()
            return RedirectResponse(
                request.url_for("hosted_describe", draft_id=draft_id),
                status_code=303,
            )

    def save_hosted_description(
        request: Request,
        draft_id: str,
        description: Annotated[str, Form()],
    ) -> Response:
        """Infer the target, then create the durable shepherding workspace."""
        with gallery_mutation_lock:
            try:
                draft = require_hosted_start_draft(draft_id)
            except HostedWorkspaceError as draft_error:
                return render_hosted_upload(request, str(draft_error), status_code=404)
            check = upload_checks.status(draft.source_path.parent)
            if check is None:
                try:
                    upload_checks.start(draft.source_path.parent)
                except ValueError as error:
                    return render_hosted_upload(request, str(error), status_code=409)
                check = upload_checks.status(draft.source_path.parent)
            if check is not None and check.state != "READY":
                return render_upload_check(request, draft, status_code=409)
            try:
                normalized = normalize_intent_description(description)
                target_analyzer = (
                    build_target_intake_analyzer(model_values(draft.model_id))
                    if draft.model_id is not None
                    else hosted_store.intake_analyzer
                )
                target_draft = target_analyzer.analyze(normalized)
            except TargetIntakeContentRefusal as error:
                discard_hosted_start_draft(draft)
                return render_hosted_describe(
                    request,
                    None,
                    str(error),
                    status_code=400,
                    refusal=True,
                )
            except ValueError as error:
                return render_hosted_describe(
                    request,
                    draft,
                    str(error),
                    status_code=400,
                    description=description,
                )
            try:
                with draft.source_path.open("rb") as stream:
                    workspace = hosted_store.create(
                        normalized,
                        draft.original_filename,
                        stream,
                        replace_workspace_id=draft.replace_workspace_id,
                        target_draft=target_draft,
                        model_provider=("bedrock-converse" if draft.model_id is not None else None),
                        model_id=draft.model_id,
                        preflight_result=check.preflight if check is not None else None,
                    )
            except (HostedWorkspaceError, ValueError, OSError) as error:
                return render_hosted_describe(
                    request,
                    draft,
                    str(error),
                    status_code=400,
                    description=description,
                )
            discard_hosted_start_draft(draft)
            return RedirectResponse(
                _workspace_notebook_url(request, workspace.record.workspace_id),
                status_code=303,
            )

    def require_hosted_start_draft(draft_id: str) -> HostedStartDraft:
        if re.fullmatch(r"[0-9a-f]{32}", draft_id) is None:
            raise HostedWorkspaceError("This upload is unavailable. Choose the GLB again.")
        with hosted_start_lock:
            draft = hosted_start_drafts.get(draft_id)
            if draft is None:
                draft = load_hosted_start_draft(draft_id)
                if draft is not None:
                    hosted_start_drafts[draft_id] = draft
        if draft is None or not draft.source_path.is_file():
            raise HostedWorkspaceError("This upload is unavailable. Choose the GLB again.")
        return draft

    def discard_hosted_start_draft(draft: HostedStartDraft) -> None:
        """Remove one exact staged source after completion or terminal refusal."""
        with hosted_start_lock:
            hosted_start_drafts.pop(draft.draft_id, None)
        draft.source_path.unlink(missing_ok=True)
        draft_root = draft.source_path.parent
        if draft_root.parent == hosted_staging_root and draft_root.is_dir():
            (draft_root / "draft.json").unlink(missing_ok=True)
            (draft_root / "upload-check.json").unlink(missing_ok=True)
            draft_root.rmdir()

    def hosted_describe(request: Request, draft_id: str) -> Response:
        """Describe the model after its GLB has passed objective preflight."""
        try:
            draft = require_hosted_start_draft(draft_id)
        except HostedWorkspaceError as error:
            return render_hosted_upload(request, str(error), status_code=404)
        check = upload_checks.status(draft.source_path.parent)
        if check is None:
            try:
                upload_checks.start(draft.source_path.parent)
            except ValueError as error:
                return render_hosted_upload(request, str(error), status_code=409)
            check = upload_checks.status(draft.source_path.parent)
        if check is not None and check.state != "READY":
            return render_upload_check(request, draft)
        return render_hosted_describe(request, draft)

    def render_upload_check(
        request: Request, draft: HostedStartDraft, *, status_code: int = 200
    ) -> Response:
        check = upload_checks.status(draft.source_path.parent)
        return templates.TemplateResponse(
            request=request,
            name="hosted_upload_check.html",
            context={
                "draft": draft,
                "check": check,
                "active_mode": "conversation",
                "active_style": "Upload",
                "hosted_step": "upload",
            },
            status_code=status_code,
            headers={"Cache-Control": "no-store"},
        )

    def hosted_upload_status(request: Request, draft_id: str) -> Response:
        try:
            draft = require_hosted_start_draft(draft_id)
        except HostedWorkspaceError as error:
            return JSONResponse({"error": str(error)}, status_code=404)
        check = upload_checks.status(draft.source_path.parent)
        return JSONResponse(
            {
                "state": check.state if check is not None else "READY",
                "error": check.error if check is not None else None,
                "next_url": str(request.url_for("hosted_describe", draft_id=draft_id)),
            },
            headers={"Cache-Control": "no-store"},
        )

    def retry_upload_check(request: Request, draft_id: str) -> Response:
        with gallery_mutation_lock:
            try:
                draft = require_hosted_start_draft(draft_id)
                check = upload_checks.status(draft.source_path.parent)
                if check is None or check.state == "FAILED":
                    upload_checks.start(draft.source_path.parent)
            except (HostedWorkspaceError, ValueError) as error:
                return render_hosted_upload(request, str(error), status_code=409)
            return RedirectResponse(request.url_for("hosted_describe", draft_id=draft_id), 303)

    def redo_hosted_workspace(request: Request, workspace_id: str) -> Response:
        """Stage the original GLB for a fresh run without discarding saved progress."""
        with gallery_mutation_lock:
            draft_root: Path | None = None
            source_path: Path | None = None
            try:
                workspace = require_hosted_workspace(workspace_id)
                draft_id = uuid4().hex
                draft_root = hosted_staging_root / draft_id
                source_path = draft_root / "source.glb"
                draft_root.mkdir(parents=True, exist_ok=False)
                shutil.copyfile(workspace.source_path, source_path)
                draft = HostedStartDraft(
                    draft_id=draft_id,
                    original_filename=workspace.record.original_filename,
                    source_path=source_path,
                    replace_workspace_id=workspace_id,
                    initial_description=workspace.record.private_description,
                    model_id=workspace.record.model_id,
                )
                persist_hosted_start_draft(draft)
                upload_checks.reuse(draft_root, workspace.record.preflight)
                with hosted_start_lock:
                    hosted_start_drafts[draft_id] = draft
            except (HostedWorkspaceError, OSError) as error:
                if source_path is not None:
                    source_path.unlink(missing_ok=True)
                if draft_root is not None and draft_root.is_dir():
                    draft_root.rmdir()
                return render_hosted_home(request, str(error), status_code=400)
            return RedirectResponse(
                request.url_for("hosted_describe", draft_id=draft_id),
                status_code=303,
            )

    def trash_hosted_workspace(
        request: Request,
        workspace_id: str,
        confirmation: Annotated[str, Form()],
    ) -> Response:
        """Permanently remove a confirmed gallery asset, not merely its tile."""
        if not gallery_mutation_lock.acquire(blocking=False):
            return render_hosted_home(
                request, "An asset operation is running. Try Trash later.", status_code=409
            )
        try:
            if confirmation != workspace_id:
                return render_hosted_home(
                    request, "Confirm the exact asset to trash.", status_code=400
                )
            try:
                drafts = [
                    draft
                    for draft in list_hosted_start_drafts()
                    if draft.replace_workspace_id == workspace_id
                ]
                for draft in drafts:
                    check = upload_checks.status(draft.source_path.parent)
                    if check is not None and check.state == "CHECKING":
                        raise HostedWorkspaceError("Wait for this asset's upload check to finish.")
                hosted_store.trash(workspace_id)
                for draft in drafts:
                    discard_hosted_start_draft(draft)
            except HostedWorkspaceError as error:
                return render_hosted_home(request, str(error), status_code=409)
            except Exception:
                return render_hosted_home(
                    request,
                    "Deletion could not finish. Please retry Trash; the slot is not yet freed.",
                    status_code=503,
                )
            return RedirectResponse(request.url_for("hosted_home"), status_code=303)
        finally:
            gallery_mutation_lock.release()

    def trash_hosted_draft(
        request: Request,
        draft_id: str,
        confirmation: Annotated[str, Form()],
    ) -> Response:
        """Discard an unsubmitted upload and free its reserved gallery slot."""
        if not gallery_mutation_lock.acquire(blocking=False):
            return render_hosted_home(
                request, "An asset operation is running. Try Trash later.", status_code=409
            )
        try:
            if confirmation != draft_id:
                return render_hosted_home(
                    request, "Confirm the exact upload to trash.", status_code=400
                )
            try:
                draft = require_hosted_start_draft(draft_id)
                check = upload_checks.status(draft.source_path.parent)
                if check is not None and check.state == "CHECKING":
                    raise HostedWorkspaceError(
                        "Wait for the upload check to finish before trashing it."
                    )
                discard_hosted_start_draft(draft)
            except (HostedWorkspaceError, OSError) as error:
                return render_hosted_home(request, str(error), status_code=409)
            return RedirectResponse(request.url_for("hosted_home"), status_code=303)
        finally:
            gallery_mutation_lock.release()

    def create_hosted_workspace(
        request: Request,
        description: Annotated[str, Form()],
        asset: Annotated[UploadFile, File()],
        replace_workspace_id: Annotated[str | None, Form()] = None,
    ) -> Response:
        """Accept minimal context and run objective preflight only."""
        filename = asset.filename or ""
        try:
            workspace = hosted_store.create(
                description,
                filename,
                asset.file,
                replace_workspace_id=replace_workspace_id,
            )
        except TargetIntakeContentRefusal as error:
            return render_hosted_home(
                request,
                str(error),
                status_code=400,
                refusal=True,
            )
        except (HostedWorkspaceError, ValueError) as error:
            return render_hosted_home(
                request,
                str(error),
                status_code=400,
                description=description,
            )
        finally:
            asset.file.close()
        return RedirectResponse(
            _workspace_notebook_url(request, workspace.record.workspace_id),
            status_code=303,
        )

    def require_hosted_workspace(workspace_id: str) -> HostedWorkspace:
        """Load only a valid durable workspace beneath the hosted root."""
        workspace = hosted_store.get(workspace_id)
        if workspace is None:
            raise HostedWorkspaceError("This asset workspace is unavailable.")
        return workspace

    def _remote_command_response(
        request: Request, workspace_id: str, command_id: str
    ) -> JSONResponse:
        """Return an accepted receipt that the notebook can poll without holding the request."""
        return JSONResponse(
            {
                "schema_version": 1,
                "state": "QUEUED",
                "status_url": str(
                    request.url_for(
                        "hosted_command_status",
                        workspace_id=workspace_id,
                        command_id=command_id,
                    )
                ),
                "redirect_url": _workspace_notebook_url(request, workspace_id),
            },
            status_code=202,
            headers={"Cache-Control": "private, no-store"},
        )

    def hosted_workspace_page(request: Request, workspace_id: str) -> Response:
        """Resume one durable conversation and Job Contract."""
        try:
            workspace = require_hosted_workspace(workspace_id)
        except HostedWorkspaceError as error:
            return render_hosted_home(request, str(error), status_code=404)
        return render_hosted_workspace(request, workspace)

    def clarify_hosted_target(
        request: Request,
        workspace_id: str,
        command_id: Annotated[str, Form()],
        description: Annotated[str | None, Form()] = None,
        target_use: Annotated[str | None, Form()] = None,
        endpoint: Annotated[str | None, Form()] = None,
        endpoint_detail: Annotated[str | None, Form()] = None,
        viewing_use: Annotated[str | None, Form()] = None,
        target_x_m: Annotated[str | None, Form()] = None,
        target_y_m: Annotated[str | None, Form()] = None,
        target_z_m: Annotated[str | None, Form()] = None,
    ) -> Response:
        """Answer only target fields missing from the durable minimum contract."""
        try:
            workspace = require_hosted_workspace(workspace_id)
            if description is not None:
                hosted_store.reinterpret_target(
                    workspace,
                    description=description,
                    command_id=command_id,
                )
            else:
                hosted_store.clarify_target(
                    workspace,
                    target_use_value=target_use,
                    endpoint_value=endpoint,
                    endpoint_detail=endpoint_detail,
                    viewing_use_value=viewing_use,
                    target_x_m=target_x_m,
                    target_y_m=target_y_m,
                    target_z_m=target_z_m,
                    command_id=command_id,
                )
        except HostedWorkspaceError as error:
            try:
                workspace = require_hosted_workspace(workspace_id)
            except HostedWorkspaceError:
                return render_hosted_home(request, str(error), status_code=404)
            return render_hosted_workspace(request, workspace, str(error), status_code=400)
        return RedirectResponse(
            _workspace_notebook_url(request, workspace_id),
            status_code=303,
        )

    def revise_hosted_target(
        request: Request,
        workspace_id: str,
        command_id: Annotated[str, Form()],
        description: Annotated[str | None, Form()] = None,
        target_use: Annotated[str | None, Form()] = None,
        endpoint: Annotated[str | None, Form()] = None,
        endpoint_detail: Annotated[str | None, Form()] = None,
        viewing_use: Annotated[str | None, Form()] = None,
        target_x_m: Annotated[str | None, Form()] = None,
        target_y_m: Annotated[str | None, Form()] = None,
        target_z_m: Annotated[str | None, Form()] = None,
    ) -> Response:
        """Reinterpret natural-language corrections to an unfrozen target proposal."""
        try:
            workspace = require_hosted_workspace(workspace_id)
            if description is not None:
                hosted_store.reinterpret_target(
                    workspace,
                    description=description,
                    command_id=command_id,
                )
            elif (
                target_use is not None
                and endpoint is not None
                and target_x_m is not None
                and target_y_m is not None
                and target_z_m is not None
                and viewing_use is not None
            ):
                hosted_store.revise_target(
                    workspace,
                    target_use_value=target_use,
                    endpoint_value=endpoint,
                    endpoint_detail=endpoint_detail,
                    viewing_use_value=viewing_use,
                    target_x_m=target_x_m,
                    target_y_m=target_y_m,
                    target_z_m=target_z_m,
                    command_id=command_id,
                )
            else:
                raise HostedWorkspaceError("Describe what the target should be instead.")
        except HostedWorkspaceError as error:
            try:
                workspace = require_hosted_workspace(workspace_id)
            except HostedWorkspaceError:
                return render_hosted_home(request, str(error), status_code=404)
            return render_hosted_workspace(request, workspace, str(error), status_code=400)
        return RedirectResponse(
            _workspace_notebook_url(request, workspace_id),
            status_code=303,
        )

    def confirm_hosted_target(
        request: Request,
        workspace_id: str,
        command_id: Annotated[str, Form()],
        viewing_use: Annotated[str | None, Form()] = None,
        accept_supported_goal: Annotated[str | None, Form()] = None,
        custom_height_tolerance_cm: Annotated[str | None, Form()] = None,
        custom_require_y_up: Annotated[str | None, Form()] = None,
        custom_require_ground_contact: Annotated[str | None, Form()] = None,
        custom_ground_tolerance_cm: Annotated[str | None, Form()] = None,
        custom_naming_pattern: Annotated[str | None, Form()] = None,
        custom_max_triangles: Annotated[str | None, Form()] = None,
        custom_max_materials: Annotated[str | None, Form()] = None,
        custom_max_textures: Annotated[str | None, Form()] = None,
        custom_max_texture_dimension: Annotated[str | None, Form()] = None,
    ) -> Response:
        """Freeze the typed target and derived policy before policy inspection."""
        try:
            workspace = require_hosted_workspace(workspace_id)
            custom_values = {
                "custom_height_tolerance_cm": custom_height_tolerance_cm,
                "custom_require_y_up": custom_require_y_up,
                "custom_require_ground_contact": custom_require_ground_contact,
                "custom_ground_tolerance_cm": custom_ground_tolerance_cm,
                "custom_naming_pattern": custom_naming_pattern,
                "custom_max_triangles": custom_max_triangles,
                "custom_max_materials": custom_max_materials,
                "custom_max_textures": custom_max_textures,
                "custom_max_texture_dimension": custom_max_texture_dimension,
            }
            if remote_dispatcher is not None:
                remote_dispatcher.enqueue(
                    {
                        "schema_version": 1,
                        "operation": "confirm_target",
                        "actor_id": runtime_actor_id,
                        "workspace_id": workspace_id,
                        "command_id": command_id,
                        "accept_supported_goal": accept_supported_goal == "true",
                        "viewing_use": viewing_use,
                        "custom_values": custom_values,
                    }
                )
                return _remote_command_response(request, workspace_id, command_id)
            hosted_store.confirm_target(
                workspace,
                accept_supported_goal=accept_supported_goal == "true",
                command_id=command_id,
                viewing_use_value=viewing_use,
                custom_values=custom_values,
            )
        except (HostedWorkspaceError, AgentCoreDispatchError) as error:
            try:
                workspace = require_hosted_workspace(workspace_id)
            except HostedWorkspaceError:
                return render_hosted_home(request, str(error), status_code=404)
            return render_hosted_workspace(request, workspace, str(error), status_code=400)
        return RedirectResponse(
            _workspace_notebook_url(request, workspace_id),
            status_code=303,
        )

    async def decide_hosted_workspace(
        request: Request,
        workspace_id: str,
        interrupt_id: Annotated[str, Form()],
        decision: Annotated[str, Form()],
        command_id: Annotated[str, Form()],
        response_size_and_pose: Annotated[str | None, Form()] = None,
        comment_size_and_pose: Annotated[str | None, Form()] = None,
        response_topology: Annotated[str | None, Form()] = None,
        comment_topology: Annotated[str | None, Form()] = None,
        response_display_names: Annotated[str | None, Form()] = None,
        comment_display_names: Annotated[str | None, Form()] = None,
        turn_comment: Annotated[str | None, Form()] = None,
    ) -> Response:
        """Bind exact approval or typed plan feedback to the durable Strands interrupt."""
        workspace: HostedWorkspace | None = None
        try:
            workspace = require_hosted_workspace(workspace_id)
            if decision not in {"approve", "reject", "revise"}:
                raise HostedWorkspaceError("Choose approve or reject for this repair.")
            raw_responses = (
                (
                    ProposalLane.SIZE_AND_POSE,
                    response_size_and_pose,
                    comment_size_and_pose,
                ),
                (ProposalLane.TOPOLOGY, response_topology, comment_topology),
                (
                    ProposalLane.DISPLAY_NAMES,
                    response_display_names,
                    comment_display_names,
                ),
            )
            responses: list[ProposalResponse] = []
            disposition_values = {
                "accept": ProposalDisposition.ACCEPT,
                "reject": ProposalDisposition.REJECT,
                "comment": ProposalDisposition.COMMENT,
            }
            for lane, raw_disposition, raw_comment in raw_responses:
                if raw_disposition is None:
                    continue
                disposition = disposition_values.get(raw_disposition)
                if disposition is None:
                    raise HostedWorkspaceError("A proposed-change response is invalid.")
                comment = raw_comment.strip() if raw_comment else None
                if disposition is ProposalDisposition.COMMENT and not comment:
                    raise HostedWorkspaceError("Add a comment for the proposed change.")
                responses.append(
                    ProposalResponse(
                        lane=lane,
                        disposition=disposition,
                        comment=comment if disposition is ProposalDisposition.COMMENT else None,
                    )
                )
            general_comment = turn_comment.strip() if turn_comment else None
            if general_comment:
                responses.append(
                    ProposalResponse(
                        lane=ProposalLane.GENERAL,
                        disposition=ProposalDisposition.COMMENT,
                        comment=general_comment,
                    )
                )
            submitted_form = await request.form()
            component_prefix = "response_component_"
            component_choices: dict[str, str] = {}
            for field_name, raw_value in submitted_form.multi_items():
                if field_name.startswith(component_prefix):
                    component_id = field_name.removeprefix(component_prefix)
                    if component_id in component_choices:
                        raise HostedWorkspaceError("A component selection was submitted twice.")
                    component_choices[component_id] = str(raw_value)
            if component_choices:
                if workspace.runtime is None:
                    raise HostedWorkspaceError(
                        "The component selection is unavailable. Reload this page."
                    )
                components = tuple(
                    component
                    for check in _inspection_checks(workspace.runtime.job)
                    for component in check.component_proposals
                )
                _validate_component_choices(components, component_choices)
            for field_name, raw_value in submitted_form.multi_items():
                if not field_name.startswith(component_prefix):
                    continue
                component_id = field_name.removeprefix(component_prefix)
                raw_disposition = str(raw_value)
                disposition = disposition_values.get(raw_disposition)
                requested_remove = raw_disposition == "request_remove"
                if requested_remove:
                    disposition = ProposalDisposition.COMMENT
                if disposition is None:
                    raise HostedWorkspaceError("A component response is invalid.")
                raw_comment = submitted_form.get(f"comment_component_{component_id}")
                comment = str(raw_comment).strip() if raw_comment else None
                if requested_remove:
                    comment = "Remove this currently retained component in the revised plan."
                elif disposition is ProposalDisposition.COMMENT and not comment:
                    raise HostedWorkspaceError("Add a comment for the proposed component.")
                responses.append(
                    ProposalResponse(
                        lane=ProposalLane.TOPOLOGY,
                        component_id=component_id,
                        disposition=disposition,
                        comment=comment if disposition is ProposalDisposition.COMMENT else None,
                    )
                )
            requests_revision = any(
                response.disposition is not ProposalDisposition.ACCEPT for response in responses
            )
            if decision == "revise" or requests_revision:
                if remote_dispatcher is not None:
                    remote_dispatcher.enqueue(
                        {
                            "schema_version": 1,
                            "operation": "revise_plan",
                            "actor_id": runtime_actor_id,
                            "workspace_id": workspace_id,
                            "command_id": command_id,
                            "interrupt_id": interrupt_id,
                            "responses": [
                                response.model_dump(mode="json") for response in responses
                            ],
                        }
                    )
                    return _remote_command_response(request, workspace_id, command_id)
                hosted_store.revise_plan(
                    workspace,
                    interrupt_id=interrupt_id,
                    responses=tuple(responses),
                    command_id=command_id,
                )
            else:
                if remote_dispatcher is not None:
                    remote_dispatcher.enqueue(
                        {
                            "schema_version": 1,
                            "operation": "decision",
                            "actor_id": runtime_actor_id,
                            "workspace_id": workspace_id,
                            "command_id": command_id,
                            "interrupt_id": interrupt_id,
                            "approved": decision == "approve",
                        }
                    )
                    return _remote_command_response(request, workspace_id, command_id)
                hosted_store.decide(
                    workspace,
                    interrupt_id=interrupt_id,
                    approved=decision == "approve",
                    command_id=command_id,
                )
        except (
            HostedWorkspaceError,
            AgentCoreDispatchError,
            AgentWorkflowError,
            ValueError,
        ) as error:
            if workspace is None:
                return render_hosted_home(request, str(error), status_code=404)
            return render_hosted_workspace(request, workspace, str(error), status_code=409)
        return RedirectResponse(
            _workspace_notebook_url(request, workspace_id),
            status_code=303,
        )

    def review_hosted_result(
        request: Request,
        workspace_id: str,
        decision: Annotated[str, Form()],
        command_id: Annotated[str, Form()],
        feedback: Annotated[str, Form()] = "",
        continue_from: Annotated[str, Form()] = "candidate",
    ) -> Response:
        """Accept a hosted result or continue the durable agent loop."""
        try:
            workspace = require_hosted_workspace(workspace_id)
            if decision not in {"accept", "continue"}:
                raise HostedWorkspaceError("Choose whether the result is right.")
            if remote_dispatcher is not None:
                remote_dispatcher.enqueue(
                    {
                        "schema_version": 1,
                        "operation": "review_result",
                        "actor_id": runtime_actor_id,
                        "workspace_id": workspace_id,
                        "command_id": command_id,
                        "accepted": decision == "accept",
                        "feedback": feedback,
                        "continuation_source": continue_from.upper(),
                    }
                )
                return _remote_command_response(request, workspace_id, command_id)
            hosted_store.review_result(
                workspace,
                accepted=decision == "accept",
                feedback=feedback,
                command_id=command_id,
                continuation_source=cast(Literal["INPUT", "CANDIDATE"], continue_from.upper()),
            )
        except (HostedWorkspaceError, AgentCoreDispatchError) as error:
            try:
                workspace = require_hosted_workspace(workspace_id)
            except HostedWorkspaceError:
                return render_hosted_home(request, str(error), status_code=404)
            return render_hosted_workspace(request, workspace, str(error), status_code=400)
        if decision == "accept" and request.headers.get("x-asset-shepherd-transition") == "accept":
            return Response(status_code=204, headers={"Cache-Control": "no-store"})
        return RedirectResponse(
            _workspace_notebook_url(request, workspace_id),
            status_code=303,
        )

    def retry_hosted_iteration(
        request: Request,
        workspace_id: str,
        command_id: Annotated[str, Form()],
    ) -> Response:
        """Resume only the unfinished evidence and packaging portion of one iteration."""
        try:
            workspace = require_hosted_workspace(workspace_id)
            if remote_dispatcher is not None:
                remote_dispatcher.enqueue(
                    {
                        "schema_version": 1,
                        "operation": "retry",
                        "actor_id": runtime_actor_id,
                        "workspace_id": workspace_id,
                        "command_id": command_id,
                    }
                )
                return _remote_command_response(request, workspace_id, command_id)
            hosted_store.retry_incomplete_turn(workspace, command_id=command_id)
        except (HostedWorkspaceError, AgentCoreDispatchError) as error:
            try:
                workspace = require_hosted_workspace(workspace_id)
            except HostedWorkspaceError:
                return render_hosted_home(request, str(error), status_code=404)
            return render_hosted_workspace(request, workspace, str(error), status_code=409)
        return RedirectResponse(
            _workspace_notebook_url(request, workspace_id),
            status_code=303,
        )

    def hosted_source_asset(workspace_id: str) -> Response:
        """Serve the immutable input to the current hosted repair turn."""
        source_path = hosted_store.source_path(workspace_id)
        if source_path is None:
            return Response(status_code=404)
        return FileResponse(
            source_path,
            media_type="model/gltf-binary",
            headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
        )

    def hosted_original_source_asset(workspace_id: str) -> Response:
        """Serve the immutable R0 upload for its historical notebook cell."""
        source_path = hosted_store.original_source_path(workspace_id)
        if source_path is None:
            return Response(status_code=404)
        return FileResponse(
            source_path,
            media_type="model/gltf-binary",
            headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
        )

    def hosted_source_scene(request: Request, workspace_id: str) -> Response:
        """Render the uploaded notebook state only when that earlier cell becomes active."""
        source_path = hosted_store.original_source_path(workspace_id)
        if source_path is None:
            return Response(status_code=404)
        try:
            scene = _source_scene(source_path)
        except (OSError, ValueError):
            return Response(status_code=404)
        return templates.TemplateResponse(
            request=request,
            name="_model_comparison.html",
            context={
                "comparison_scene": scene,
                "comparison_candidate_ready": False,
                "comparison_source_only": True,
                "comparison_before_label": "Uploaded model",
                "comparison_after_label": "",
                "comparison_source_url": request.url_for(
                    "hosted_original_source_asset",
                    workspace_id=workspace_id,
                ),
            },
            headers={"Cache-Control": "private, no-store"},
        )

    def hosted_turn_asset(workspace_id: str, turn_index: int) -> Response:
        """Serve the immutable hash-bound output of one completed notebook turn."""
        source_path = hosted_store.archived_turn_output_path(workspace_id, turn_index)
        if source_path is None:
            return Response(status_code=404)
        return FileResponse(
            source_path,
            media_type="model/gltf-binary",
            headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
        )

    def hosted_turn_scene(request: Request, workspace_id: str, turn_index: int) -> Response:
        """Render a completed turn only when its notebook scene becomes active."""
        source_path = hosted_store.archived_turn_output_path(workspace_id, turn_index)
        if source_path is None:
            return Response(status_code=404)
        try:
            scene = _source_scene(source_path)
        except (OSError, ValueError):
            return Response(status_code=404)
        return templates.TemplateResponse(
            request=request,
            name="_model_comparison.html",
            context={
                "comparison_scene": scene,
                "comparison_candidate_ready": False,
                "comparison_source_only": True,
                "comparison_before_label": f"Iteration {turn_index + 1}",
                "comparison_after_label": "",
                "comparison_source_url": request.url_for(
                    "hosted_turn_asset",
                    workspace_id=workspace_id,
                    turn_index=turn_index,
                ),
            },
            headers={"Cache-Control": "private, no-store"},
        )

    def hosted_workspace_activity(workspace_id: str) -> Response:
        """Expose concise observable tool activity without model reasoning or transcript text."""
        activity = hosted_store.activity(workspace_id)
        if activity is None:
            return Response(status_code=404)
        return JSONResponse(activity, headers={"Cache-Control": "private, no-store"})

    def hosted_command_status(workspace_id: str, command_id: str) -> Response:
        """Expose one actor-bound dispatch receipt for notebook polling."""
        if remote_dispatcher is None:
            return Response(status_code=404)
        if (
            re.fullmatch(r"[0-9a-f]{32}", workspace_id) is None
            or re.fullmatch(r"[0-9a-f]{32}", command_id) is None
        ):
            return Response(status_code=404)
        status = remote_dispatcher.status(workspace_id, command_id)
        if status is None:
            return Response(status_code=404)
        status["redirect_url"] = f"/workspace/{workspace_id}#current-turn"
        return JSONResponse(status, headers={"Cache-Control": "private, no-store"})

    def hosted_draft_source_asset(draft_id: str) -> Response:
        """Serve a staged GLB preview for a resumable description draft."""
        try:
            draft = require_hosted_start_draft(draft_id)
        except HostedWorkspaceError:
            return Response(status_code=404)
        check = upload_checks.status(draft.source_path.parent)
        if check is None or check.state != "READY":
            return Response(status_code=409)
        return FileResponse(
            draft.source_path,
            media_type="model/gltf-binary",
            headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
        )

    def hosted_repaired_asset(workspace_id: str) -> Response:
        """Serve only a verified hosted candidate."""
        workspace = hosted_store.get(workspace_id)
        if workspace is None or not workspace.ready_candidate:
            return Response(status_code=404)
        return FileResponse(
            workspace.output_dir / "repaired.glb",
            media_type="model/gltf-binary",
            filename=_shepherded_download_filename(workspace.record.asset_name),
            headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
        )

    def hosted_rejected_candidate_asset(workspace_id: str) -> Response:
        """Serve an executed candidate even when automated verification rejected it."""
        workspace = hosted_store.get(workspace_id)
        if workspace is None or workspace.runtime is None:
            return Response(status_code=404)
        candidate_path = _failed_candidate_path(workspace.runtime.job)
        if candidate_path is None:
            return Response(status_code=404)
        return FileResponse(
            candidate_path,
            media_type="model/gltf-binary",
            filename=f"{_asset_download_stem(workspace.record.asset_name)}-candidate.glb",
            headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
        )

    def download_hosted_result(workspace_id: str) -> Response:
        """Serve the contracted package from a completed durable workspace."""
        workspace = hosted_store.get(workspace_id)
        result_zip = workspace.output_dir / "result.zip" if workspace is not None else None
        if (
            workspace is None
            or workspace.runtime is None
            or workspace.runtime.job.result is None
            or result_zip is None
            or not result_zip.is_file()
        ):
            return Response(status_code=404)
        return FileResponse(
            result_zip,
            media_type="application/zip",
            filename=f"{_asset_download_stem(workspace.record.asset_name)}-evidence.zip",
            headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
        )

    app.add_api_route("/", home, methods=["GET"], response_class=HTMLResponse, name="home")
    app.add_api_route(
        "/how-it-works",
        how_it_works,
        methods=["GET"],
        response_class=HTMLResponse,
        name="how_it_works",
    )
    app.add_api_route(
        "/what-it-does",
        what_it_does,
        methods=["GET"],
        response_class=HTMLResponse,
        name="what_it_does",
    )
    app.add_api_route(
        "/faq",
        faq,
        methods=["GET"],
        response_class=HTMLResponse,
        name="faq",
    )
    app.add_api_route(
        "/feedback",
        feedback_page,
        methods=["GET"],
        response_class=HTMLResponse,
        name="feedback_page",
    )
    app.add_api_route(
        "/feedback",
        submit_feedback,
        methods=["POST"],
        response_class=HTMLResponse,
        name="submit_feedback",
    )
    app.add_api_route(
        "/intents",
        create_intent,
        methods=["POST"],
        name="create_intent",
    )
    app.add_api_route(
        "/intents/{intent_id}",
        intent_review,
        methods=["GET"],
        response_class=HTMLResponse,
        name="intent_review",
    )
    app.add_api_route(
        "/intents/{intent_id}/clarify",
        clarify_intent,
        methods=["POST"],
        name="clarify_intent",
    )
    app.add_api_route(
        "/intents/{intent_id}/revise",
        revise_intent,
        methods=["POST"],
        name="revise_intent",
    )
    app.add_api_route(
        "/intents/{intent_id}/agree",
        confirm_intent,
        methods=["POST"],
        name="confirm_intent",
    )
    app.add_api_route(
        "/intents/{intent_id}/intake",
        intent_intake,
        methods=["GET"],
        response_class=HTMLResponse,
        name="intent_intake",
    )
    app.add_api_route(
        "/stories/{story_slug}",
        story_home,
        methods=["GET"],
        response_class=HTMLResponse,
        name="story_home",
    )
    app.add_api_route("/healthz", health, methods=["GET"], name="health")
    app.add_api_route(
        "/intents/{intent_id}/jobs",
        create_intent_job,
        methods=["POST"],
        name="create_intent_job",
    )
    app.add_api_route(
        "/jobs/{job_id}",
        job_page,
        methods=["GET"],
        response_class=HTMLResponse,
        name="job_page",
    )
    app.add_api_route(
        "/jobs/{job_id}/inspection/confirm",
        confirm_inspection,
        methods=["POST"],
        name="confirm_inspection",
    )
    app.add_api_route(
        "/jobs/{job_id}/decision",
        decide_job,
        methods=["POST"],
        name="decide_job",
    )
    app.add_api_route(
        "/jobs/{job_id}/result",
        review_job_result,
        methods=["POST"],
        name="review_job_result",
    )
    app.add_api_route(
        "/jobs/{job_id}/source.glb",
        source_asset,
        methods=["GET"],
        name="source_asset",
    )
    app.add_api_route(
        "/jobs/{job_id}/repaired.glb",
        repaired_asset,
        methods=["GET"],
        name="repaired_asset",
    )
    app.add_api_route(
        "/jobs/{job_id}/candidate-preview.glb",
        rejected_candidate_asset,
        methods=["GET"],
        name="rejected_candidate_asset",
    )
    app.add_api_route(
        "/jobs/{job_id}/download",
        download_result,
        methods=["GET"],
        name="download_result",
    )
    app.add_api_route(
        "/workspace",
        hosted_home,
        methods=["GET"],
        response_class=HTMLResponse,
        name="hosted_home",
    )
    app.add_api_route(
        "/workspace/new/upload",
        hosted_upload,
        methods=["GET"],
        response_class=HTMLResponse,
        name="hosted_upload",
    )
    app.add_api_route(
        "/workspace/new/upload",
        upload_hosted_asset,
        methods=["POST"],
        name="upload_hosted_asset",
    )
    app.add_api_route(
        "/workspace/new/{draft_id}/upload-status",
        hosted_upload_status,
        methods=["GET"],
        name="hosted_upload_status",
    )
    app.add_api_route(
        "/workspace/new/{draft_id}/check",
        retry_upload_check,
        methods=["POST"],
        name="retry_upload_check",
    )
    app.add_api_route(
        "/workspace/new/{draft_id}/describe",
        hosted_describe,
        methods=["GET"],
        response_class=HTMLResponse,
        name="hosted_describe",
    )
    app.add_api_route(
        "/workspace/new/{draft_id}/describe",
        save_hosted_description,
        methods=["POST"],
        name="save_hosted_description",
    )
    app.add_api_route(
        "/workspace",
        create_hosted_workspace,
        methods=["POST"],
        name="create_hosted_workspace",
    )
    app.add_api_route(
        "/workspace/{workspace_id}",
        hosted_workspace_page,
        methods=["GET"],
        response_class=HTMLResponse,
        name="hosted_workspace_page",
    )
    app.add_api_route(
        "/workspace/{workspace_id}/redo",
        redo_hosted_workspace,
        methods=["POST"],
        name="redo_hosted_workspace",
    )
    app.add_api_route(
        "/workspace/{workspace_id}/trash",
        trash_hosted_workspace,
        methods=["POST"],
        name="trash_hosted_workspace",
    )
    app.add_api_route(
        "/workspace/new/{draft_id}/trash",
        trash_hosted_draft,
        methods=["POST"],
        name="trash_hosted_draft",
    )
    app.add_api_route(
        "/workspace/{workspace_id}/target",
        confirm_hosted_target,
        methods=["POST"],
        name="confirm_hosted_target",
    )
    app.add_api_route(
        "/workspace/{workspace_id}/target/clarify",
        clarify_hosted_target,
        methods=["POST"],
        name="clarify_hosted_target",
    )
    app.add_api_route(
        "/workspace/{workspace_id}/target/revise",
        revise_hosted_target,
        methods=["POST"],
        name="revise_hosted_target",
    )
    app.add_api_route(
        "/workspace/{workspace_id}/decision",
        decide_hosted_workspace,
        methods=["POST"],
        name="decide_hosted_workspace",
    )
    app.add_api_route(
        "/workspace/{workspace_id}/result",
        review_hosted_result,
        methods=["POST"],
        name="review_hosted_result",
    )
    app.add_api_route(
        "/workspace/{workspace_id}/retry",
        retry_hosted_iteration,
        methods=["POST"],
        name="retry_hosted_iteration",
    )
    app.add_api_route(
        "/workspace/{workspace_id}/source.glb",
        hosted_source_asset,
        methods=["GET"],
        name="hosted_source_asset",
    )
    app.add_api_route(
        "/workspace/{workspace_id}/uploaded.glb",
        hosted_original_source_asset,
        methods=["GET"],
        name="hosted_original_source_asset",
    )
    app.add_api_route(
        "/workspace/{workspace_id}/source-scene",
        hosted_source_scene,
        methods=["GET"],
        response_class=HTMLResponse,
        name="hosted_source_scene",
    )
    app.add_api_route(
        "/workspace/{workspace_id}/turns/{turn_index}/model.glb",
        hosted_turn_asset,
        methods=["GET"],
        name="hosted_turn_asset",
    )
    app.add_api_route(
        "/workspace/{workspace_id}/turns/{turn_index}/scene",
        hosted_turn_scene,
        methods=["GET"],
        response_class=HTMLResponse,
        name="hosted_turn_scene",
    )
    app.add_api_route(
        "/workspace/{workspace_id}/activity",
        hosted_workspace_activity,
        methods=["GET"],
        name="hosted_workspace_activity",
    )
    app.add_api_route(
        "/workspace/{workspace_id}/commands/{command_id}",
        hosted_command_status,
        methods=["GET"],
        name="hosted_command_status",
    )
    app.add_api_route(
        "/workspace/new/{draft_id}/source.glb",
        hosted_draft_source_asset,
        methods=["GET"],
        name="hosted_draft_source_asset",
    )
    app.add_api_route(
        "/workspace/{workspace_id}/repaired.glb",
        hosted_repaired_asset,
        methods=["GET"],
        name="hosted_repaired_asset",
    )
    app.add_api_route(
        "/workspace/{workspace_id}/candidate-preview.glb",
        hosted_rejected_candidate_asset,
        methods=["GET"],
        name="hosted_rejected_candidate_asset",
    )
    app.add_api_route(
        "/workspace/{workspace_id}/download",
        download_hosted_result,
        methods=["GET"],
        name="download_hosted_result",
    )
    return app


app = create_app()
