"""Create one saved-target Luna workspace and assess it in AgentCore; never approve repair."""

import argparse
import json
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import cast
from uuid import uuid4

import boto3
from botocore.config import Config

from asset_shepherd.cloud_workspace import S3DynamoWorkspaceRepository
from asset_shepherd.hosted_workspace import HostedWorkspaceStore
from asset_shepherd.models import ProjectProfile
from asset_shepherd.target_intake import TargetIntakeContract


def main() -> None:
    """Use an existing confirmed target without changing or approving the original workspace."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--aws-profile", default="asset-shepherd-admin")
    parser.add_argument("--region", default="us-east-1")
    args = parser.parse_args()
    output: Path = args.output_root
    output.mkdir(parents=True, exist_ok=False)
    session = boto3.Session(profile_name=args.aws_profile, region_name=args.region)
    cf = session.client("cloudformation")
    stack = cf.describe_stacks(StackName="asset-shepherd-agentcore")["Stacks"][0]
    parameters = {item["ParameterKey"]: item["ParameterValue"] for item in stack["Parameters"]}
    runtime_arn = next(
        item["OutputValue"] for item in stack["Outputs"] if item["OutputKey"] == "AgentRuntimeArn"
    )
    repository = S3DynamoWorkspaceRepository(
        bucket=parameters["WorkspaceBucketName"],
        table=parameters["WorkspaceTableName"],
        owner_id=parameters["WorkspaceOwnerId"],
        region=args.region,
        aws_profile=args.aws_profile,
    )
    family = (
        Path(__file__).resolve().parents[1]
        / "src/asset_shepherd/data/unreal_static_game_asset_family.json"
    )
    store = HostedWorkspaceStore(
        output / "hosted",
        ProjectProfile.model_validate_json(family.read_text()),
        workspace_repository=repository,
    )
    root: Path = args.source_root
    saved = json.loads((root / "workspace.json").read_text(encoding="utf-8"))
    target = TargetIntakeContract.model_validate(saved["target_draft"])
    if not target.ready_for_confirmation:
        raise ValueError("Use a saved target with all user choices already supplied")
    source = root / "source.glb"
    original_hash = sha256(source.read_bytes()).hexdigest()
    with source.open("rb") as stream:
        workspace = store.create(
            target.description,
            "smartpad-luna-hosted-probe.glb",
            stream,
            target_draft=target,
            model_provider="openai",
            model_id="gpt-5.6-luna",
        )
    command = {
        "schema_version": 1,
        "operation": "confirm_target",
        "actor_id": parameters["WorkspaceOwnerId"],
        "workspace_id": workspace.record.workspace_id,
        "command_id": uuid4().hex,
        "accept_supported_goal": True,
    }
    (output / "probe-command.json").write_text(json.dumps(command, indent=2), encoding="utf-8")
    print("Created isolated probe workspace:", workspace.record.workspace_id, flush=True)
    client = session.client(
        "bedrock-agentcore", config=Config(read_timeout=600, retries={"total_max_attempts": 1})
    )
    started = perf_counter()
    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            runtimeSessionId=f"workspace-{workspace.record.workspace_id}",
            payload=json.dumps(command).encode(),
        )
        result = json.loads(response["response"].read())
        summary = {
            "workspace_id": workspace.record.workspace_id,
            "elapsed_seconds": round(perf_counter() - started, 2),
            "response": cast(object, result),
            "source_sha256": original_hash,
            "source_unchanged": sha256(source.read_bytes()).hexdigest() == original_hash,
            "approval_sent": False,
        }
    except Exception as error:
        summary = {
            "workspace_id": workspace.record.workspace_id,
            "elapsed_seconds": round(perf_counter() - started, 2),
            "error_type": type(error).__name__,
            "approval_sent": False,
        }
    (output / "probe-result.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
