"""Deterministic JSON Schema export for all public version-1 artifacts."""

import argparse
import json
from pathlib import Path
from typing import Final

from pydantic import BaseModel

from asset_shepherd.models import (
    AgentMetrics,
    AgentWorkflowResult,
    ApprovalCard,
    AssetIntentProvenance,
    CandidateRepair,
    Decisions,
    Finding,
    FixtureManifest,
    InspectionResult,
    JobResult,
    PlanSelection,
    ProjectProfile,
    Provenance,
    RepairPlan,
    VerificationResult,
)

SCHEMA_MODELS: Final[dict[str, type[BaseModel]]] = {
    "agent_metrics.schema.json": AgentMetrics,
    "agent_workflow_result.schema.json": AgentWorkflowResult,
    "approval_card.schema.json": ApprovalCard,
    "asset_intent.schema.json": AssetIntentProvenance,
    "candidate_repair.schema.json": CandidateRepair,
    "decisions.schema.json": Decisions,
    "finding.schema.json": Finding,
    "fixture_manifest.schema.json": FixtureManifest,
    "inspection.schema.json": InspectionResult,
    "job_result.schema.json": JobResult,
    "plan_selection.schema.json": PlanSelection,
    "profile.schema.json": ProjectProfile,
    "provenance.schema.json": Provenance,
    "repair_plan.schema.json": RepairPlan,
    "verification.schema.json": VerificationResult,
}


def export_schemas(output_dir: Path) -> tuple[Path, ...]:
    """Write stable Draft 2020-12 schemas and return their paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    for filename, model in sorted(SCHEMA_MODELS.items()):
        schema = model.model_json_schema(mode="serialization")
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = f"https://asset-shepherd.dev/schemas/v1/{filename}"
        payload = json.dumps(schema, indent=2, sort_keys=True)
        path = output_dir / filename
        path.write_text(f"{payload}\n", encoding="utf-8", newline="\n")
        generated.append(path)
    return tuple(generated)


def main() -> None:
    """Export the public contract schemas."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("schemas"))
    args = parser.parse_args()
    export_schemas(args.output)


if __name__ == "__main__":
    main()
