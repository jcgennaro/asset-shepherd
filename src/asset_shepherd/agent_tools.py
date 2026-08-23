"""Narrow Strands tools over the deterministic Asset Shepherd core."""

# Strands' overloaded decorator exposes a partially unknown bare-dict schema type to Pyright.
# pyright: reportUnknownVariableType=false

from typing import Any

from strands import tool
from strands.types.tools import ToolContext

from asset_shepherd.agent_job import AgentJob, AgentWorkflowError
from asset_shepherd.models import ApprovalResponse, VerificationState
from asset_shepherd.repair import RepairOutcome

APPROVAL_INTERRUPT_NAME = "asset-shepherd-normalization-approval-v1"


def _outcome_json(outcome: RepairOutcome) -> dict[str, Any]:
    return {
        "source_sha256": outcome.source_sha256,
        "output_sha256": outcome.output_sha256,
        "executed_action_ids": list(outcome.executed_action_ids),
        "rejected_action_ids": list(outcome.rejected_action_ids),
    }


class AssetShepherdTools:
    """State-bound tools that never accept model-selected filesystem paths."""

    def __init__(self, job: AgentJob) -> None:
        """Bind every tool call to one trusted job workspace."""
        self.job = job

    @tool(name="inspect_asset_for_job")
    def inspect_asset_for_job(self) -> dict[str, Any]:
        """Measure the configured GLB without changing it; always use this first.

        Returns the authoritative inspection, including measured package and geometry facts,
        eligibility, findings, evidence, and rule provenance. Raises a workflow error when the
        configured input cannot be inspected.

        """
        return self.job.inspect().model_dump(mode="json")

    @tool(name="list_repair_candidates")
    def list_repair_candidates(self) -> dict[str, Any]:
        """Build the deterministic repair registry after inspection, without changing the GLB.

        Returns exact candidate IDs, authorization classes, finding links, payload evidence, and
        blocked reasons. Use only these registered candidates in the selection tool.

        """
        return self.job.list_candidates().model_dump(mode="json")

    @tool(name="select_repair_candidates")
    def select_repair_candidates(self, candidate_ids: list[str]) -> dict[str, Any]:
        """Freeze one subset of the registered plan before execution.

        Args:
            candidate_ids: Candidate IDs chosen from list_repair_candidates. Every AUTO_SAFE ID
                must be included; unregistered IDs are rejected.

        Returns the validated plan ID and selected IDs. Raises a workflow error for unknown,
        duplicate, omitted AUTO_SAFE, or repeated selections. This tool performs no mutation.

        """
        return self.job.select_candidates(candidate_ids).model_dump(mode="json")

    @tool(context=True, name="execute_selected_repairs")
    def execute_selected_repairs(self, tool_context: ToolContext) -> dict[str, Any]:
        """Execute the frozen selection, using a native interrupt for physical normalization.

        Call only after selection. The tool supplies the exact approval card and validates the
        returned candidate and interrupt IDs; free text cannot authorize it. A rejection is recorded
        and not executed. Returns source/output hashes and executed/rejected candidate IDs.

        """
        card = self.job.approval_card()
        if card is None:
            return _outcome_json(self.job.execute(approved=None, interrupt_id=None))
        response_value = tool_context.interrupt(
            APPROVAL_INTERRUPT_NAME,
            reason=card.model_dump(mode="json"),
        )
        response = ApprovalResponse.model_validate(response_value)
        if response.candidate_id != card.candidate_id:
            raise AgentWorkflowError("Approval response references a different candidate")
        if self.job.pending_interrupt_id is None:
            raise AgentWorkflowError(
                "Approval response is not associated with a pending interrupt ID"
            )
        outcome = self.job.execute(
            approved=response.approved,
            interrupt_id=self.job.pending_interrupt_id,
        )
        return _outcome_json(outcome)

    @tool(name="verify_and_package")
    def verify_and_package(self) -> dict[str, Any]:
        """Independently reload, verify, and package the selected workflow result.

        Use after execution, rejection, or a blocked plan. Returns the authoritative verification
        state, final job result when complete, remaining warnings, and whether one fresh
        reassessment is available. A failed candidate is never marked ready.

        """
        verification, result = self.job.verify_and_package()
        return {
            "verification": verification.model_dump(mode="json"),
            "job_result": None if result is None else result.model_dump(mode="json"),
            "reassessment_available": (
                verification.state is VerificationState.FAILED and self.job.correction_attempts == 0
            ),
        }

    @tool(name="reassess_candidate_after_verification_failure")
    def reassess_candidate_after_verification_failure(self) -> dict[str, Any]:
        """After a failed verification, derive one fresh plan from the failed on-disk candidate.

        Use only when verify_and_package reports reassessment_available. Returns an unexecuted plan
        and whether it would need a new approval. It never reapplies the old plan or mutates the
        candidate, and a second reassessment raises a workflow error.

        """
        plan = self.job.reassess_candidate_after_failure()
        return {
            "repair_plan": plan.model_dump(mode="json"),
            "requires_new_approval": bool(plan.approval_action_ids),
            "executed": False,
        }

    def as_list(self) -> list[Any]:
        """Return only the six contracted tools available to the primary agent."""
        return [
            self.inspect_asset_for_job,
            self.list_repair_candidates,
            self.select_repair_candidates,
            self.execute_selected_repairs,
            self.verify_and_package,
            self.reassess_candidate_after_verification_failure,
        ]
