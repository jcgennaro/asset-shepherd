#Requires -Version 5.1

[CmdletBinding()]
param(
    [string]$SecretPath = (Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'AssetShepherd\gemini-api-key.dpapi')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($env:OS -ne 'Windows_NT') {
    throw 'This local key helper requires Windows data protection.'
}
Add-Type -AssemblyName System.Security

$secretDirectory = Split-Path -Parent $SecretPath
[void](New-Item -ItemType Directory -Path $secretDirectory -Force)
$secureKey = Read-Host 'Paste the Gemini API key (input is hidden)' -AsSecureString
$keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
$plainKey = $null
$plainBytes = $null
$protectedBytes = $null

try {
    $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer)
    if ([string]::IsNullOrWhiteSpace($plainKey)) {
        throw 'The API key cannot be empty.'
    }
    $plainBytes = [Text.Encoding]::UTF8.GetBytes($plainKey)
    $protectedBytes = [System.Security.Cryptography.ProtectedData]::Protect(
        $plainBytes,
        $null,
        [System.Security.Cryptography.DataProtectionScope]::CurrentUser
    )
    [IO.File]::WriteAllText(
        $SecretPath,
        [Convert]::ToBase64String($protectedBytes),
        [Text.UTF8Encoding]::new($false)
    )
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer)
    if ($null -ne $plainBytes) {
        [Array]::Clear($plainBytes, 0, $plainBytes.Length)
    }
    if ($null -ne $protectedBytes) {
        [Array]::Clear($protectedBytes, 0, $protectedBytes.Length)
    }
    $plainKey = $null
    $secureKey.Dispose()
}

Write-Output 'Saved the encrypted Gemini API key for this Windows user.'
