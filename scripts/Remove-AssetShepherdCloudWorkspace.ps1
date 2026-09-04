[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-f]{32}$')]
    [string]$WorkspaceId,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z0-9.-]{3,63}$')]
    [string]$Bucket,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9_.-]{3,255}$')]
    [string]$Table,
    [string]$OwnerId = 'contest-demo',
    [string]$Profile = 'asset-shepherd-admin',
    [string]$Region = 'us-east-1',
    [switch]$AllowOrphanedWorkspace
)

$ErrorActionPreference = 'Stop'

function Invoke-AwsJson {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    $raw = & aws @Arguments --output json
    if ($LASTEXITCODE -ne 0) {
        throw "AWS CLI command failed: aws $($Arguments -join ' ')"
    }
    if (-not $raw) {
        return $null
    }
    return $raw | ConvertFrom-Json
}

function Remove-S3PrefixVersions {
    param([Parameter(Mandatory = $true)][string]$Prefix)

    $listing = Invoke-AwsJson -Arguments @(
        's3api', 'list-object-versions',
        '--profile', $Profile,
        '--region', $Region,
        '--bucket', $Bucket,
        '--prefix', $Prefix
    )
    $objects = @()
    foreach ($entry in @($listing.Versions) + @($listing.DeleteMarkers)) {
        if ($null -ne $entry -and $entry.Key -like "$Prefix*") {
            $objects += [ordered]@{ Key = $entry.Key; VersionId = $entry.VersionId }
        }
    }

    for ($offset = 0; $offset -lt $objects.Count; $offset += 1000) {
        $last = [Math]::Min($offset + 999, $objects.Count - 1)
        $batch = @($objects[$offset..$last])
        $deleteDocument = [ordered]@{ Objects = $batch; Quiet = $true }
        $temporary = [System.IO.Path]::GetTempFileName()
        try {
            [System.IO.File]::WriteAllText(
                $temporary,
                ($deleteDocument | ConvertTo-Json -Depth 5 -Compress),
                [System.Text.UTF8Encoding]::new($false)
            )
            $null = Invoke-AwsJson -Arguments @(
                's3api', 'delete-objects',
                '--profile', $Profile,
                '--region', $Region,
                '--bucket', $Bucket,
                '--delete', "file://$temporary"
            )
        }
        finally {
            Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
        }
    }
    return $objects.Count
}

$workspaceKey = [ordered]@{
    PK = @{ S = "WORKSPACE#$WorkspaceId" }
    SK = @{ S = 'STATE' }
} | ConvertTo-Json -Depth 4 -Compress
$record = Invoke-AwsJson -Arguments @(
    'dynamodb', 'get-item',
    '--profile', $Profile,
    '--region', $Region,
    '--table-name', $Table,
    '--key', $workspaceKey,
    '--consistent-read'
)
$recordOwner = $record.Item.owner_id.S
if ($recordOwner -and $recordOwner -ne $OwnerId) {
    throw "Workspace $WorkspaceId belongs to a different application owner."
}
if (-not $recordOwner -and -not $AllowOrphanedWorkspace) {
    throw 'The workspace pointer is absent; use -AllowOrphanedWorkspace only for a known orphan.'
}

$commandValues = @{ ':pk' = @{ S = "COMMAND#$WorkspaceId" } } |
    ConvertTo-Json -Depth 4 -Compress
$commands = Invoke-AwsJson -Arguments @(
    'dynamodb', 'query',
    '--profile', $Profile,
    '--region', $Region,
    '--table-name', $Table,
    '--key-condition-expression', 'PK = :pk',
    '--expression-attribute-values', $commandValues,
    '--consistent-read'
)
$commandItems = @($commands.Items | Where-Object { $null -ne $_ })
foreach ($item in $commandItems) {
    if ($item.dispatch_owner.S -and $item.dispatch_owner.S -ne $OwnerId) {
        throw "A command receipt for $WorkspaceId belongs to a different application owner."
    }
}

$target = "s3://$Bucket/{workspaces/$WorkspaceId,sessions/session_$WorkspaceId} and table $Table"
if (-not $PSCmdlet.ShouldProcess($target, 'Permanently delete every object version and record')) {
    return
}

$deletedObjectVersions = 0
$deletedObjectVersions += Remove-S3PrefixVersions -Prefix "workspaces/$WorkspaceId/"
$deletedObjectVersions += Remove-S3PrefixVersions -Prefix "sessions/session_$WorkspaceId/"

foreach ($item in $commandItems) {
    $commandKey = [ordered]@{ PK = $item.PK; SK = $item.SK } |
        ConvertTo-Json -Depth 4 -Compress
    $null = Invoke-AwsJson -Arguments @(
        'dynamodb', 'delete-item',
        '--profile', $Profile,
        '--region', $Region,
        '--table-name', $Table,
        '--key', $commandKey
    )
}

if ($recordOwner) {
    $ownerValues = @{ ':owner' = @{ S = $OwnerId } } | ConvertTo-Json -Depth 4 -Compress
    $null = Invoke-AwsJson -Arguments @(
        'dynamodb', 'delete-item',
        '--profile', $Profile,
        '--region', $Region,
        '--table-name', $Table,
        '--key', $workspaceKey,
        '--condition-expression', 'owner_id = :owner',
        '--expression-attribute-values', $ownerValues
    )
}

$workspaceRemainder = Invoke-AwsJson -Arguments @(
    's3api', 'list-object-versions',
    '--profile', $Profile,
    '--region', $Region,
    '--bucket', $Bucket,
    '--prefix', "workspaces/$WorkspaceId/"
)
$sessionRemainder = Invoke-AwsJson -Arguments @(
    's3api', 'list-object-versions',
    '--profile', $Profile,
    '--region', $Region,
    '--bucket', $Bucket,
    '--prefix', "sessions/session_$WorkspaceId/"
)
$recordRemainder = Invoke-AwsJson -Arguments @(
    'dynamodb', 'get-item',
    '--profile', $Profile,
    '--region', $Region,
    '--table-name', $Table,
    '--key', $workspaceKey,
    '--consistent-read'
)
$commandRemainder = Invoke-AwsJson -Arguments @(
    'dynamodb', 'query',
    '--profile', $Profile,
    '--region', $Region,
    '--table-name', $Table,
    '--key-condition-expression', 'PK = :pk',
    '--expression-attribute-values', $commandValues,
    '--consistent-read'
)

$remainingObjects = @($workspaceRemainder.Versions | Where-Object { $null -ne $_ }).Count +
    @($workspaceRemainder.DeleteMarkers | Where-Object { $null -ne $_ }).Count +
    @($sessionRemainder.Versions | Where-Object { $null -ne $_ }).Count +
    @($sessionRemainder.DeleteMarkers | Where-Object { $null -ne $_ }).Count
if ($remainingObjects -ne 0 -or $recordRemainder.Item -or $commandRemainder.Count -ne 0) {
    throw 'Workspace deletion verification failed.'
}

[pscustomobject]@{
    WorkspaceId = $WorkspaceId
    DeletedObjectVersions = $deletedObjectVersions
    DeletedCommandReceipts = $commandItems.Count
    WorkspacePointerDeleted = [bool]$recordOwner
    VerifiedEmpty = $true
}
