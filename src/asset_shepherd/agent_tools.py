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
        """Inspect the configured GLB and return deterministic structured facts."""
        return self.job.inspect().model_dump(mode="json")

    @tool(name="list_repair_candidates")
    def list_repair_candidates(self) -> dict[str, Any]:
        """Return the registered deterministic version-1 repair candidates."""
        return self.job.list_candidates().model_dump(mode="json")

    @tool(name="select_repair_candidates")
    def select_repair_candidates(self, candidate_ids: list[str]) -> dict[str, Any]:
        """Select registered repair candidates using their exact IDs.

        Args:
            candidate_ids: Candidate IDs chosen from list_repair_candidates. Every AUTO_SAFE ID
                must be included; unregistered IDs are rejected.

        """
        return self.job.select_candidates(candidate_ids).model_dump(mode="json")

    @tool(context=True, name="execute_selected_repairs")
    def execute_selected_repairs(self, tool_context: ToolContext) -> dict[str, Any]:
        """Execute selected repairs after the native approval interrupt, if required."""
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
        """Verify/package a repaired candidate, or package safe diagnostics for a blocked plan."""
        verification, result = self.job.verify_and_package()
        return {
            "verification": verification.model_dump(mode="json"),
            "job_result": None if result is None else result.model_dump(mode="json"),
            "correction_available": (
                verification.state is VerificationState.FAILED and self.job.correction_attempts == 0
            ),
        }

    @tool(name="retry_once_after_verification_failure")
    def retry_once_after_verification_failure(self) -> dict[str, Any]:
        """Reapply the same authorized plan once after deterministic verification failure."""
        return _outcome_json(self.job.retry_once())

    def as_list(self) -> list[Any]:
        """Return only the six contracted tools available to the primary agent."""
        return [
            self.inspect_asset_for_job,
            self.list_repair_candidates,
            self.select_repair_candidates,
            self.execute_selected_repairs,
            self.verify_and_package,
            self.retry_once_after_verification_failure,
        ]
