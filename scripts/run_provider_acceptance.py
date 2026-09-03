"""Run the fixed eight-case provider acceptance set through the live Strands workflow."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from asset_shepherd.agent_job import AgentJob, AgentWorkflowError
from asset_shepherd.agent_runtime import AssetShepherdAgent, build_live_agent
from asset_shepherd.intent import build_asset_intent
from asset_shepherd.models import (
    AgentWorkflowResult,
    ApprovalCard,
    AssetEndpoint,
    AssetIntentProvenance,
    AssetTargetUse,
    AssetViewingUse,
    ProjectProfile,
    VerificationState,
)
from asset_shepherd.policy_resolution import resolve_policy_family
from asset_shepherd.provider_acceptance import (
    AcceptanceCase,
    AcceptanceManifest,
    evaluate_selected_plan,
    file_sha256,
    load_acceptance_manifest,
    resolve_case_source,
    write_json,
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("validation/provider-acceptance/cases.json"),
    )
    parser.add_argument("--output-root", type=Path, default=Path("build/provider-acceptance"))
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument(
        "--provider",
        required=True,
        choices=("openai", "bedrock", "bedrock-converse", "gemini", "meta"),
    )
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--aws-profile")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--reasoning")
    parser.add_argument("--approve-safe", action="store_true")
    parser.add_argument(
        "--profile-family",
        type=Path,
        default=Path("profiles/unreal_indie_robot.json"),
    )
    return parser.parse_args()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:80]


def _provider_values(args: argparse.Namespace) -> dict[str, str]:
    values = dict(os.environ)
    values["ASSET_SHEPHERD_MODEL_PROVIDER"] = str(args.provider)
    values["ASSET_SHEPHERD_MODEL_ID"] = str(args.model_id)
    if args.provider in {"bedrock", "bedrock-converse"}:
        values["ASSET_SHEPHERD_AWS_REGION"] = str(args.region)
        if args.aws_profile:
            values["AWS_PROFILE"] = str(args.aws_profile)
    if args.reasoning:
        values["ASSET_SHEPHERD_WORKFLOW_REASONING"] = str(args.reasoning)
    elif args.provider == "bedrock-converse":
        values.pop("ASSET_SHEPHERD_WORKFLOW_REASONING", None)
    return values


def _case_intent(case: AcceptanceCase) -> AssetIntentProvenance:
    viewing_use = AssetViewingUse(case.viewing_use)
    return build_asset_intent(
        case.description,
        AssetTargetUse.STATIC_GAME_ASSET,
        case.target_dimensions_cm[1],
        endpoint=AssetEndpoint.UNREAL,
        target_dimensions_cm=case.target_dimensions_cm,
        viewing_use=viewing_use,
        expected_piece_count=case.expected_piece_count,
        expected_piece_count_evidence=case.expected_piece_count_evidence,
    )


def _complete_after_approval(
    runtime: AssetShepherdAgent,
    job: AgentJob,
    interrupt_id: str,
) -> AgentWorkflowResult:
    resumed = runtime.resume(interrupt_id, approved=True)
    try:
        return runtime.complete(resumed)
    except AgentWorkflowError:
        if job.outcome is None or not job.outcome.executed_action_ids:
            raise
        recovered = runtime.continue_incomplete_turn()
        return runtime.complete(recovered)


def _record_failure(
    path: Path,
    base: dict[str, Any],
    error: Exception | str,
    *,
    source_unchanged: bool,
) -> dict[str, Any]:
    message = str(error)
    record = {
        **base,
        "status": "FAILED",
        "error": message[:2000],
        "source_unchanged": source_unchanged,
        "safety_pass": False,
        "semantic_pass": False,
        "visual_pass": False,
    }
    write_json(path, record)
    return record


def _run_case(
    case: AcceptanceCase,
    manifest: AcceptanceManifest,
    *,
    repository_root: Path,
    run_root: Path,
    family: ProjectProfile,
    provider_values: dict[str, str],
    approve_safe: bool,
) -> dict[str, Any]:
    case_root = run_root / case.case_id
    record_path = case_root / "acceptance_result.json"
    source = resolve_case_source(case, repository_root)
    base: dict[str, Any] = {
        "schema_version": 1,
        "case_id": case.case_id,
        "title": case.title,
        "provider": provider_values["ASSET_SHEPHERD_MODEL_PROVIDER"],
        "model_id": provider_values["ASSET_SHEPHERD_MODEL_ID"],
        "source_path": case.source_path,
        "expected_source_sha256": case.source_sha256,
        "observed_source_sha256": source.observed_sha256,
        "source_availability": case.source_availability,
    }
    if not source.available:
        record = {
            **base,
            "status": "SKIPPED_MISSING_SOURCE",
            "source_unchanged": False,
            "safety_pass": False,
            "semantic_pass": False,
            "visual_pass": False,
        }
        write_json(record_path, record)
        return record
    if not source.hash_matches:
        return _record_failure(
            record_path,
            base,
            "Source hash does not match the frozen acceptance case.",
            source_unchanged=False,
        )

    case_root.mkdir(parents=True, exist_ok=True)
    intent = _case_intent(case)
    policy = resolve_policy_family(
        family,
        description=case.description,
        target_use=AssetTargetUse.STATIC_GAME_ASSET,
        target_height_cm=case.target_dimensions_cm[1],
        viewing_use=AssetViewingUse(case.viewing_use),
    )
    profile_path = case_root / "profile.json"
    intent_path = case_root / "intent.json"
    write_json(profile_path, policy.profile.model_dump(mode="json"))
    write_json(intent_path, intent.model_dump(mode="json"))
    output_dir = case_root / "output"
    job = AgentJob(
        source.path,
        profile_path,
        output_dir,
        profile_policy=policy.provenance,
        asset_intent=intent,
        agent_orchestrated=True,
    )

    try:
        runtime = build_live_agent(
            job,
            session_id=f"acceptance-{run_root.name}-{case.case_id}",
            session_root=case_root / "strands_state",
            values=provider_values,
        )
        started = runtime.start()
        planning_recovery_used = False
        if (
            started.stop_reason != "interrupt"
            and job.inspection is not None
            and job.agent_assessment is None
        ):
            started = runtime.retry_incomplete_planning()
            planning_recovery_used = True
        plan_evaluation = evaluate_selected_plan(
            case,
            job.selected_plan,
            globally_forbidden=manifest.globally_forbidden_action_kinds,
        )
        if not plan_evaluation.passed:
            raise AgentWorkflowError(" ".join(plan_evaluation.reasons))
        approval_action_ids = (
            tuple(job.selected_plan.approval_action_ids) if job.selected_plan is not None else ()
        )
        prepared_plan_recovery_used = False
        if approval_action_ids and started.stop_reason != "interrupt":
            started = runtime.continue_prepared_plan()
            prepared_plan_recovery_used = True
        interrupts = tuple(started.interrupts or ())
        approval_boundary_pass = not approval_action_ids or (
            started.stop_reason == "interrupt" and len(interrupts) == 1
        )
        if not approval_boundary_pass:
            reasons: list[str] = []
            if not approval_boundary_pass:
                reasons.append("Approval-required actions did not stop at one review interrupt.")
            raise AgentWorkflowError(" ".join(reasons))

        completed: AgentWorkflowResult | None = None
        approval_card: ApprovalCard | None = None
        if started.stop_reason == "interrupt":
            if not approve_safe:
                raise AgentWorkflowError(
                    "Safe plan passed, but --approve-safe was not supplied; no mutation occurred."
                )
            interrupt = interrupts[0]
            approval_card = ApprovalCard.model_validate_json(json.dumps(interrupt.reason))
            completed = _complete_after_approval(runtime, job, interrupt.id)
        else:
            completed = runtime.complete(started)

        source_unchanged = file_sha256(source.path) == case.source_sha256
        verification_pass = completed.metrics.final_verification_state in {
            VerificationState.PASSED_PROJECT_READY,
            VerificationState.PASSED_WITH_REMAINING_WARNINGS,
        }
        if case.requires_candidate_visual_confirmation:
            visual_pass = bool(
                job.candidate_reassessment is not None
                and job.candidate_reassessment.candidate_satisfies_assessment
            )
        else:
            visual_pass = True
        safety_pass = bool(
            source_unchanged
            and plan_evaluation.passed
            and approval_boundary_pass
            and verification_pass
        )
        semantic_pass = bool(plan_evaluation.passed and visual_pass)
        record = {
            **base,
            "status": "COMPLETED" if safety_pass else "FAILED",
            "selected_action_ids": list(plan_evaluation.selected_action_ids),
            "selected_action_kinds": [kind.value for kind in plan_evaluation.selected_action_kinds],
            "approval_action_ids": list(approval_action_ids),
            "approval_card": (
                approval_card.model_dump(mode="json") if approval_card is not None else None
            ),
            "approval_boundary_pass": approval_boundary_pass,
            "planning_recovery_used": planning_recovery_used,
            "prepared_plan_recovery_used": prepared_plan_recovery_used,
            "verification_state": completed.metrics.final_verification_state.value,
            "ready_candidate": completed.job_result.ready_candidate,
            "source_unchanged": source_unchanged,
            "candidate_visual_confirmation_required": (case.requires_candidate_visual_confirmation),
            "candidate_visual_reassessment": (
                job.candidate_reassessment.model_dump(mode="json")
                if job.candidate_reassessment is not None
                else None
            ),
            "safety_pass": safety_pass,
            "semantic_pass": semantic_pass,
            "visual_pass": visual_pass,
            "metrics": completed.metrics.model_dump(mode="json"),
            "user_message": completed.user_message,
        }
        write_json(record_path, record)
        return record
    except Exception as error:
        source_unchanged = file_sha256(source.path) == case.source_sha256
        return _record_failure(
            record_path,
            base,
            error,
            source_unchanged=source_unchanged,
        )


def main() -> int:
    """Run selected cases and make the full release gate explicit."""
    args = _arguments()
    repository_root = Path(__file__).resolve().parents[1]
    manifest_path = (repository_root / args.manifest).resolve(strict=True)
    manifest = load_acceptance_manifest(manifest_path)
    case_by_id = {case.case_id: case for case in manifest.cases}
    selected_ids = args.case_ids or list(case_by_id)
    unknown = sorted(set(selected_ids) - set(case_by_id))
    if unknown:
        raise SystemExit(f"Unknown acceptance case: {unknown[0]}")

    family_path = (repository_root / args.profile_family).resolve(strict=True)
    family = ProjectProfile.model_validate_json(family_path.read_text(encoding="utf-8"))
    provider_values = _provider_values(args)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_name = f"{timestamp}-{_slug(args.provider)}-{_slug(args.model_id)}"
    run_root = (repository_root / args.output_root / run_name).resolve(strict=False)
    if run_root.exists():
        raise SystemExit(f"Refusing to overwrite acceptance run: {run_root}")
    run_root.mkdir(parents=True)

    records: list[dict[str, Any]] = []
    for case_id in selected_ids:
        print(json.dumps({"phase": "start", "case_id": case_id}, sort_keys=True), flush=True)
        record = _run_case(
            case_by_id[case_id],
            manifest,
            repository_root=repository_root,
            run_root=run_root,
            family=family,
            provider_values=provider_values,
            approve_safe=args.approve_safe,
        )
        records.append(record)
        print(
            json.dumps(
                {
                    "phase": "complete",
                    "case_id": case_id,
                    "status": record["status"],
                    "safety_pass": record["safety_pass"],
                    "semantic_pass": record["semantic_pass"],
                },
                sort_keys=True,
            ),
            flush=True,
        )

    full_matrix = set(selected_ids) == set(case_by_id) and len(selected_ids) == len(case_by_id)
    safety_passes = sum(bool(record["safety_pass"]) for record in records)
    semantic_passes = sum(bool(record["semantic_pass"]) for record in records)
    missing_cases = [
        record["case_id"] for record in records if record["status"].startswith("SKIPPED")
    ]
    gate_pass = bool(
        full_matrix
        and not missing_cases
        and safety_passes == len(manifest.cases)
        and semantic_passes >= manifest.semantic_minimum_passes
    )
    summary = {
        "schema_version": 1,
        "acceptance_set_id": manifest.acceptance_set_id,
        "provider": args.provider,
        "model_id": args.model_id,
        "run_name": run_name,
        "selected_case_ids": selected_ids,
        "full_matrix": full_matrix,
        "safety_passes": safety_passes,
        "safety_required": len(manifest.cases),
        "semantic_passes": semantic_passes,
        "semantic_required": manifest.semantic_minimum_passes,
        "missing_cases": missing_cases,
        "release_gate": "PASSED" if gate_pass else "FAILED" if full_matrix else "NOT_EVALUATED",
        "case_results": records,
    }
    write_json(run_root / "run_summary.json", summary)
    print(json.dumps({**summary, "case_results": None}, sort_keys=True), flush=True)
    if full_matrix:
        return 0 if gate_pass else 1
    return 0 if all(record["safety_pass"] and record["semantic_pass"] for record in records) else 1


if __name__ == "__main__":
    sys.exit(main())
