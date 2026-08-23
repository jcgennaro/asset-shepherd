"""Local FastAPI product surface for the Asset Shepherd workflow."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Annotated, BinaryIO
from uuid import uuid4

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import JsonValue
from strands.agent import AgentResult

from asset_shepherd.agent_job import AgentJob, AgentWorkflowError
from asset_shepherd.agent_runtime import AssetShepherdAgent, build_scripted_agent
from asset_shepherd.hosted_workspace import (
    HostedWorkspace,
    HostedWorkspaceError,
    HostedWorkspaceStore,
)
from asset_shepherd.intake_analyzer import (
    DeterministicTargetIntakeAnalyzer,
    TargetIntakeAnalyzer,
)
from asset_shepherd.intent import (
    TARGET_USE_LABELS,
    build_asset_intent,
    craft_confirmed_story,
    validate_asset_intent,
)
from asset_shepherd.models import (
    ActionClass,
    AgentWorkflowResult,
    ApprovalCard,
    AssetIntentProvenance,
    AssetTargetUse,
    DecisionRecord,
    DecisionValue,
    Finding,
    ProfilePolicyProvenance,
    ProjectProfile,
    RepairEligibility,
    Severity,
    VerificationState,
)
from asset_shepherd.policy_resolution import PolicyResolution, resolve_policy_family
from asset_shepherd.profile_policy import canonical_profile_sha256
from asset_shepherd.target_intake import (
    TargetFieldEvidence,
    TargetIntakeContract,
    clarify_target_intake,
)

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
_PACKAGE_ROOT = Path(__file__).resolve().parent
_DEFAULT_PROJECT_ROOT = _PACKAGE_ROOT.parents[1]
_DEFAULT_WORK_ROOT = _DEFAULT_PROJECT_ROOT / "build" / "web" / "jobs"


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
        authorization.append("safe names automatic")
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
        ("Automatic safe renaming", _yes_no(profile.repair_policy.auto_rename)),
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
        upload_label="Add the original GLB",
        upload_hint="One static mesh · embedded resources · source stays untouched",
        submit_label="Check import readiness",
        job_kicker="Import readiness run",
        job_question="Can this asset enter the project safely?",
        source_label="Downloaded asset",
        candidate_label="Import-ready candidate",
        findings_heading="What needs attention",
        verification_heading="Ready-to-import proof",
        approval_eyebrow="Your one project-impact decision",
        rejection_note=(
            "Rejecting keeps the original physical setup, preserves the unresolved findings, "
            "and still packages safe name repairs."
        ),
        landing_template="story.html",
        steps=(
            JourneyStep(
                "01", "Choose the target", "Select the scale and naming rules your project expects."
            ),
            JourneyStep(
                "02",
                "Upload the original",
                "Hand over one untouched static GLB; the source is preserved.",
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
        intake_eyebrow="Open a protected handoff",
        intake_title="Bring the untouched work",
        profile_label="Choose the delivery target",
        upload_label="Choose your source GLB",
        upload_hint="No topology, UV, material, texture, or artistic edits",
        submit_label="Preview the handoff",
        job_kicker="Protected artist handoff",
        job_question="What changes before delivery—and what remains untouched?",
        source_label="Your untouched work",
        candidate_label="Verified delivery copy",
        findings_heading="Technical handoff notes",
        verification_heading="Preservation checks",
        approval_eyebrow="Your artistic-intent checkpoint",
        rejection_note=(
            "Rejecting keeps your scale and orientation exactly as delivered. The decision and any "
            "remaining physical findings stay visible in the package."
        ),
        landing_template="story.html",
        steps=(
            JourneyStep(
                "01", "Share the untouched work", "The original export is retained byte-for-byte."
            ),
            JourneyStep(
                "02",
                "Inspect without editing",
                "Asset facts are measured before any candidate is written.",
            ),
            JourneyStep(
                "03",
                "Review every proposed change",
                "Safe names are separated from physical, intent-sensitive changes.",
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
        upload_label="Unmodified source artifact",
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
    headline="Set the policy, then run the same guarded workflow.",
    promise=(
        "Customize only rules the deterministic engine enforces; authorization and verification "
        "boundaries stay fixed."
    ),
    intake_eyebrow="Advanced policy intake",
    intake_title="Choose or customize the target rules",
    profile_label="Versioned project policy",
    upload_label="Unmodified source artifact",
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
        JourneyStep("02", "Upload source", "Bind one untouched GLB to the frozen policy copy."),
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
    def draft_story(self) -> str:
        """Build the reviewable story only from a complete minimum contract."""
        return craft_confirmed_story(
            self.original_description,
            self.target_use,
            self.target_height_cm,
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
            return "Stopped safely"
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
    return "The workflow stopped unexpectedly. The source is preserved and no output is ready."


def _display_target_height(height_cm: float) -> str:
    """Format target scale in the most readable metric unit for confirmation."""
    if height_cm < 1.0:
        return f"{height_cm * 10:g} mm"
    if height_cm < 100.0:
        return f"{height_cm:g} cm"
    return f"{height_cm / 100:g} m"


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
        "Static repair boundary",
        "Skins, animation, morph targets, topology, UVs, and artistic edits are inspection-only.",
    ),
    (
        "Content preservation",
        "Geometry, materials, textures, and binary payloads must survive any supported repair.",
    ),
    (
        "Exact authorization",
        "Names may be repaired safely; physical normalization requires approval and independent "
        "verification.",
    ),
)

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
    return labels.get(value or "", "Fixed product boundary")


def _target_expectations(
    target: TargetIntakeContract,
    profile: ProjectProfile,
    policy_sources: Mapping[str, str],
) -> tuple[ExpectationView, ...]:
    """Expose every current target assumption separately from measured GLB facts."""
    if target.target_use is None or target.target_height_cm is None:
        return ()
    evidence = {item.field: item for item in target.evidence}
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
            source=_evidence_source_label(evidence.get("target_use")),
            detail="This is context and a support-boundary check, not a repair preset.",
        ),
        ExpectationView(
            label="Supported outcome",
            value=(
                "Full static inspect → repair → verify workflow"
                if full_static
                else "Static inspection and handoff; no rigging or animation repair"
            ),
            source="Current product boundary",
            detail="The same deterministic checks and safety rules apply to every supported GLB.",
        ),
        ExpectationView(
            label="Real-world size",
            value=f"About {_display_target_height(target.target_height_cm)} tall",
            source=_evidence_source_label(evidence.get("target_height_cm")),
            detail="This target will be compared with measured world-space bounds.",
        ),
        ExpectationView(
            label="Orientation",
            value=orientation_value,
            source=_policy_source_label(policy_sources.get("orientation.require_y_up_geometry")),
            detail="The GLB is measured before any rotation is proposed.",
        ),
        ExpectationView(
            label="Grounding",
            value=grounding_value,
            source=_policy_source_label(policy_sources.get("orientation.require_ground_contact")),
            detail="Hanging or hovering language can remove this target-specific goal.",
        ),
        ExpectationView(
            label="Assembly",
            value="No semantic piece-count assumption",
            source="Unspecified",
            detail=(
                "Inspection reports nodes, meshes, roots, and primitives. Asset Shepherd does not "
                "merge, split, or guess semantic pieces."
            ),
        ),
    )


class WebJobStore:
    """Thread-safe in-process job registry with isolated filesystem workspaces."""

    def __init__(
        self,
        work_root: Path,
        family: PolicyFamilyOption,
        intake_analyzer: TargetIntakeAnalyzer,
    ) -> None:
        """Create a registry rooted in an ignored, caller-controlled directory."""
        self.work_root = work_root.resolve(strict=False)
        self.family = family
        self.intake_analyzer = intake_analyzer
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

    def confirm_intent(self, intent: WebIntent) -> AssetIntentProvenance:
        """Freeze the exact reviewed story once; repeated confirmation is idempotent."""
        with self._lock:
            if not intent.ready_for_confirmation:
                raise UploadValidationError(
                    "Answer the remaining target questions before confirming this story."
                )
            if intent.confirmed is None:
                intent.confirmed = build_asset_intent(
                    intent.original_description,
                    intent.target_use,
                    intent.target_height_cm,
                    intent_id=intent.intent_id,
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
        runtime = build_scripted_agent(
            AgentJob(
                source_path,
                profile_path,
                job_root / "output",
                profile_policy=policy_provenance,
                asset_intent=intent,
            )
        )
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
                job.latest_result = job.runtime.start()
                if job.latest_result.stop_reason != "interrupt":
                    job.workflow_result = job.runtime.complete(job.latest_result)
            except Exception as error:
                job.error = _public_workflow_error(error)

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
            job.latest_result = result
            job.workflow_result = job.runtime.complete(result)


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


def _default_job_view(job: WebJob) -> str:
    """Choose the one workflow step that needs the user's attention now."""
    if job.waiting_for_approval:
        return "decide"
    if job.workflow_result is not None or job.error is not None:
        return "download"
    return "inspect"


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


def _job_context(job: WebJob, requested_view: str | None = None) -> dict[str, object]:
    """Build the template context solely from structured job state."""
    core = job.runtime.job
    verification = core.last_verification
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
    report_only_findings = tuple(
        finding
        for finding in (core.inspection.findings if core.inspection is not None else ())
        if finding.action_class is ActionClass.REPORT_ONLY
    )
    cannot_repair = bool(
        (plan is not None and plan.blocked)
        or (
            core.inspection is not None
            and core.inspection.repair_eligibility is not RepairEligibility.ELIGIBLE_STATIC_MESH
        )
    )
    return {
        "job": job,
        "story": job.story,
        "active_mode": active_view,
        "active_style": active_view.capitalize(),
        "active_view": active_view,
        "workflow_steps": _workflow_steps(job),
        "stages": job.stages(),
        "finding_groups": _finding_groups(job),
        "basis_labels": BASIS_LABELS,
        "target_expectations": _target_expectations(
            job.target_intake,
            core.profile,
            job.profile.policy_provenance.rule_sources,
        ),
        "universal_expectations": UNIVERSAL_EXPECTATIONS,
        "report_only_findings": report_only_findings,
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
        "decision_records": decision_records,
        "is_blocked": bool(
            verification is not None and verification.state is VerificationState.BLOCKED
        ),
    }


def create_app(
    *,
    project_root: Path = _DEFAULT_PROJECT_ROOT,
    work_root: Path = _DEFAULT_WORK_ROOT,
    intake_analyzer: TargetIntakeAnalyzer | None = None,
) -> FastAPI:
    """Create a local Asset Shepherd web application and isolated job store."""
    family = discover_policy_family(project_root.resolve(strict=True))
    analyzer = intake_analyzer or DeterministicTargetIntakeAnalyzer()
    store = WebJobStore(work_root, family, analyzer)
    hosted_store = HostedWorkspaceStore(
        work_root / "hosted",
        family.profile,
        analyzer,
    )
    templates = Jinja2Templates(directory=_PACKAGE_ROOT / "templates")
    app = FastAPI(
        title="Asset Shepherd",
        description="Inspect, approve, repair, verify, and package one static GLB.",
        docs_url=None,
        redoc_url=None,
    )
    app.mount("/static", StaticFiles(directory=_PACKAGE_ROOT / "static"), name="static")

    def render_intent_home(
        request: Request,
        error: str | None = None,
        status_code: int = 200,
        values: Mapping[str, str] | None = None,
    ) -> Response:
        """Render the single intent-first entry point."""
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "error": error,
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
    ) -> Response:
        """Render the versioned D019 conversation-led entry point."""
        return templates.TemplateResponse(
            request=request,
            name="hosted_home.html",
            context={
                "error": error,
                "description": description,
                "active_mode": "conversation",
                "active_style": "New asset",
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
        target_expectations: tuple[ExpectationView, ...] = ()
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
                )
                expectation_profile = expectation_resolution.profile
                expectation_sources = expectation_resolution.provenance.rule_sources
            target_expectations = _target_expectations(
                target_draft,
                expectation_profile,
                expectation_sources,
            )
        return templates.TemplateResponse(
            request=request,
            name="hosted_workspace.html",
            context={
                "workspace": workspace,
                "record": workspace.record,
                "preflight": workspace.record.preflight,
                "job": runtime_job,
                "inspection": inspection,
                "plan": runtime_job.selected_plan if runtime_job is not None else None,
                "verification": (
                    runtime_job.last_verification if runtime_job is not None else None
                ),
                "approval_card": approval_card,
                "finding_groups": tuple(finding_groups),
                "policy_rules": policy_rules,
                "target_draft": workspace.record.target_draft,
                "target_expectations": target_expectations,
                "universal_expectations": UNIVERSAL_EXPECTATIONS,
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
                "command_id": uuid4().hex,
                "error": error,
                "active_mode": "conversation",
                "active_style": "Conversation",
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
                "target_expectations": _target_expectations(
                    intent.target,
                    policy_proposal.resolution.profile,
                    policy_proposal.resolution.provenance.rule_sources,
                ),
                "universal_expectations": UNIVERSAL_EXPECTATIONS,
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
                "active_style": "Rules and upload",
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
        """Ask what the user was trying to make."""
        return render_intent_home(request)

    def how_it_works(request: Request) -> Response:
        """Explain the complete workflow and its safety boundary."""
        return templates.TemplateResponse(
            request=request,
            name="how_it_works.html",
            context={
                "active_mode": "help",
                "active_style": "How it works",
            },
            headers={"Cache-Control": "no-store"},
        )

    def create_intent(
        request: Request,
        description: Annotated[str, Form()],
    ) -> Response:
        """Extract a bounded target draft without starting an inspection."""
        values = {"description": description}
        try:
            intent = store.create_intent(description)
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

    def confirm_intent(request: Request, intent_id: str) -> Response:
        """Freeze the reviewed target story before exposing upload controls."""
        try:
            intent = require_intent(intent_id)
            store.confirm_intent(intent)
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

    def source_asset(job_id: str) -> Response:
        """Serve the immutable uploaded source for the before preview."""
        job = store.get(job_id)
        if job is None:
            return Response(status_code=404)
        return FileResponse(
            job.source_path,
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
            headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
        )

    def download_result(job_id: str) -> Response:
        """Download the safe contracted result ZIP after packaging."""
        job = store.get(job_id)
        if job is None:
            return Response(status_code=404)
        result_zip = job.output_dir / "result.zip"
        if job.runtime.job.result is None or not result_zip.is_file():
            return Response(status_code=404)
        return FileResponse(
            result_zip,
            media_type="application/zip",
            filename=f"asset-shepherd-{job.job_id[:8]}.zip",
            headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
        )

    def hosted_home(request: Request) -> Response:
        """Start a new conversation-led asset workspace."""
        return render_hosted_home(request)

    def create_hosted_workspace(
        request: Request,
        description: Annotated[str, Form()],
        asset: Annotated[UploadFile, File()],
    ) -> Response:
        """Accept minimal context and run objective preflight only."""
        filename = asset.filename or ""
        try:
            workspace = hosted_store.create(description, filename, asset.file)
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
            request.url_for("hosted_workspace_page", workspace_id=workspace.record.workspace_id),
            status_code=303,
        )

    def require_hosted_workspace(workspace_id: str) -> HostedWorkspace:
        """Load only a valid durable workspace beneath the hosted root."""
        workspace = hosted_store.get(workspace_id)
        if workspace is None:
            raise HostedWorkspaceError("This asset workspace is unavailable.")
        return workspace

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
        target_height_m: Annotated[str | None, Form()] = None,
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
                    target_height_m=target_height_m,
                    command_id=command_id,
                )
        except HostedWorkspaceError as error:
            try:
                workspace = require_hosted_workspace(workspace_id)
            except HostedWorkspaceError:
                return render_hosted_home(request, str(error), status_code=404)
            return render_hosted_workspace(request, workspace, str(error), status_code=400)
        return RedirectResponse(
            request.url_for("hosted_workspace_page", workspace_id=workspace_id),
            status_code=303,
        )

    def revise_hosted_target(
        request: Request,
        workspace_id: str,
        command_id: Annotated[str, Form()],
        description: Annotated[str | None, Form()] = None,
        target_use: Annotated[str | None, Form()] = None,
        target_height_m: Annotated[str | None, Form()] = None,
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
            elif target_use is not None and target_height_m is not None:
                hosted_store.revise_target(
                    workspace,
                    target_use_value=target_use,
                    target_height_m=target_height_m,
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
            request.url_for("hosted_workspace_page", workspace_id=workspace_id),
            status_code=303,
        )

    def confirm_hosted_target(
        request: Request,
        workspace_id: str,
        command_id: Annotated[str, Form()],
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
            hosted_store.confirm_target(
                workspace,
                accept_supported_goal=accept_supported_goal == "true",
                command_id=command_id,
                custom_values={
                    "custom_height_tolerance_cm": custom_height_tolerance_cm,
                    "custom_require_y_up": custom_require_y_up,
                    "custom_require_ground_contact": custom_require_ground_contact,
                    "custom_ground_tolerance_cm": custom_ground_tolerance_cm,
                    "custom_naming_pattern": custom_naming_pattern,
                    "custom_max_triangles": custom_max_triangles,
                    "custom_max_materials": custom_max_materials,
                    "custom_max_textures": custom_max_textures,
                    "custom_max_texture_dimension": custom_max_texture_dimension,
                },
            )
        except HostedWorkspaceError as error:
            try:
                workspace = require_hosted_workspace(workspace_id)
            except HostedWorkspaceError:
                return render_hosted_home(request, str(error), status_code=404)
            return render_hosted_workspace(request, workspace, str(error), status_code=400)
        return RedirectResponse(
            request.url_for("hosted_workspace_page", workspace_id=workspace_id),
            status_code=303,
        )

    def decide_hosted_workspace(
        request: Request,
        workspace_id: str,
        interrupt_id: Annotated[str, Form()],
        decision: Annotated[str, Form()],
        command_id: Annotated[str, Form()],
    ) -> Response:
        """Bind a structured decision to the exact durable Strands interrupt."""
        workspace: HostedWorkspace | None = None
        try:
            workspace = require_hosted_workspace(workspace_id)
            if decision not in {"approve", "reject"}:
                raise HostedWorkspaceError("Choose approve or reject for this repair.")
            hosted_store.decide(
                workspace,
                interrupt_id=interrupt_id,
                approved=decision == "approve",
                command_id=command_id,
            )
        except (HostedWorkspaceError, AgentWorkflowError) as error:
            if workspace is None:
                return render_hosted_home(request, str(error), status_code=404)
            return render_hosted_workspace(request, workspace, str(error), status_code=409)
        return RedirectResponse(
            request.url_for("hosted_workspace_page", workspace_id=workspace_id),
            status_code=303,
        )

    def ask_hosted_workspace(
        request: Request,
        workspace_id: str,
        category: Annotated[str, Form()],
    ) -> Response:
        """Answer one bounded question strictly from recorded job evidence."""
        try:
            workspace = require_hosted_workspace(workspace_id)
            if category not in {"measurements", "materials", "authorization", "result"}:
                raise HostedWorkspaceError("Choose one of the supported evidence questions.")
            hosted_store.answer_evidence_question(workspace, category)
        except HostedWorkspaceError as error:
            return render_hosted_home(request, str(error), status_code=404)
        return RedirectResponse(
            request.url_for("hosted_workspace_page", workspace_id=workspace_id),
            status_code=303,
        )

    def hosted_source_asset(workspace_id: str) -> Response:
        """Serve one immutable hosted source GLB."""
        workspace = hosted_store.get(workspace_id)
        if workspace is None:
            return Response(status_code=404)
        return FileResponse(
            workspace.source_path,
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
            filename=f"asset-shepherd-{workspace_id[:8]}.zip",
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
        "/jobs/{job_id}/decision",
        decide_job,
        methods=["POST"],
        name="decide_job",
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
        "/workspace/{workspace_id}/ask",
        ask_hosted_workspace,
        methods=["POST"],
        name="ask_hosted_workspace",
    )
    app.add_api_route(
        "/workspace/{workspace_id}/source.glb",
        hosted_source_asset,
        methods=["GET"],
        name="hosted_source_asset",
    )
    app.add_api_route(
        "/workspace/{workspace_id}/repaired.glb",
        hosted_repaired_asset,
        methods=["GET"],
        name="hosted_repaired_asset",
    )
    app.add_api_route(
        "/workspace/{workspace_id}/download",
        download_hosted_result,
        methods=["GET"],
        name="download_hosted_result",
    )
    return app


app = create_app()
