"""Source-level invariants for the bounded operations deployment."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OPERATIONS_TEMPLATE = PROJECT_ROOT / "infra" / "cloudformation" / "operations.yaml"


def test_every_project_alarm_routes_to_one_private_email_topic() -> None:
    """All eight alarms share one parameterized route without committing contact data."""
    template = OPERATIONS_TEMPLATE.read_text(encoding="utf-8")

    assert "AlarmEmailAddress:" in template
    assert "NoEcho: true" in template
    assert template.count("AlarmActions:") == 8
    assert template.count("- !Ref AlarmNotificationTopic") == 8
    assert "@gmail.com" not in template
