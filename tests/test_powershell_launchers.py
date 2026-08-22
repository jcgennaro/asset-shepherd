"""Static security acceptance for the one-command Windows launch helpers."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAVE_SCRIPT = PROJECT_ROOT / "scripts" / "Save-OpenAIKey.ps1"
START_SCRIPT = PROJECT_ROOT / "scripts" / "Start-AssetShepherd.ps1"


def test_key_setup_uses_hidden_input_and_windows_user_protection() -> None:
    """The setup script must not request a key in command text or write it unencrypted."""
    script = SAVE_SCRIPT.read_text(encoding="utf-8")

    assert "Read-Host" in script
    assert "-AsSecureString" in script
    assert "ProtectedData]::Protect" in script
    assert "DataProtectionScope]::CurrentUser" in script
    assert "LocalApplicationData" in script
    assert "Set-Content $plainKey" not in script
    assert "setx" not in script.casefold()


def test_launcher_injects_and_removes_the_key_around_only_the_web_process() -> None:
    """The launcher decrypts locally, starts the app, and restores process state in finally."""
    script = START_SCRIPT.read_text(encoding="utf-8")

    assert "ProtectedData]::Unprotect" in script
    assert "$env:OPENAI_API_KEY = $plainKey" in script
    assert "uv run asset-shepherd web" in script
    assert "Remove-Item Env:OPENAI_API_KEY" in script
    assert "finally" in script
    assert "LocalApplicationData" in script
