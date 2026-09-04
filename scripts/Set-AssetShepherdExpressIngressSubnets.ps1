[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param(
    [Parameter(Mandatory = $true)]
    [ValidateCount(2, 2)]
    [ValidatePattern('^subnet-[0-9a-f]+$')]
    [string[]]$SubnetIds,
    [string]$EnvironmentName = 'contest',
    [string]$Profile = 'asset-shepherd-admin',
    [string]$Region = 'us-east-1'
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

if ($SubnetIds[0] -eq $SubnetIds[1]) {
    throw 'Specify two distinct public subnet IDs.'
}

$subnets = Invoke-AwsJson -Arguments @(
    'ec2', 'describe-subnets',
    '--profile', $Profile,
    '--region', $Region,
    '--subnet-ids', $SubnetIds[0], $SubnetIds[1]
)
if (@($subnets.Subnets).Count -ne 2) {
    throw 'AWS did not return both requested subnets.'
}
$availabilityZones = @($subnets.Subnets.AvailabilityZone | Sort-Object -Unique)
if ($availabilityZones.Count -ne 2) {
    throw 'The ingress subnets must be in two different Availability Zones.'
}
$vpcIds = @($subnets.Subnets.VpcId | Sort-Object -Unique)
if ($vpcIds.Count -ne 1) {
    throw 'The ingress subnets must be in the same VPC.'
}
if (@($subnets.Subnets | Where-Object { -not $_.MapPublicIpOnLaunch }).Count -ne 0) {
    throw 'Both ingress subnets must map public IPv4 addresses on launch.'
}

$tagged = Invoke-AwsJson -Arguments @(
    'resourcegroupstaggingapi', 'get-resources',
    '--profile', $Profile,
    '--region', $Region,
    '--resource-type-filters', 'elasticloadbalancing:loadbalancer',
    '--tag-filters', 'Key=Project,Values=asset-shepherd',
    "Key=Environment,Values=$EnvironmentName"
)
$loadBalancerArns = @(
    $tagged.ResourceTagMappingList.ResourceARN |
        Where-Object { $_ -match ':loadbalancer/app/ecs-express-gateway-alb-' }
)
if ($loadBalancerArns.Count -ne 1) {
    throw "Expected one tagged Asset Shepherd Express ALB, found $($loadBalancerArns.Count)."
}
$loadBalancerArn = $loadBalancerArns[0]
$loadBalancer = Invoke-AwsJson -Arguments @(
    'elbv2', 'describe-load-balancers',
    '--profile', $Profile,
    '--region', $Region,
    '--load-balancer-arns', $loadBalancerArn
)
$description = $loadBalancer.LoadBalancers[0]
if ($description.Type -ne 'application' -or $description.Scheme -ne 'internet-facing') {
    throw 'The tagged resource is not the expected internet-facing Application Load Balancer.'
}
if ($description.VpcId -ne $vpcIds[0]) {
    throw 'The requested subnets do not belong to the load balancer VPC.'
}

$target = "$($description.LoadBalancerName) in $($availabilityZones -join ', ')"
if (-not $PSCmdlet.ShouldProcess($target, 'Replace the Express ALB subnet set')) {
    return
}

$null = Invoke-AwsJson -Arguments @(
    'elbv2', 'set-subnets',
    '--profile', $Profile,
    '--region', $Region,
    '--load-balancer-arn', $loadBalancerArn,
    '--subnets', $SubnetIds[0], $SubnetIds[1]
)

& aws elbv2 wait load-balancer-available `
    --profile $Profile `
    --region $Region `
    --load-balancer-arns $loadBalancerArn
if ($LASTEXITCODE -ne 0) {
    throw 'The load balancer did not return to the available state.'
}

$verified = Invoke-AwsJson -Arguments @(
    'elbv2', 'describe-load-balancers',
    '--profile', $Profile,
    '--region', $Region,
    '--load-balancer-arns', $loadBalancerArn
)
$actualSubnetIds = @($verified.LoadBalancers[0].AvailabilityZones.SubnetId | Sort-Object)
$expectedSubnetIds = @($SubnetIds | Sort-Object)
if (($actualSubnetIds -join ',') -ne ($expectedSubnetIds -join ',')) {
    throw "Load balancer subnet verification failed: $($actualSubnetIds -join ', ')."
}

[pscustomobject]@{
    LoadBalancer = $description.LoadBalancerName
    Subnets = $actualSubnetIds -join ', '
    AvailabilityZones = $availabilityZones -join ', '
    Verified = $true
}
