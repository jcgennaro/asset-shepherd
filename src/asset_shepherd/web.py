"""Local FastAPI product surface for the Asset Shepherd workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Annotated, BinaryIO
from uuid import uuid4

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from strands.agent import AgentResult

from asset_shepherd.agent_job import AgentJob, AgentWorkflowError
from asset_shepherd.agent_runtime import AssetShepherdAgent, build_scripted_agent
from asset_shepherd.models import (
    AgentWorkflowResult,
    ApprovalCard,
    Finding,
    ProjectProfile,
    Severity,
    VerificationState,
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
        landing_template="story_game_developer.html",
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
        landing_template="story_artist.html",
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
        landing_template="story_technical_artist.html",
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


@dataclass
class WebJob:
    """In-memory browser session state bound to one isolated on-disk job."""

    job_id: str
    original_filename: str
    story: StoryDefinition
    profile: ProfileOption
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
        options.append(
            ProfileOption(
                profile_id=profile.profile_id,
                name=profile.name,
                description=descriptions.get(profile.profile_id, profile.asset_type),
                path=path.resolve(strict=True),
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
    ) -> WebJob:
        """Validate, isolate, start, and retain one browser-submitted job."""
        if Path(original_filename).suffix.lower() != ".glb":
            raise UploadValidationError("Choose exactly one file with a .glb extension.")
        profile = self.profiles.get(profile_id)
        if profile is None:
            raise UploadValidationError("Choose one of the available project profiles.")
        job_id = uuid4().hex
        job_root = self.work_root / job_id
        job_root.mkdir(parents=True, exist_ok=False)
        source_path = job_root / "source.glb"
        try:
            _copy_validated_upload(stream, source_path)
        except Exception:
            source_path.unlink(missing_ok=True)
            job_root.rmdir()
            raise
        runtime = build_scripted_agent(AgentJob(source_path, profile.path, job_root / "output"))
        job = WebJob(
            job_id=job_id,
            original_filename=Path(original_filename).name,
            story=story,
            profile=profile,
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


def _job_context(job: WebJob) -> dict[str, object]:
    """Build the template context solely from structured job state."""
    core = job.runtime.job
    verification = core.last_verification
    return {
        "job": job,
        "story": job.story,
        "stories": STORIES,
        "stages": job.stages(),
        "finding_groups": _finding_groups(job),
        "approval_card": job.approval_card(),
        "interrupt_id": core.pending_interrupt_id,
        "inspection": core.inspection,
        "plan": core.selected_plan,
        "verification": verification,
        "workflow_result": job.workflow_result,
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
    stories_by_slug = {story.slug: story for story in STORIES}
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
            context={"stories": STORIES, "error": error},
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
    ) -> Response:
        """Accept one bounded GLB and advance it to approval or completion."""
        filename = asset.filename or ""
        try:
            story = require_story(story_slug)
            job = store.create(filename, story, profile_id, asset.file)
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

    def job_page(request: Request, job_id: str) -> Response:
        """Render refresh-safe in-process state for one opaque job ID."""
        try:
            job = require_job(job_id)
        except UploadValidationError as error:
            return render_concepts(request, str(error), status_code=404)
        return templates.TemplateResponse(
            request=request,
            name="job.html",
            context=_job_context(job),
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
                context=_job_context(job),
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
