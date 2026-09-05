"""Replay one saved confirmed target through the selected live provider, without approval."""

import argparse
import json
import os
from hashlib import sha256
from pathlib import Path
from time import perf_counter

from asset_shepherd.agent_job import AgentJob
from asset_shepherd.agent_runtime import build_live_agent
from asset_shepherd.models import AssetIntentProvenance, ProfilePolicyProvenance


def main() -> None:
    """Keep source/target fixed and stop at the first native approval boundary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--provider", choices=("openai", "meta", "bedrock-converse"), required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--reasoning", default="xhigh")
    args = parser.parse_args()
    root: Path = args.source_root
    output: Path = args.output_root
    output.mkdir(parents=True, exist_ok=False)
    workspace = json.loads((root / "workspace.json").read_text(encoding="utf-8"))
    policy = ProfilePolicyProvenance.model_validate_json(json.dumps(workspace["profile_policy"]))
    intent = AssetIntentProvenance.model_validate_json((root / "intent.json").read_text())
    source = root / "source.glb"
    original_hash = sha256(source.read_bytes()).hexdigest()
    job = AgentJob(
        source,
        root / "profile.json",
        output / "output",
        asset_intent=intent,
        profile_policy=policy,
        agent_orchestrated=True,
    )
    values = dict(os.environ)
    # This comparator must not attach to a hosted workspace or its remote session.
    values.pop("ASSET_SHEPHERD_SESSION_BUCKET", None)
    values["ASSET_SHEPHERD_MODEL_PROVIDER"] = args.provider
    values["ASSET_SHEPHERD_MODEL_ID"] = args.model_id
    values["ASSET_SHEPHERD_WORKFLOW_REASONING"] = args.reasoning
    runtime = build_live_agent(
        job, values=values, session_id="saved-assessment", session_root=output / "strands_state"
    )
    start = perf_counter()
    error: str | None = None
    stop_reason: str | None = None
    try:
        result = runtime.start()
        stop_reason = str(result.stop_reason)
    except Exception as exception:
        # Do not print provider exceptions, request bodies, credentials or raw model prose.
        error = type(exception).__name__
    summary = {
        "provider": args.provider,
        "model_id": args.model_id,
        "requested_reasoning": args.reasoning,
        "elapsed_seconds": perf_counter() - start,
        "source_sha256": original_hash,
        "source_unchanged": sha256(source.read_bytes()).hexdigest() == original_hash,
        "stop_reason": stop_reason,
        "error_type": error,
        "assessment": job.agent_assessment.model_dump(mode="json")
        if job.agent_assessment
        else None,
        "approval_pending": job.pending_interrupt_id is not None,
        "candidate_executed": job.outcome is not None,
    }
    (output / "assessment_result.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
