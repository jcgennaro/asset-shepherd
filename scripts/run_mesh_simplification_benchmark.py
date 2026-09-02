"""Run one opt-in live-provider mesh-simplification workflow.

This benchmark deliberately starts from an already normalized, immutable GLB so the workflow model
can be evaluated on the new viewing-use decision rather than spending a turn on scale or pose.
Credentials and provider configuration remain environment-owned.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from asset_shepherd.agent_job import AgentJob, AgentWorkflowError
from asset_shepherd.agent_runtime import build_live_agent
from asset_shepherd.intent import build_asset_intent
from asset_shepherd.models import (
    AgentWorkflowResult,
    ApprovalCard,
    AssetEndpoint,
    AssetIntentProvenance,
    AssetTargetUse,
    AssetViewingUse,
    ProjectProfile,
)
from asset_shepherd.policy_resolution import resolve_policy_family


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--profile-family",
        type=Path,
        default=Path("profiles/unreal_indie_robot.json"),
    )
    return parser.parse_args()


def main() -> int:
    """Build a normal-gameplay target, approve the proposed reduction, and save exact metrics."""
    args = _arguments()
    output = args.output.resolve(strict=False)
    if output.exists() and not args.resume:
        raise SystemExit(f"Refusing to overwrite existing benchmark output: {output}")
    if not output.exists() and args.resume:
        raise SystemExit(f"Cannot resume missing benchmark output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    description = (
        "A decorative pet collar with a shattered-heart charm and buckle for Unreal. Its many "
        "small disconnected decorative construction parts are intentional and must be preserved."
    )
    viewing_use = AssetViewingUse.NORMAL_GAMEPLAY
    profile_path = output.parent / "profile.json"
    intent_path = output.parent / "intent.json"
    family = ProjectProfile.model_validate_json(
        args.profile_family.resolve(strict=True).read_text(encoding="utf-8")
    )
    policy = resolve_policy_family(
        family,
        description=description,
        target_use=AssetTargetUse.STATIC_GAME_ASSET,
        target_height_cm=3.0,
        viewing_use=viewing_use,
    )
    policy_provenance = policy.provenance
    if args.resume:
        intent = AssetIntentProvenance.model_validate_json(intent_path.read_text(encoding="utf-8"))
    else:
        profile_path.write_text(
            f"{json.dumps(policy.profile.model_dump(mode='json'), indent=2, sort_keys=True)}\n",
            encoding="utf-8",
            newline="\n",
        )
        intent = build_asset_intent(
            description,
            AssetTargetUse.STATIC_GAME_ASSET,
            3.0,
            endpoint=AssetEndpoint.UNREAL,
            target_dimensions_cm=(15.0, 3.0, 12.0),
            viewing_use=viewing_use,
            expected_piece_count=1,
            expected_piece_count_evidence=(
                "The visually coherent collar is one semantic asset assembled from many "
                "intentional decorative construction parts; preserve all of them."
            ),
        )
        intent_path.write_text(
            f"{json.dumps(intent.model_dump(mode='json'), indent=2, sort_keys=True)}\n",
            encoding="utf-8",
            newline="\n",
        )

    job = AgentJob(
        args.source.resolve(strict=True),
        profile_path,
        output,
        profile_policy=policy_provenance,
        asset_intent=intent,
        agent_orchestrated=True,
    )
    runtime = build_live_agent(
        job,
        session_id=f"mesh-simplification-{output.parent.name}",
        session_root=output.parent / "strands_state",
    )
    completed: AgentWorkflowResult | None = None
    if args.resume:
        if job.pending_interrupt_id is None:
            if job.outcome is None or not job.outcome.executed_action_ids:
                raise AgentWorkflowError(
                    "The saved benchmark has neither a pending approval nor an executed candidate"
                )
            recovered = runtime.continue_incomplete_turn()
            completed = runtime.complete(recovered)
            card = None
            interrupt_id = None
        else:
            card = job.approval_card()
            if card is None:
                raise AgentWorkflowError("The saved benchmark has no approval card")
            interrupt_id = job.pending_interrupt_id
    else:
        interrupted = runtime.start()
        interrupts = tuple(interrupted.interrupts or ())
        if interrupted.stop_reason != "interrupt" or len(interrupts) != 1:
            raise AgentWorkflowError(
                f"The live model did not offer one reviewable simplification plan: {interrupted}"
            )
        interrupt = interrupts[0]
        interrupt_id = interrupt.id
        card = ApprovalCard.model_validate_json(json.dumps(interrupt.reason))
    if card is not None:
        print(
            json.dumps(
                {
                    "phase": "approval",
                    "candidate_id": card.candidate_id,
                    "title": card.title,
                    "consequence_summary": card.consequence_summary,
                },
                sort_keys=True,
            ),
            flush=True,
        )
        if "simplify-mesh-v1" not in card.candidate_id:
            raise AgentWorkflowError(
                f"The live model proposed {card.candidate_id!r}, not mesh simplification"
            )
        assert interrupt_id is not None
        resumed = runtime.resume(interrupt_id, approved=True)
        try:
            completed = runtime.complete(resumed)
        except AgentWorkflowError:
            if job.outcome is None or not job.outcome.executed_action_ids:
                raise
            recovered = runtime.continue_incomplete_turn()
            completed = runtime.complete(recovered)
    if completed is None:
        raise AgentWorkflowError("The benchmark did not produce a completed workflow result")
    print(
        json.dumps(
            {
                "phase": "complete",
                "provider": completed.metrics.provider,
                "model_id": completed.metrics.model_id,
                "verification": completed.metrics.final_verification_state.value,
                "seconds": completed.metrics.invocation_duration_seconds,
                "tokens": (
                    completed.metrics.token_usage.model_dump(mode="json")
                    if completed.metrics.token_usage is not None
                    else None
                ),
                "ready_candidate": completed.job_result.ready_candidate,
                "output": str(output),
            },
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
