[CmdletBinding()]
param(
    [string]$Profile = 'asset-shepherd-admin',
    [string]$Region = 'us-east-1',
    [ValidateRange(1, 3653)]
    [int]$RetentionDays = 7
)

$ErrorActionPreference = 'Stop'

$logGroups = aws logs describe-log-groups `
    --profile $Profile `
    --region $Region `
    --query 'logGroups[].logGroupName' `
    --output json | ConvertFrom-Json

$selected = @(
    $logGroups | Where-Object {
        $_ -match '^/aws/(codebuild|ecs|lambda)/.*asset-shepherd' -or
        $_ -match '^/aws/bedrock-agentcore/runtimes/AssetShepherdRuntime-'
    }
)

if ($selected.Count -eq 0) {
    throw 'No Asset Shepherd CloudWatch log groups were found.'
}

foreach ($logGroup in $selected) {
    aws logs put-retention-policy `
        --profile $Profile `
        --region $Region `
        --log-group-name $logGroup `
        --retention-in-days $RetentionDays
    if ($LASTEXITCODE -ne 0) {
        throw "Could not set retention for $logGroup."
    }
    Write-Output "$RetentionDays days`t$logGroup"
}
