"""D019 acceptance tests for objective preflight and durable hosted job state."""

from io import BytesIO
from pathlib import Path

import pytest

from asset_shepherd.hosted_workspace import (
    HostedWorkspace,
    HostedWorkspaceError,
    HostedWorkspaceStore,
    SupportStatus,
    WorkspacePhase,
)
from asset_shepherd.models import AssetTargetUse, ProjectProfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BROKEN_PATH = PROJECT_ROOT / "fixtures" / "broken_robot.glb"
CLEAN_PATH = PROJECT_ROOT / "fixtures" / "clean_robot.glb"
DESCRIPTION = "A friendly humanoid robot intended as a 1.8 m static game asset."


def _family() -> ProjectProfile:
    return ProjectProfile.model_validate_json(
        (
            PROJECT_ROOT
            / "src"
            / "asset_shepherd"
            / "data"
            / "unreal_static_game_asset_family.json"
        ).read_text(encoding="utf-8")
    )


def _create(
    store: HostedWorkspaceStore,
    source: Path = BROKEN_PATH,
    description: str = DESCRIPTION,
) -> HostedWorkspace:
    return store.create(description, source.name, BytesIO(source.read_bytes()))


def test_preflight_measures_source_without_policy_findings_or_plan(tmp_path: Path) -> None:
    """Early upload yields profile-free facts and no policy-bound workflow artifacts."""
    workspace = _create(HostedWorkspaceStore(tmp_path / "hosted", _family()))

    assert workspace.record.phase is WorkspacePhase.TARGET_CONFIRMATION
    assert workspace.record.target is None
    assert workspace.record.profile_policy is None
    assert workspace.record.preflight.package.parse_success
    assert workspace.record.preflight.geometry is not None
    assert workspace.record.preflight.materials
    assert workspace.record.events[0].event_type == "SOURCE_MEASURED"
    assert not workspace.output_dir.exists()
    assert not (workspace.root / "profile.json").exists()
    assert not (workspace.root / "intent.json").exists()


def test_pending_interrupt_survives_restart_and_duplicate_resume_is_exactly_once(
    tmp_path: Path,
) -> None:
    """A native pending interrupt restores and one command cannot duplicate mutation."""
    root = tmp_path / "hosted"
    store = HostedWorkspaceStore(root, _family())
    workspace = _create(store)
    workspace = store.confirm_target(
        workspace,
        accept_supported_goal=False,
        command_id="1" * 32,
    )
    interrupt_id = workspace.record.pending_interrupt_id
    assert interrupt_id is not None
    assert workspace.record.phase is WorkspacePhase.APPROVAL

    restarted_store = HostedWorkspaceStore(root, _family())
    restarted = restarted_store.get(workspace.record.workspace_id)
    assert restarted is not None
    assert restarted.waiting_for_approval
    assert restarted.record.pending_interrupt_id == interrupt_id

    answered = restarted_store.answer_evidence_question(restarted, "authorization")
    assert answered.waiting_for_approval
    assert answered.record.last_answer is not None
    assert answered.record.last_answer.statements[0] == "Chat text cannot approve a repair."

    completed = restarted_store.decide(
        answered,
        interrupt_id=interrupt_id,
        approved=True,
        command_id="2" * 32,
    )
    assert completed.record.phase is WorkspacePhase.COMPLETE
    assert completed.ready_candidate
    repaired_before = (completed.output_dir / "repaired.glb").read_bytes()
    result_before = (completed.output_dir / "result.zip").read_bytes()

    duplicate = restarted_store.decide(
        completed,
        interrupt_id=interrupt_id,
        approved=True,
        command_id="2" * 32,
    )
    assert (duplicate.output_dir / "repaired.glb").read_bytes() == repaired_before
    assert (duplicate.output_dir / "result.zip").read_bytes() == result_before

    restarted_again = HostedWorkspaceStore(root, _family()).get(workspace.record.workspace_id)
    assert restarted_again is not None
    assert restarted_again.record.phase is WorkspacePhase.COMPLETE
    assert restarted_again.ready_candidate


def test_unsupported_intent_requires_narrow_goal_and_clean_control_needs_no_approval(
    tmp_path: Path,
) -> None:
    """Unsupported goals require agreement while a compliant GLB remains mutation-free."""
    root = tmp_path / "hosted"
    store = HostedWorkspaceStore(root, _family())
    workspace = _create(
        store,
        CLEAN_PATH,
        "A friendly 1.8 m playable character for a game.",
    )

    with pytest.raises(HostedWorkspaceError, match="Accept the narrower"):
        store.confirm_target(
            workspace,
            accept_supported_goal=False,
            command_id="3" * 32,
        )

    workspace = store.confirm_target(
        workspace,
        accept_supported_goal=True,
        command_id="4" * 32,
    )
    assert workspace.record.target is not None
    assert workspace.record.target.support_status is SupportStatus.NARROWED_EXTERNAL_HANDOFF
    assert workspace.record.phase is WorkspacePhase.COMPLETE
    assert not workspace.waiting_for_approval
    assert workspace.runtime is not None
    assert workspace.runtime.job.decisions is not None
    selected_plan = workspace.runtime.job.selected_plan
    assert selected_plan is not None
    assert not selected_plan.approval_action_ids
    assert (workspace.output_dir / "repaired.glb").read_bytes() == CLEAN_PATH.read_bytes()


def test_advanced_supported_rules_are_schema_validated_and_frozen(tmp_path: Path) -> None:
    """Advanced input can change enforced targets but cannot bypass ProjectProfile validation."""
    store = HostedWorkspaceStore(tmp_path / "hosted", _family())
    invalid = _create(store, CLEAN_PATH)
    with pytest.raises(HostedWorkspaceError, match="resolved policy is invalid"):
        store.confirm_target(
            invalid,
            accept_supported_goal=False,
            command_id="5" * 32,
            custom_values={"custom_height_tolerance_cm": "-1"},
        )
    assert invalid.record.target is None
    assert not (invalid.root / "profile.json").exists()

    workspace = _create(
        store,
        CLEAN_PATH,
        "A friendly humanoid robot intended as a 1.82 m static game asset.",
    )
    completed = store.confirm_target(
        workspace,
        accept_supported_goal=False,
        command_id="6" * 32,
        custom_values={
            "custom_height_tolerance_cm": "2",
            "custom_max_materials": "3",
        },
    )
    policy = completed.record.profile_policy
    assert policy is not None
    assert policy.explicit_overrides == {
        "budgets.max_materials": 3,
        "expected_height_cm.target": 182.0,
        "expected_height_cm.tolerance": 2.0,
        "orientation.ground_tolerance_cm": 0.91,
    }
    assert policy.policy_family_id == "unreal-static-game-asset-family-v1"
    assert policy.rule_sources["budgets.max_materials"] == "USER_OVERRIDE"


def test_missing_target_answer_is_durable_and_confirmation_never_reasks_it(
    tmp_path: Path,
) -> None:
    """Only absent fields are clarified, persisted, and consumed by final confirmation."""
    root = tmp_path / "hosted"
    store = HostedWorkspaceStore(root, _family())
    workspace = _create(
        store,
        CLEAN_PATH,
        "A friendly humanoid robot intended as a static game asset.",
    )
    draft = workspace.record.target_draft
    assert draft is not None
    assert draft.target_use is AssetTargetUse.STATIC_GAME_ASSET
    assert draft.target_height_cm is None
    assert draft.missing_fields == ("target_height_cm",)

    clarified = store.clarify_target(
        workspace,
        target_use_value=None,
        target_height_m="1.8",
        command_id="7" * 32,
    )
    restarted = HostedWorkspaceStore(root, _family()).get(clarified.record.workspace_id)
    assert restarted is not None
    completed_draft = restarted.record.target_draft
    assert completed_draft is not None
    assert completed_draft.ready_for_confirmation
    assert completed_draft.target_height_cm == 180.0
    assert completed_draft.evidence[-1].source.value == "USER_CLARIFICATION"

    completed = store.confirm_target(
        restarted,
        accept_supported_goal=False,
        command_id="8" * 32,
    )
    assert completed.record.target is not None
    assert completed.record.target.target_height_cm == 180.0


def test_target_adjustment_is_durable_and_exactly_once(tmp_path: Path) -> None:
    """An explicit correction replaces an unfrozen proposal and survives application restart."""
    root = tmp_path / "hosted"
    store = HostedWorkspaceStore(root, _family())
    workspace = _create(store, CLEAN_PATH)

    revised = store.revise_target(
        workspace,
        target_use_value=AssetTargetUse.STATIC_GAME_ASSET.value,
        target_height_m="2.4",
        command_id="9" * 32,
    )
    duplicate = store.revise_target(
        revised,
        target_use_value=AssetTargetUse.PLAYABLE_CHARACTER.value,
        target_height_m="3.0",
        command_id="9" * 32,
    )
    restarted = HostedWorkspaceStore(root, _family()).get(duplicate.record.workspace_id)

    assert restarted is not None
    assert restarted.record.target_draft is not None
    assert restarted.record.target_draft.target_use is AssetTargetUse.STATIC_GAME_ASSET
    assert restarted.record.target_draft.target_height_cm == 240.0
    assert restarted.record.events[-1].event_type == "TARGET_REVISED"
    assert sum(event.event_type == "TARGET_REVISED" for event in restarted.record.events) == 1
