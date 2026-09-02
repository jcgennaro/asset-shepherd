"""Provider-neutral acceptance-set contracts and fail-closed scoring."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from asset_shepherd.models import RepairKind, RepairPlan


class AcceptanceCase(BaseModel):
    """One immutable model-provider evaluation case."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    title: str = Field(min_length=3, max_length=100)
    source_path: str = Field(min_length=1)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_availability: Literal["tracked", "local_saved"]
    description: str = Field(min_length=12, max_length=600)
    target_dimensions_cm: tuple[float, float, float]
    viewing_use: Literal[
        "CLOSE_UP_SHOWCASE",
        "NORMAL_GAMEPLAY",
        "SMALL_DISTANT_REPEATED",
    ]
    expected_piece_count: int = Field(ge=1, le=64)
    expected_piece_count_evidence: str = Field(min_length=1, max_length=160)
    allowed_action_kinds: tuple[RepairKind, ...]
    required_action_kinds: tuple[RepairKind, ...] = ()
    requires_candidate_visual_confirmation: bool = False
    evaluation_note: str = Field(min_length=8, max_length=500)

    @model_validator(mode="after")
    def required_actions_are_allowed(self) -> AcceptanceCase:
        """Prevent a case from requiring an action its safety allowlist rejects."""
        if not set(self.required_action_kinds).issubset(self.allowed_action_kinds):
            raise ValueError("Required action kinds must also be allowed")
        if any(value <= 0.0 for value in self.target_dimensions_cm):
            raise ValueError("Target dimensions must be positive")
        return self


class AcceptanceManifest(BaseModel):
    """Versioned acceptance matrix shared by every candidate provider."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    acceptance_set_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    safety_requires_all_cases: Literal[True] = True
    semantic_minimum_passes: int = Field(ge=1)
    globally_forbidden_action_kinds: tuple[RepairKind, ...]
    cases: tuple[AcceptanceCase, ...]

    @model_validator(mode="after")
    def case_inventory_is_valid(self) -> AcceptanceManifest:
        """Bind the release gate to eight uniquely named cases."""
        if len(self.cases) != 8:
            raise ValueError("The provider acceptance set must contain exactly eight cases")
        if len({case.case_id for case in self.cases}) != len(self.cases):
            raise ValueError("Provider acceptance case IDs must be unique")
        if self.semantic_minimum_passes > len(self.cases):
            raise ValueError("Semantic pass threshold cannot exceed the case count")
        for case in self.cases:
            overlap = set(case.allowed_action_kinds) & set(self.globally_forbidden_action_kinds)
            if overlap:
                raise ValueError(
                    f"Case {case.case_id} allows globally forbidden action {next(iter(overlap))}"
                )
        return self


@dataclass(frozen=True)
class SourceResolution:
    """Resolved source state without treating a missing private fixture as a pass."""

    path: Path
    available: bool
    hash_matches: bool
    observed_sha256: str | None


@dataclass(frozen=True)
class PlanEvaluation:
    """Fail-closed comparison of one model-selected plan with a case contract."""

    passed: bool
    selected_action_ids: tuple[str, ...]
    selected_action_kinds: tuple[RepairKind, ...]
    reasons: tuple[str, ...]


def load_acceptance_manifest(path: Path) -> AcceptanceManifest:
    """Load and validate one checked-in acceptance matrix."""
    return AcceptanceManifest.model_validate_json(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    """Hash one immutable source without loading a large GLB into memory."""
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_case_source(case: AcceptanceCase, repository_root: Path) -> SourceResolution:
    """Resolve and hash a tracked or local-saved case source."""
    path = (repository_root / Path(case.source_path)).resolve(strict=False)
    if not path.is_file():
        return SourceResolution(
            path=path,
            available=False,
            hash_matches=False,
            observed_sha256=None,
        )
    observed = file_sha256(path)
    return SourceResolution(
        path=path,
        available=True,
        hash_matches=observed == case.source_sha256,
        observed_sha256=observed,
    )


def evaluate_selected_plan(
    case: AcceptanceCase,
    plan: RepairPlan | None,
    *,
    globally_forbidden: tuple[RepairKind, ...] = (),
) -> PlanEvaluation:
    """Reject unsupported, forbidden, or semantically incomplete model selections."""
    candidates = tuple(plan.candidates) if plan is not None else ()
    selected_ids = tuple(candidate.id for candidate in candidates)
    selected_kinds = tuple(candidate.kind for candidate in candidates)
    selected_kind_set = set(selected_kinds)
    reasons: list[str] = []

    forbidden = selected_kind_set & set(globally_forbidden)
    if forbidden:
        values = ", ".join(sorted(kind.value for kind in forbidden))
        reasons.append(f"Selected globally forbidden action kinds: {values}.")

    unsupported = selected_kind_set - set(case.allowed_action_kinds)
    if unsupported:
        values = ", ".join(sorted(kind.value for kind in unsupported))
        reasons.append(f"Selected action kinds outside the case allowlist: {values}.")

    missing = set(case.required_action_kinds) - selected_kind_set
    if missing:
        values = ", ".join(sorted(kind.value for kind in missing))
        reasons.append(f"Missing required action kinds: {values}.")

    if plan is not None and plan.blocked:
        reasons.append("The selected repair plan is blocked.")

    return PlanEvaluation(
        passed=not reasons,
        selected_action_ids=selected_ids,
        selected_action_kinds=selected_kinds,
        reasons=tuple(reasons),
    )


def write_json(path: Path, value: object) -> None:
    """Write one stable evaluation record."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"{json.dumps(value, indent=2, sort_keys=True)}\n",
        encoding="utf-8",
        newline="\n",
    )


def aggregate_acceptance_summaries(
    manifest: AcceptanceManifest,
    summaries: Iterable[tuple[str, dict[str, object]]],
    *,
    provider: str,
    model_id: str,
) -> dict[str, object]:
    """Select the newest compatible passing result for every frozen case.

    Live provider evaluation is intentionally resumable in small batches.  This reducer makes
    those bounded runs auditable as one release gate without rerunning already-passing paid cases.
    A result is compatible only when provider, model, case ID, and frozen source hash all match.
    """
    case_by_id = {case.case_id: case for case in manifest.cases}
    selected: dict[str, dict[str, object]] = {}
    selected_run: dict[str, str] = {}
    for run_name, summary in sorted(summaries, key=lambda item: item[0]):
        if summary.get("provider") != provider or summary.get("model_id") != model_id:
            continue
        records = summary.get("case_results")
        if not isinstance(records, list):
            continue
        for value in cast(list[object], records):
            if not isinstance(value, dict):
                continue
            raw_record = cast(dict[object, object], value)
            record = {key: item for key, item in raw_record.items() if isinstance(key, str)}
            case_id = record.get("case_id")
            case = case_by_id.get(case_id) if isinstance(case_id, str) else None
            if case is None or record.get("expected_source_sha256") != case.source_sha256:
                continue
            if record.get("safety_pass") is not True or record.get("semantic_pass") is not True:
                continue
            selected[case.case_id] = record
            selected_run[case.case_id] = run_name

    case_results: list[dict[str, object]] = []
    for case in manifest.cases:
        record = selected.get(case.case_id)
        if record is not None:
            case_results.append({**record, "source_run": selected_run[case.case_id]})

    safety_passes = sum(record.get("safety_pass") is True for record in case_results)
    semantic_passes = sum(record.get("semantic_pass") is True for record in case_results)
    missing_cases = [case.case_id for case in manifest.cases if case.case_id not in selected]
    token_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    invocation_duration_seconds = 0.0
    for record in case_results:
        metrics = record.get("metrics")
        if not isinstance(metrics, dict):
            continue
        typed_metrics = cast(dict[object, object], metrics)
        usage = typed_metrics.get("token_usage")
        if isinstance(usage, dict):
            typed_usage = cast(dict[object, object], usage)
            for key in token_usage:
                value = typed_usage.get(key)
                if isinstance(value, int):
                    token_usage[key] += value
        duration = typed_metrics.get("invocation_duration_seconds")
        if isinstance(duration, int | float):
            invocation_duration_seconds += float(duration)

    gate_pass = bool(
        not missing_cases
        and safety_passes == len(manifest.cases)
        and semantic_passes >= manifest.semantic_minimum_passes
    )
    return {
        "schema_version": 1,
        "acceptance_set_id": manifest.acceptance_set_id,
        "provider": provider,
        "model_id": model_id,
        "full_matrix": not missing_cases,
        "safety_passes": safety_passes,
        "safety_required": len(manifest.cases),
        "semantic_passes": semantic_passes,
        "semantic_required": manifest.semantic_minimum_passes,
        "missing_cases": missing_cases,
        "release_gate": "PASSED" if gate_pass else "FAILED",
        "metrics": {
            "invocation_duration_seconds": invocation_duration_seconds,
            "token_usage": token_usage,
        },
        "case_results": case_results,
    }
