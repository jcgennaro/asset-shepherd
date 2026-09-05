#Requires -Version 5.1

[CmdletBinding()]
param(
    [string]$AwsProfile = 'asset-shepherd-admin',
    [string]$Region = 'us-east-1',
    [string]$SecretPath = (Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'AssetShepherd\openai-api-key.dpapi')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Security
$protectedBytes = [Convert]::FromBase64String([IO.File]::ReadAllText($SecretPath))
$plainBytes = $null
$plainKey = $null
try {
    $plainBytes = [Security.Cryptography.ProtectedData]::Unprotect(
        $protectedBytes, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser
    )
    $plainKey = [Text.Encoding]::UTF8.GetString($plainBytes)
    # Transfer through an anonymous process pipe, never argv, a plaintext file, or console output.
    $plainKey | uv run python -c @'
import json, logging, sys
import boto3
logging.disable(logging.CRITICAL)
key = sys.stdin.read().strip()
if not key.startswith("sk-") or len(key) < 20:
    raise SystemExit("The locally protected OpenAI key is invalid.")
try:
    client = boto3.Session(profile_name=sys.argv[1], region_name=sys.argv[2]).client("secretsmanager")
    result = client.create_secret(
        Name="asset-shepherd/contest/openai",
        Description="Backend-only OpenAI API credential for Asset Shepherd; not a login signer.",
        SecretString=json.dumps({"api_key": key}),
        Tags=[{"Key": "Project", "Value": "asset-shepherd"}, {"Key": "Environment", "Value": "contest"}],
    )
    print("Created encrypted provider secret:", result["ARN"])
except Exception as error:
    # Includes ResourceExistsException: never silently replace an existing credential.
    raise SystemExit("Secret creation failed: " + type(error).__name__) from None
finally:
    key = None
'@ $AwsProfile $Region
    if ($LASTEXITCODE -ne 0) { throw 'Provider secret publication did not succeed.' }
}
finally {
    if ($null -ne $plainBytes) { [Array]::Clear($plainBytes, 0, $plainBytes.Length) }
    [Array]::Clear($protectedBytes, 0, $protectedBytes.Length)
    $plainKey = $null
}
