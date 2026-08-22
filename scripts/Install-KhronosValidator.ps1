#Requires -Version 5.1

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$validatorVersion = '2.0.0-dev.3.10'
$archiveName = "gltf_validator-$validatorVersion-win64.zip"
$archiveSha256 = 'C5068F51205DEEDC28ACC3529EE7E11EE60E853454F673093398EBA80142202C'
$executableSha256 = '4388A152FF90B68C6430AE03862E05E257A9D50A500ED7D0EB1CD420DC75FF96'
$downloadUri = "https://github.com/KhronosGroup/glTF-Validator/releases/download/$validatorVersion/$archiveName"
$installRoot = Join-Path $env:LOCALAPPDATA "AssetShepherd\tools\gltf-validator\$validatorVersion"
$executablePath = Join-Path $installRoot 'gltf_validator.exe'

if (-not (Test-Path -LiteralPath $executablePath -PathType Leaf) -or
    (Get-FileHash -LiteralPath $executablePath -Algorithm SHA256).Hash -ne $executableSha256) {
    $temporaryArchive = Join-Path ([System.IO.Path]::GetTempPath()) ("asset-shepherd-" + [guid]::NewGuid().ToString('N') + '.zip')
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $downloadUri -OutFile $temporaryArchive -UseBasicParsing
        $downloadedHash = (Get-FileHash -LiteralPath $temporaryArchive -Algorithm SHA256).Hash
        if ($downloadedHash -ne $archiveSha256) {
            throw "Khronos validator archive hash mismatch: $downloadedHash"
        }
        New-Item -ItemType Directory -Path $installRoot -Force | Out-Null
        Expand-Archive -LiteralPath $temporaryArchive -DestinationPath $installRoot -Force
        $installedHash = (Get-FileHash -LiteralPath $executablePath -Algorithm SHA256).Hash
        if ($installedHash -ne $executableSha256) {
            throw "Khronos validator executable hash mismatch: $installedHash"
        }
    }
    finally {
        Remove-Item -LiteralPath $temporaryArchive -Force -ErrorAction SilentlyContinue
    }
}

[Environment]::SetEnvironmentVariable(
    'ASSET_SHEPHERD_GLTF_VALIDATOR',
    $executablePath,
    [EnvironmentVariableTarget]::User
)
$env:ASSET_SHEPHERD_GLTF_VALIDATOR = $executablePath
Write-Output "Installed official Khronos glTF Validator $validatorVersion at $executablePath"
Write-Output 'Open a new PowerShell window before running Asset Shepherd so it inherits the saved path.'
