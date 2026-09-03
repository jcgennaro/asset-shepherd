"""Static security acceptance for the one-command Windows launch helpers."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAVE_SCRIPT = PROJECT_ROOT / "scripts" / "Save-OpenAIKey.ps1"
META_SAVE_SCRIPT = PROJECT_ROOT / "scripts" / "Save-MetaModelKey.ps1"
GEMINI_SAVE_SCRIPT = PROJECT_ROOT / "scripts" / "Save-GeminiKey.ps1"
START_SCRIPT = PROJECT_ROOT / "scripts" / "Start-AssetShepherd.ps1"
KHRONOS_SCRIPT = PROJECT_ROOT / "scripts" / "Install-KhronosValidator.ps1"


def test_key_setup_uses_hidden_input_and_windows_user_protection() -> None:
    """The setup script must not request a key in command text or write it unencrypted."""
    script = SAVE_SCRIPT.read_text(encoding="utf-8")

    assert "#Requires -Version 5.1" in script
    assert "Add-Type -AssemblyName System.Security" in script
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

    assert "#Requires -Version 5.1" in script
    assert "Add-Type -AssemblyName System.Security" in script
    assert "ProtectedData]::Unprotect" in script
    assert "$env:OPENAI_API_KEY = $plainKey" in script
    assert "uv run asset-shepherd web" in script
    assert "Remove-Item Env:OPENAI_API_KEY" in script
    assert "finally" in script
    assert "LocalApplicationData" in script


def test_launcher_bedrock_mode_never_requires_or_exposes_an_openai_key() -> None:
    """An explicit Bedrock launch uses AWS configuration and removes inherited OpenAI secrets."""
    script = START_SCRIPT.read_text(encoding="utf-8")

    assert "$modelProvider -in @('bedrock', 'bedrock-converse', 'bedrock-nova')" in script
    assert "Bedrock mode requires ASSET_SHEPHERD_MODEL_ID" in script
    assert "Bedrock mode requires ASSET_SHEPHERD_AWS_REGION or AWS_REGION" in script
    assert "$env:ASSET_SHEPHERD_INTAKE_PROVIDER = $modelProvider" in script
    assert "Remove-Item Env:OPENAI_API_KEY" in script


def test_meta_key_setup_and_launcher_keep_the_key_process_scoped() -> None:
    """Muse evaluation uses a separate DPAPI secret and clears it after the web process."""
    save_script = META_SAVE_SCRIPT.read_text(encoding="utf-8")
    start_script = START_SCRIPT.read_text(encoding="utf-8")

    assert (
        "Read-Host 'Paste the Meta Model API key (input is hidden)' -AsSecureString" in save_script
    )
    assert "ProtectedData]::Protect" in save_script
    assert "meta-model-api-key.dpapi" in save_script
    assert "setx" not in save_script.casefold()
    assert "$modelProvider -eq 'meta'" in start_script
    assert "$env:MODEL_API_KEY = $plainKey" in start_script
    assert "$env:ASSET_SHEPHERD_INTAKE_PROVIDER = 'meta'" in start_script
    assert "Remove-Item Env:MODEL_API_KEY" in start_script
    assert "No saved Meta Model API key was found" in start_script


def test_gemini_key_setup_and_launcher_keep_the_key_process_scoped() -> None:
    """Gemini evaluation uses DPAPI and never persists its plaintext environment variable."""
    save_script = GEMINI_SAVE_SCRIPT.read_text(encoding="utf-8")
    start_script = START_SCRIPT.read_text(encoding="utf-8")

    assert "Read-Host 'Paste the Gemini API key (input is hidden)' -AsSecureString" in save_script
    assert "ProtectedData]::Protect" in save_script
    assert "gemini-api-key.dpapi" in save_script
    assert "setx" not in save_script.casefold()
    assert "$modelProvider -eq 'gemini'" in start_script
    assert "$env:GEMINI_API_KEY = $plainKey" in start_script
    assert "$env:ASSET_SHEPHERD_INTAKE_PROVIDER = 'gemini'" in start_script
    assert "Remove-Item Env:GEMINI_API_KEY" in start_script
    assert "No saved Gemini API key was found" in start_script


def test_khronos_installer_is_pinned_hashed_and_powershell_51_compatible() -> None:
    """The optional native validator installer fails closed on supply-chain drift."""
    script = KHRONOS_SCRIPT.read_text(encoding="utf-8")

    assert "#Requires -Version 5.1" in script
    assert "2.0.0-dev.3.10" in script
    assert "C5068F51205DEEDC28ACC3529EE7E11EE60E853454F673093398EBA80142202C" in script
    assert "4388A152FF90B68C6430AE03862E05E257A9D50A500ED7D0EB1CD420DC75FF96" in script
    assert "Get-FileHash" in script
    assert "[EnvironmentVariableTarget]::User" in script
    assert "LOCALAPPDATA" in script
