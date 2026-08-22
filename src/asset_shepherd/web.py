"""Local FastAPI product surface for the Asset Shepherd workflow."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from threading import RLock
from typing import Annotated, BinaryIO, cast
from uuid import uuid4

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import JsonValue, ValidationError
from strands.agent import AgentResult

from asset_shepherd.agent_job import AgentJob, AgentWorkflowError
from asset_shepherd.agent_runtime import AssetShepherdAgent, build_scripted_agent
from asset_shepherd.models import (
    AgentWorkflowResult,
    ApprovalCard,
    DecisionRecord,
    DecisionValue,
    Finding,
    ProfilePolicyProvenance,
    ProjectProfile,
    Severity,
    VerificationState,
)
from asset_shepherd.profile_policy import (
    build_profile_policy_provenance,
    canonical_profile_sha256,
)

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
_PACKAGE_ROOT = Path(__file__).resolve().parent
_DEFAULT_PROJECT_ROOT = _PACKAGE_ROOT.parents[1]
_DEFAULT_WORK_ROOT = _DEFAULT_PROJECT_ROOT / "build" / "web" / "jobs"


class UploadValidationError(ValueError):
    """Raised when a browser upload violates the contracted GLB boundary."""


@dataclass(frozen=True)
class ProfileOption:
    """One trusted, validated profile selectable by its stable identifier."""

    profile_id: str
    name: str
    description: str
    path: Path
    profile: ProjectProfile
    canonical_sha256: str
    summary: tuple[tuple[str, str], ...]
    review_rules: tuple[tuple[str, str], ...]
    form_defaults: dict[str, JsonValue]


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
        "custom_height_target_cm": profile.expected_height_cm.target,
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


def _set_profile_value(profile_data: dict[str, object], path: str, value: JsonValue) -> None:
    section_name, field_name = path.split(".", maxsplit=1)
    section = profile_data.get(section_name)
    if not isinstance(section, dict):
        raise UploadValidationError("The selected preset has an invalid policy structure.")
    section[field_name] = value


def _custom_profile(
    base: ProfileOption,
    values: Mapping[str, str | None],
) -> tuple[ProjectProfile, ProfilePolicyProvenance]:
    """Validate supported target-state overrides and freeze a custom policy copy."""
    naming_pattern = _required_custom_value(values, "custom_naming_pattern")
    if len(naming_pattern) > 128:
        raise UploadValidationError("The naming pattern must be at most 128 characters.")
    if (
        re.fullmatch(
            r"\^\[[A-Za-z0-9_-]+\]\[[A-Za-z0-9_-]+\]\*\$",
            naming_pattern,
        )
        is None
    ):
        raise UploadValidationError(
            "The naming pattern must use two anchored character classes, such as "
            "^[A-Z][A-Za-z0-9_]*$."
        )
    try:
        naming_rule = re.compile(naming_pattern)
    except re.error as error:
        raise UploadValidationError(f"The naming pattern is invalid: {error}.") from error
    if any(naming_rule.fullmatch(name) is None for name in ("Node_000", "Mesh_000")):
        raise UploadValidationError(
            "The naming pattern must allow deterministic names such as Node_000 and Mesh_000."
        )

    candidate_values: dict[str, JsonValue] = {
        "expected_height_cm.target": _custom_float(
            values, "custom_height_target_cm", "Target height"
        ),
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
    base_values = base.profile.model_dump(mode="json")
    explicit_overrides = {
        path: value
        for path, value in candidate_values.items()
        if _nested_profile_value(base_values, path) != value
    }
    if not explicit_overrides:
        raise UploadValidationError(
            "Change at least one supported rule, or use the immutable preset as-is."
        )

    signature_payload = json.dumps(
        {"base_preset_id": base.profile_id, "explicit_overrides": explicit_overrides},
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    frozen_id = f"{base.profile_id}-custom-{sha256(signature_payload).hexdigest()[:12]}"
    resolved_data = base.profile.model_dump(mode="python")
    for path, value in explicit_overrides.items():
        _set_profile_value(resolved_data, path, value)
    resolved_data["profile_id"] = frozen_id
    resolved_data["name"] = f"{base.name} — custom copy"
    try:
        profile = ProjectProfile.model_validate(resolved_data)
    except ValidationError as error:
        first_error = error.errors(include_url=False)[0]
        location = ".".join(str(part) for part in first_error["loc"])
        raise UploadValidationError(
            f"Custom policy is invalid at {location}: {first_error['msg']}."
        ) from error
    policy = build_profile_policy_provenance(
        profile,
        base_preset_id=base.profile_id,
        explicit_overrides=explicit_overrides,
    )
    return profile, policy


def _nested_profile_value(profile_data: Mapping[str, object], path: str) -> object:
    section_name, field_name = path.split(".", maxsplit=1)
    section = profile_data.get(section_name)
    if not isinstance(section, dict):
        raise UploadValidationError("The selected preset has an invalid policy structure.")
    return cast(dict[str, object], section).get(field_name)


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
        JourneyStep("01", "Set policy", "Choose a preset or customize its supported target state."),
        JourneyStep("02", "Upload source", "Bind one untouched GLB to the frozen policy copy."),
        JourneyStep("03", "Inspect", "Review deterministic facts and policy provenance."),
        JourneyStep("04", "Authorize", "Approve or reject the one grouped physical change."),
        JourneyStep("05", "Package", "Download the verified candidate and evidence trail."),
    ),
)

WORKFLOW_STORIES = (*STORIES, ADVANCED_STORY)


@dataclass
class WebJob:
    """In-memory browser session state bound to one isolated on-disk job."""

    job_id: str
    original_filename: str
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


def discover_profiles(project_root: Path) -> tuple[ProfileOption, ...]:
    """Load only repository-owned versioned profiles offered by the web UI."""
    profile_paths = (
        project_root / "profiles" / "unreal_indie_robot.json",
        project_root / "validation" / "profiles" / "small_stylized_static_mesh.json",
    )
    descriptions = {
        "unreal-indie-robot-v1": "1.8 m character-scale static mesh",
        "small-stylized-static-mesh-v1": "0.9-1.5 m compact stylized asset",
    }
    options: list[ProfileOption] = []
    for path in profile_paths:
        profile = ProjectProfile.model_validate_json(path.read_text(encoding="utf-8"))
        canonical_sha256 = canonical_profile_sha256(profile)
        options.append(
            ProfileOption(
                profile_id=profile.profile_id,
                name=profile.name,
                description=descriptions.get(profile.profile_id, profile.asset_type),
                path=path.resolve(strict=True),
                profile=profile,
                canonical_sha256=canonical_sha256,
                summary=_profile_summary(profile),
                review_rules=_profile_review_rules(profile, canonical_sha256),
                form_defaults=_profile_form_defaults(profile),
            )
        )
    return tuple(options)


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


class WebJobStore:
    """Thread-safe in-process job registry with isolated filesystem workspaces."""

    def __init__(self, work_root: Path, profiles: tuple[ProfileOption, ...]) -> None:
        """Create a registry rooted in an ignored, caller-controlled directory."""
        self.work_root = work_root.resolve(strict=False)
        self.profiles = {profile.profile_id: profile for profile in profiles}
        self._jobs: dict[str, WebJob] = {}
        self._lock = RLock()

    def create(
        self,
        original_filename: str,
        story: StoryDefinition,
        profile_id: str,
        stream: BinaryIO,
        *,
        profile_mode: str = "preset",
        custom_values: Mapping[str, str | None] | None = None,
    ) -> WebJob:
        """Validate, isolate, start, and retain one browser-submitted job."""
        if Path(original_filename).suffix.lower() != ".glb":
            raise UploadValidationError("Choose exactly one file with a .glb extension.")
        base_profile = self.profiles.get(profile_id)
        if base_profile is None:
            raise UploadValidationError("Choose one of the available project profiles.")
        if profile_mode == "preset":
            resolved_profile = base_profile.profile
            policy_provenance = build_profile_policy_provenance(
                resolved_profile,
                base_preset_id=base_profile.profile_id,
                explicit_overrides={},
            )
        elif profile_mode == "custom":
            if custom_values is None:
                raise UploadValidationError("Complete the custom policy before uploading.")
            resolved_profile, policy_provenance = _custom_profile(
                base_profile,
                custom_values,
            )
        else:
            raise UploadValidationError("Choose the preset or a validated custom copy.")
        job_id = uuid4().hex
        job_root = self.work_root / job_id
        job_root.mkdir(parents=True, exist_ok=False)
        source_path = job_root / "source.glb"
        profile_path = job_root / "profile.json"
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
        except Exception:
            source_path.unlink(missing_ok=True)
            profile_path.unlink(missing_ok=True)
            job_root.rmdir()
            raise
        frozen_profile = FrozenProfile(
            profile_id=resolved_profile.profile_id,
            name=resolved_profile.name,
            path=profile_path,
            policy_provenance=policy_provenance,
        )
        runtime = build_scripted_agent(
            AgentJob(
                source_path,
                profile_path,
                job_root / "output",
                profile_policy=policy_provenance,
            )
        )
        job = WebJob(
            job_id=job_id,
            original_filename=Path(original_filename).name,
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
    return {
        "job": job,
        "story": job.story,
        "stories": STORIES,
        "active_mode": job.story.slug,
        "active_style": job.story.nav_label,
        "active_view": active_view,
        "workflow_steps": _workflow_steps(job),
        "stages": job.stages(),
        "finding_groups": _finding_groups(job),
        "rule_explanations": {
            finding.id: explanation
            for finding in (core.inspection.findings if core.inspection is not None else ())
            if (explanation := _rule_explanation(finding)) is not None
        },
        "approval_card": job.approval_card(),
        "interrupt_id": core.pending_interrupt_id,
        "inspection": core.inspection,
        "plan": core.selected_plan,
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
) -> FastAPI:
    """Create a local Asset Shepherd web application and isolated job store."""
    profiles = discover_profiles(project_root.resolve(strict=True))
    stories_by_slug = {story.slug: story for story in WORKFLOW_STORIES}
    store = WebJobStore(work_root, profiles)
    templates = Jinja2Templates(directory=_PACKAGE_ROOT / "templates")
    app = FastAPI(
        title="Asset Shepherd",
        description="Inspect, approve, repair, verify, and package one static GLB.",
        docs_url=None,
        redoc_url=None,
    )
    app.mount("/static", StaticFiles(directory=_PACKAGE_ROOT / "static"), name="static")

    def render_concepts(
        request: Request,
        error: str | None = None,
        status_code: int = 200,
    ) -> Response:
        """Render the three-story concept chooser."""
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "stories": STORIES,
                "error": error,
                "active_mode": "help",
                "active_style": "Help me choose",
            },
            status_code=status_code,
            headers={"Cache-Control": "no-store"},
        )

    def require_story(story_slug: str) -> StoryDefinition:
        """Resolve one of the three explicit presentation concepts."""
        story = stories_by_slug.get(story_slug)
        if story is None:
            raise UploadValidationError("Choose one of the three user-story concepts.")
        return story

    def render_story_home(
        request: Request,
        story: StoryDefinition,
        error: str | None = None,
        status_code: int = 200,
    ) -> Response:
        """Render a story-specific intake over the shared workflow."""
        return templates.TemplateResponse(
            request=request,
            name=story.landing_template,
            context={
                "profiles": profiles,
                "stories": STORIES,
                "story": story,
                "error": error,
                "max_upload_mb": 50,
                "active_mode": story.slug,
                "active_style": story.nav_label,
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
        """Show the user-story concept chooser."""
        return render_concepts(request)

    def story_home(request: Request, story_slug: str) -> Response:
        """Show one complete story-specific intake experience."""
        try:
            story = require_story(story_slug)
        except UploadValidationError as error:
            return render_concepts(request, str(error), status_code=404)
        return render_story_home(request, story)

    def health() -> dict[str, str]:
        """Return a minimal liveness response without job or credential data."""
        return {"status": "ok"}

    def create_story_job(
        request: Request,
        story_slug: str,
        profile_id: Annotated[str, Form()],
        asset: Annotated[UploadFile, File()],
        profile_mode: Annotated[str, Form()] = "preset",
        custom_height_target_cm: Annotated[str | None, Form()] = None,
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
            story = require_story(story_slug)
            custom_values = {
                "custom_height_target_cm": custom_height_target_cm,
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
                story,
                profile_id,
                asset.file,
                profile_mode=profile_mode,
                custom_values=custom_values,
            )
        except UploadValidationError as error:
            story = stories_by_slug.get(story_slug)
            if story is None:
                return render_concepts(request, str(error), status_code=404)
            return render_story_home(request, story, str(error), status_code=400)
        finally:
            asset.file.close()
        return RedirectResponse(
            request.url_for("job_page", job_id=job.job_id),
            status_code=303,
        )

    def job_page(request: Request, job_id: str, view: str | None = None) -> Response:
        """Render refresh-safe in-process state for one opaque job ID."""
        try:
            job = require_job(job_id)
        except UploadValidationError as error:
            return render_concepts(request, str(error), status_code=404)
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
                return render_concepts(request, str(error), status_code=404)
            job.error = _public_workflow_error(error)
            return templates.TemplateResponse(
                request=request,
                name="job.html",
                context=_job_context(job, "decide"),
                status_code=409,
                headers={"Cache-Control": "no-store"},
            )
        return RedirectResponse(
            request.url_for("job_page", job_id=job.job_id),
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

    app.add_api_route("/", home, methods=["GET"], response_class=HTMLResponse, name="home")
    app.add_api_route(
        "/stories/{story_slug}",
        story_home,
        methods=["GET"],
        response_class=HTMLResponse,
        name="story_home",
    )
    app.add_api_route("/healthz", health, methods=["GET"], name="health")
    app.add_api_route(
        "/stories/{story_slug}/jobs",
        create_story_job,
        methods=["POST"],
        name="create_story_job",
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
    return app


app = create_app()
