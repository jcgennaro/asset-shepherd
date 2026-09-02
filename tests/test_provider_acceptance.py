"""Provider acceptance contracts fail closed before live approval."""

from pathlib import Path

from asset_shepherd.models import (
    ActionClass,
    CandidateRepair,
    ComponentRemovalPayload,
    ComponentRemovalPrimitivePayload,
    RepairKind,
    RepairPlan,
)
from asset_shepherd.provider_acceptance import (
    aggregate_acceptance_summaries,
    evaluate_selected_plan,
    load_acceptance_manifest,
    resolve_case_source,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPOSITORY_ROOT / "validation" / "provider-acceptance" / "cases.json"


def test_provider_acceptance_manifest_binds_eight_cases_and_all_tracked_hashes() -> None:
    """The checked-in matrix is fixed and every distributable source is hash-bound."""
    manifest = load_acceptance_manifest(MANIFEST)

    assert len(manifest.cases) == 8
    assert manifest.semantic_minimum_passes == 7
    assert manifest.safety_requires_all_cases is True
    assert manifest.globally_forbidden_action_kinds == (RepairKind.WELD_IDENTICAL_VERTICES,)
    for case in manifest.cases:
        resolution = resolve_case_source(case, REPOSITORY_ROOT)
        if case.source_availability == "tracked":
            assert resolution.available is True
            assert resolution.hash_matches is True


def test_riding_crop_allows_exact_component_removal_but_rejects_welding() -> None:
    """A semantic removal case cannot weaken the global seam-preservation stop rule."""
    manifest = load_acceptance_manifest(MANIFEST)
    case = next(case for case in manifest.cases if case.case_id == "riding-crop-component-choice")
    plan = RepairPlan(
        plan_id="agent-plan-61a4d1de6c828e25-v1",
        inspection_id="inspection-61a4d1de6c828e25-p1",
        profile_id="test-profile",
        profile_version=1,
        source_sha256=case.source_sha256,
        candidates=(
            CandidateRepair(
                id="remove-disconnected-components-v1",
                kind=RepairKind.REMOVE_DISCONNECTED_COMPONENTS,
                action_class=ActionClass.APPROVAL_REQUIRED,
                finding_ids=("finding-disconnected-components-detected",),
                description="Remove one exact labeled duplicate component.",
                payload=ComponentRemovalPayload(
                    consequence_summary=(
                        "Remove one exact duplicate while preserving retained data."
                    ),
                    primitives=(
                        ComponentRemovalPrimitivePayload(
                            mesh_index=0,
                            primitive_index=0,
                            before_triangle_count=10,
                            after_triangle_count=7,
                            removed_triangle_count=3,
                            removed_component_ids=("component-duplicate",),
                            retained_component_ids=("component-primary",),
                        ),
                    ),
                ),
            ),
        ),
        auto_action_ids=(),
        approval_action_ids=("remove-disconnected-components-v1",),
        blocked=False,
        blocked_reasons=(),
    )

    accepted = evaluate_selected_plan(
        case,
        plan,
        globally_forbidden=manifest.globally_forbidden_action_kinds,
    )

    assert accepted.passed is True
    assert accepted.selected_action_kinds == (RepairKind.REMOVE_DISCONNECTED_COMPONENTS,)


def test_missing_required_action_fails_before_approval() -> None:
    """A plausible but incomplete plan cannot count as a semantic pass."""
    manifest = load_acceptance_manifest(MANIFEST)
    case = next(case for case in manifest.cases if case.case_id == "broken-normalization")

    evaluated = evaluate_selected_plan(
        case,
        None,
        globally_forbidden=manifest.globally_forbidden_action_kinds,
    )

    assert evaluated.passed is False
    assert evaluated.reasons == ("Missing required action kinds: NORMALIZATION_TRANSFORM.",)


def test_split_passing_runs_aggregate_without_replacing_passes_with_failures() -> None:
    """A bounded rerun can close a matrix without paying to repeat prior successful cases."""
    manifest = load_acceptance_manifest(MANIFEST)
    summaries: list[tuple[str, dict[str, object]]] = []
    for index, case in enumerate(manifest.cases):
        summaries.append(
            (
                f"run-{index:02d}",
                {
                    "provider": "bedrock-converse",
                    "model_id": "test-model",
                    "case_results": [
                        {
                            "case_id": case.case_id,
                            "expected_source_sha256": case.source_sha256,
                            "safety_pass": True,
                            "semantic_pass": True,
                            "metrics": {
                                "invocation_duration_seconds": 1.5,
                                "token_usage": {
                                    "input_tokens": 10,
                                    "output_tokens": 2,
                                    "total_tokens": 12,
                                },
                            },
                        }
                    ],
                },
            )
        )
    first_case = manifest.cases[0]
    summaries.append(
        (
            "run-99",
            {
                "provider": "bedrock-converse",
                "model_id": "test-model",
                "case_results": [
                    {
                        "case_id": first_case.case_id,
                        "expected_source_sha256": first_case.source_sha256,
                        "safety_pass": False,
                        "semantic_pass": False,
                    }
                ],
            },
        )
    )

    aggregate = aggregate_acceptance_summaries(
        manifest,
        summaries,
        provider="bedrock-converse",
        model_id="test-model",
    )

    assert aggregate["release_gate"] == "PASSED"
    assert aggregate["safety_passes"] == 8
    assert aggregate["semantic_passes"] == 8
    assert aggregate["missing_cases"] == []
    assert aggregate["metrics"] == {
        "invocation_duration_seconds": 12.0,
        "token_usage": {
            "input_tokens": 80,
            "output_tokens": 16,
            "total_tokens": 96,
        },
    }
