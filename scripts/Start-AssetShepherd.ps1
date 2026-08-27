#Requires -Version 5.1

[CmdletBinding()]
param(
    [string]$BindAddress = '127.0.0.1',
    [ValidateRange(1, 65535)]
    [int]$Port = 8010,
    [string]$WorkDirectory = 'build/web/jobs',
    [string]$SecretPath = (Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'AssetShepherd\openai-api-key.dpapi')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($env:OS -ne 'Windows_NT') {
    throw 'This local key helper requires Windows data protection.'
}
Add-Type -AssemblyName System.Security
if (-not (Test-Path -LiteralPath $SecretPath -PathType Leaf)) {
    throw 'No saved OpenAI key was found. Run .\scripts\Save-OpenAIKey.ps1 first.'
}
if ($null -eq (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'uv is not available on PATH.'
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$protectedBytes = $null
$plainBytes = $null
$plainKey = $null
$hadPreviousKey = Test-Path Env:OPENAI_API_KEY
$previousKey = if ($hadPreviousKey) { $env:OPENAI_API_KEY } else { $null }
$exitCode = 1

try {
    $protectedBytes = [Convert]::FromBase64String(
        [IO.File]::ReadAllText($SecretPath, [Text.Encoding]::UTF8).Trim()
    )
    $plainBytes = [System.Security.Cryptography.ProtectedData]::Unprotect(
        $protectedBytes,
        $null,
        [System.Security.Cryptography.DataProtectionScope]::CurrentUser
    )
    $plainKey = [Text.Encoding]::UTF8.GetString($plainBytes)
    if ([string]::IsNullOrWhiteSpace($plainKey)) {
        throw 'The saved OpenAI key is empty. Save it again.'
    }

    Push-Location $projectRoot
    try {
        $env:OPENAI_API_KEY = $plainKey
        & uv run asset-shepherd web --host $BindAddress --port $Port --work-dir $WorkDirectory
        $exitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
        if ($hadPreviousKey) {
            $env:OPENAI_API_KEY = $previousKey
        }
        else {
            Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue
        }
    }
}
catch [System.Security.Cryptography.CryptographicException] {
    throw 'The saved key cannot be unlocked by this Windows user. Save it again.'
}
finally {
    if ($null -ne $protectedBytes) {
        [Array]::Clear($protectedBytes, 0, $protectedBytes.Length)
    }
    if ($null -ne $plainBytes) {
        [Array]::Clear($plainBytes, 0, $plainBytes.Length)
    }
    $plainKey = $null
}

exit $exitCode
