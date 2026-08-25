"""Narrow Strands tools over the deterministic Asset Shepherd core."""

# Strands' overloaded decorator exposes a partially unknown bare-dict schema type to Pyright.
# pyright: reportUnknownVariableType=false

from typing import Any, Literal

from strands import tool
from strands.types.tools import ToolContext

from asset_shepherd.agent_job import (
    GLTF_SOURCE_VIEW_CONTRACT,
    AgentJob,
    AgentWorkflowError,
)
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
        if self.job.agent_orchestrated:
            return self.job.objective_observations()
        return self.job.inspect().model_dump(mode="json")

    @tool(name="render_source_views_for_job")
    def render_source_views_for_job(self) -> dict[str, Any]:
        """Render four coordinate-labeled source views for size, pose, and yaw assessment.

        Call after inspection and before proposing any scale, rotation, or grounding change. The
        images show the GLB after Blender's normal glTF +Y-up to Blender +Z-up import conversion;
        visible vertical therefore corresponds to source +Y. glTF defines source +Z as forward.
        Each image is paired with the source-axis camera direction so the model can check whether
        the semantic front faces +Z. A long visible body axis is not automatically height. Returns
        front, right, back, and left images as model-visible evidence.

        """
        paths = self.job.render_source_views()
        content: list[dict[str, object]] = [
            {
                "text": (
                    "SOURCE GLB AXES: +Y is up, +Z is forward, and -X is right. Blender converted "
                    "+Y-up to visible +Z-up. Use the camera-axis label beside each image to check "
                    "upright pose and yaw; do not infer either from bounds alone."
                )
            }
        ]
        view_labels = GLTF_SOURCE_VIEW_CONTRACT["views"]
        if not isinstance(view_labels, dict):
            raise AgentWorkflowError("The source-view coordinate contract is invalid")
        for path in paths:
            content.append({"text": f"VIEW {path.name}: {view_labels[path.name]}"})
            content.append(
                {
                    "image": {
                        "format": "png",
                        "source": {"bytes": path.read_bytes()},
                    }
                }
            )
        return {
            "status": "success",
            "coordinate_contract": GLTF_SOURCE_VIEW_CONTRACT,
            "content": content,
        }

    @tool(name="render_candidate_views_for_job")
    def render_candidate_views_for_job(self) -> dict[str, Any]:
        """Render the executed candidate for a model-visible before/after comparison.

        Call after an authorized action executes and before verification. Review these views beside
        the previously rendered source views. Returns front, right, back, and left candidate images;
        it does not decide whether the action succeeded.

        """
        paths = self.job.render_candidate_views()
        comparison_paths = self.job.render_candidate_comparison_views()
        content: list[dict[str, object]] = [
            {
                "text": (
                    "Candidate views after the executed action. Compare these with the source "
                    "views before judging whether the proposed result was achieved."
                )
            }
        ]
        view_labels = GLTF_SOURCE_VIEW_CONTRACT["views"]
        if not isinstance(view_labels, dict):
            raise AgentWorkflowError("The source-view coordinate contract is invalid")
        for path in paths:
            content.append({"text": f"CANDIDATE VIEW {path.name}: {view_labels[path.name]}"})
            content.append(
                {
                    "image": {
                        "format": "png",
                        "source": {"bytes": path.read_bytes()},
                    }
                }
            )
        content.append(
            {
                "text": (
                    "SHARED-SCALE COMPARISONS: source and candidate are staged together without "
                    "rescaling. A very small candidate may be hard to see here; use the isolated "
                    "candidate views above to determine whether it is present and preserved."
                )
            }
        )
        for path in comparison_paths:
            content.append({"text": f"SHARED-SCALE VIEW {path.name}: {view_labels[path.name]}"})
            content.append(
                {
                    "image": {
                        "format": "png",
                        "source": {"bytes": path.read_bytes()},
                    }
                }
            )
        return {
            "status": "success",
            "coordinate_contract": GLTF_SOURCE_VIEW_CONTRACT,
            "content": content,
        }

    @tool(context=True, name="record_candidate_reassessment")
    def record_candidate_reassessment(
        self,
        tool_context: ToolContext,
        candidate_satisfies_assessment: bool,
        summary: str,
        evidence: list[str],
        confidence: float,
        source_views_used: list[str],
        candidate_views_used: list[str],
        comparison_views_used: list[str],
    ) -> dict[str, Any]:
        """Record the agent's visual comparison of source and executed candidate.

        Args:
            tool_context: Strands call identity used only for durable provenance.
            candidate_satisfies_assessment: Whether the candidate achieved the proposed result
                without a newly visible problem.
            summary: Concise evidence-grounded comparison for the user and final provenance.
            evidence: Specific observations from both sets of standardized views.
            confidence: Confidence from 0 through 1; uncertainty must remain explicit.
            source_views_used: Exact source filenames consulted.
            candidate_views_used: Exact candidate filenames consulted.
            comparison_views_used: Exact shared-scale comparison filenames consulted.

        A false result prevents project-ready completion. This judgment does not replace independent
        invariant verification and cannot authorize another action.

        """
        reassessment = self.job.register_candidate_reassessment(
            initiating_tool_call_id=tool_context.tool_use["toolUseId"],
            candidate_satisfies_assessment=candidate_satisfies_assessment,
            summary=summary,
            evidence=evidence,
            confidence=confidence,
            source_views_used=source_views_used,
            candidate_views_used=candidate_views_used,
            comparison_views_used=comparison_views_used,
        )
        return reassessment.model_dump(mode="json")

    @tool(context=True, name="propose_agent_repair_plan")
    def propose_agent_repair_plan(
        self,
        tool_context: ToolContext,
        disposition: Literal[
            "ACCEPT",
            "REPAIR",
            "REPORT_ONLY",
            "NEEDS_CLARIFICATION",
            "RETURN_TO_CREATION_TOOL",
        ],
        summary: str,
        evidence: list[str],
        confidence: float,
        semantic_height_axis: Literal["X", "Y", "Z"] | None = None,
        scale_to_confirmed_height: bool = False,
        rotation_axis: Literal["X", "Y", "Z"] | None = None,
        rotation_degrees: Literal[-180, -90, 0, 90, 180] = 0,
        ground_to_y_zero: bool = False,
        rename_invalid_display_names: bool = False,
        weld_identical_vertices: bool = False,
        source_views_used: list[str] | None = None,
    ) -> dict[str, Any]:
        """Register the agent's assessment and preview only its requested supported actions.

        Args:
            tool_context: Strands call identity used only for durable provenance.
            disposition: The evidence-backed next step. Only REPAIR may request mutation.
            summary: Concise user-facing conclusion grounded in the target and observations.
            evidence: Specific measured facts and visual observations supporting the conclusion.
            confidence: Confidence from 0 through 1; ambiguity should lower confidence or stop
                repair.
            semantic_height_axis: Source GLB axis representing real-world height, when scaling.
            scale_to_confirmed_height: Uniformly scale that semantic axis to the confirmed target.
            rotation_axis: Source world axis for a requested quarter-turn rotation, otherwise null.
            rotation_degrees: One bounded right-handed quarter turn; use 0 unless views show a
                defect.
            ground_to_y_zero: Move the post-scale/post-rotation minimum Y exactly to zero.
            rename_invalid_display_names: Apply measured index-preserving policy name replacements.
            weld_identical_vertices: Compact only complete byte-identical vertex tuples when the
                inspection reports a positive attribute-safe merge count. Attribute seams are
                never merged.
            source_views_used: Exact rendered filenames used for a physical conclusion.

        Returns an exact deterministic action preview, authorization classes, and bounds. It never
        adds a scale, rotation, grounding, or rename that was not explicitly requested here. It
        rejects uncited physical actions, unsupported parameters, and repeated planning.

        """
        plan = self.job.register_agent_plan(
            initiating_tool_call_id=tool_context.tool_use["toolUseId"],
            disposition=disposition,
            summary=summary,
            evidence=evidence,
            confidence=confidence,
            semantic_height_axis=semantic_height_axis,
            scale_to_confirmed_height=scale_to_confirmed_height,
            rotation_axis=rotation_axis,
            rotation_degrees=rotation_degrees,
            ground_to_y_zero=ground_to_y_zero,
            rename_invalid_display_names=rename_invalid_display_names,
            weld_identical_vertices=weld_identical_vertices,
            source_views_used=source_views_used or [],
        )
        return plan.model_dump(mode="json")

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
                not self.job.agent_orchestrated
                and verification.state is VerificationState.FAILED
                and self.job.correction_attempts == 0
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

    def as_agent_orchestrated_list(self) -> list[Any]:
        """Return the live model's sensing, disposition, action, and proof tools."""
        return [
            self.inspect_asset_for_job,
            self.render_source_views_for_job,
            self.propose_agent_repair_plan,
            self.execute_selected_repairs,
            self.render_candidate_views_for_job,
            self.record_candidate_reassessment,
            self.verify_and_package,
        ]
