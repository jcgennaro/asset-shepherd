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
DESCRIPTION = "A friendly humanoid robot intended as a static game asset."


def _profiles() -> tuple[ProjectProfile, ...]:
    return tuple(
        ProjectProfile.model_validate_json(path.read_text(encoding="utf-8"))
        for path in (
            PROJECT_ROOT / "profiles" / "unreal_indie_robot.json",
            PROJECT_ROOT / "validation" / "profiles" / "small_stylized_static_mesh.json",
        )
    )


def _create(store: HostedWorkspaceStore, source: Path = BROKEN_PATH) -> HostedWorkspace:
    return store.create(DESCRIPTION, source.name, BytesIO(source.read_bytes()))


def test_preflight_measures_source_without_policy_findings_or_plan(tmp_path: Path) -> None:
    """Early upload yields profile-free facts and no policy-bound workflow artifacts."""
    workspace = _create(HostedWorkspaceStore(tmp_path / "hosted", _profiles()))

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
    store = HostedWorkspaceStore(root, _profiles())
    workspace = _create(store)
    workspace = store.confirm_target(
        workspace,
        target_use_value=AssetTargetUse.STATIC_GAME_ASSET.value,
        target_height_m="1.8",
        accept_supported_goal=False,
        command_id="1" * 32,
    )
    interrupt_id = workspace.record.pending_interrupt_id
    assert interrupt_id is not None
    assert workspace.record.phase is WorkspacePhase.APPROVAL

    restarted_store = HostedWorkspaceStore(root, _profiles())
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

    restarted_again = HostedWorkspaceStore(root, _profiles()).get(workspace.record.workspace_id)
    assert restarted_again is not None
    assert restarted_again.record.phase is WorkspacePhase.COMPLETE
    assert restarted_again.ready_candidate


def test_unsupported_intent_requires_narrow_goal_and_clean_control_needs_no_approval(
    tmp_path: Path,
) -> None:
    """Unsupported goals require agreement while a compliant GLB remains mutation-free."""
    root = tmp_path / "hosted"
    store = HostedWorkspaceStore(root, _profiles())
    workspace = _create(store, CLEAN_PATH)

    with pytest.raises(HostedWorkspaceError, match="Accept the narrower"):
        store.confirm_target(
            workspace,
            target_use_value=AssetTargetUse.PLAYABLE_CHARACTER.value,
            target_height_m="1.8",
            accept_supported_goal=False,
            command_id="3" * 32,
        )

    workspace = store.confirm_target(
        workspace,
        target_use_value=AssetTargetUse.PLAYABLE_CHARACTER.value,
        target_height_m="1.8",
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
    store = HostedWorkspaceStore(tmp_path / "hosted", _profiles())
    invalid = _create(store, CLEAN_PATH)
    with pytest.raises(HostedWorkspaceError, match="customized policy is invalid"):
        store.confirm_target(
            invalid,
            target_use_value=AssetTargetUse.STATIC_GAME_ASSET.value,
            target_height_m="1.8",
            accept_supported_goal=False,
            command_id="5" * 32,
            custom_values={"custom_height_tolerance_cm": "-1"},
        )
    assert invalid.record.target is None
    assert not (invalid.root / "profile.json").exists()

    workspace = _create(store, CLEAN_PATH)
    completed = store.confirm_target(
        workspace,
        target_use_value=AssetTargetUse.STATIC_GAME_ASSET.value,
        target_height_m="1.82",
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
    }
