# Asset Shepherd AWS infrastructure

The checked-in infrastructure is intentionally incremental. All four contest stacks are live in
`us-east-1`: `asset-shepherd-state`, `asset-shepherd-container-build`,
`asset-shepherd-agentcore`, and `asset-shepherd-web`. The public web gate passed on 2026-09-04;
operations hardening and the full remote case matrix remain. See
`docs/BEDROCK_DEPLOYMENT_RUNBOOK.md` for the evidence, current endpoint, and gated procedure.

## Private workspace state

`cloudformation/state.yaml` creates:

- one private, encrypted, versioned S3 bucket with a seven-day lifecycle;
- one encrypted, on-demand DynamoDB workspace table with TTL and an owner/update index; and
- an exact-resource S3/DynamoDB policy on `AssetShepherdBedrockRuntime`.

Deploy or update it from the repository root with the bootstrap administrator profile:

```powershell
aws cloudformation deploy `
  --profile asset-shepherd-admin `
  --region us-east-1 `
  --stack-name asset-shepherd-state `
  --template-file infra/cloudformation/state.yaml `
  --capabilities CAPABILITY_NAMED_IAM
```

Read the generated resource names rather than copying names from another account:

```powershell
$stateOutputs = aws cloudformation describe-stacks `
  --profile asset-shepherd-admin `
  --region us-east-1 `
  --stack-name asset-shepherd-state `
  --query "Stacks[0].Outputs" `
  --output json | ConvertFrom-Json

$workspaceBucket = ($stateOutputs | Where-Object OutputKey -eq 'WorkspaceBucketName').OutputValue
$workspaceTable = ($stateOutputs | Where-Object OutputKey -eq 'WorkspaceTableName').OutputValue
```

The local app can exercise the same cloud adapters through the restricted runtime profile:

```powershell
$env:AWS_PROFILE = 'asset-shepherd'
$env:ASSET_SHEPHERD_AWS_REGION = 'us-east-1'
$env:ASSET_SHEPHERD_WORKSPACE_BUCKET = $workspaceBucket
$env:ASSET_SHEPHERD_SESSION_BUCKET = $workspaceBucket
$env:ASSET_SHEPHERD_WORKSPACE_TABLE = $workspaceTable
$env:ASSET_SHEPHERD_WORKSPACE_OWNER_ID = 'contest-demo'
```

`ASSET_SHEPHERD_WORKSPACE_OWNER_ID` is a server-derived application identity boundary. The contest
demo currently uses one documented identity. Do not accept this value from an arbitrary browser
parameter when multi-user authentication is added.

Run the opt-in live storage proof with the same short-lived role credentials:

```powershell
uv run pytest tests/test_cloud_workspace.py -q -m live
```

The S3 bucket and DynamoDB table use `Retain` replacement/deletion policies. Deleting the
CloudFormation stack therefore does not delete private user artifacts automatically; follow the
documented retention and explicit cleanup gate before removing a deployed environment.

## ARM64 Chromium runtime image

`cloudformation/container-build.yaml` creates a private ECR repository, a two-day build-source
bucket, and a small ARM64 CodeBuild project. CodeBuild performs the container build remotely, so a
developer workstation does not need Docker. Its build gate proves the published image is
`linux/arm64`, renders source and shared-scale evidence through packaged Chromium, imports and
starts the AgentCore HTTP application, checks `/ping`, and pushes the image only after those checks
pass. Published AgentCore tags end in `-agentcore`; the future ECS web image uses a separate tag and
command while sharing the accepted base.

Deploy or update the build resources:

```powershell
aws cloudformation deploy `
  --profile asset-shepherd-admin `
  --region us-east-1 `
  --stack-name asset-shepherd-container-build `
  --template-file infra/cloudformation/container-build.yaml `
  --capabilities CAPABILITY_NAMED_IAM
```

Create the upload from committed files only; this prevents local credentials, caches, and
untracked user artifacts from entering the remote build context:

```powershell
$buildOutputs = aws cloudformation describe-stacks `
  --profile asset-shepherd-admin `
  --region us-east-1 `
  --stack-name asset-shepherd-container-build `
  --query "Stacks[0].Outputs" `
  --output json | ConvertFrom-Json

$sourceBucket = ($buildOutputs | Where-Object OutputKey -eq 'BuildSourceBucketName').OutputValue
$sourceKey = ($buildOutputs | Where-Object OutputKey -eq 'BuildSourceObjectKey').OutputValue
$buildProject = ($buildOutputs | Where-Object OutputKey -eq 'BuildProjectName').OutputValue
$sourceArchive = Join-Path $env:TEMP 'asset-shepherd-build.zip'
$imageTag = "$(git rev-parse --short=12 HEAD)-$(Get-Date -Format yyyyMMddHHmmss)"

git archive --format=zip --output=$sourceArchive HEAD
aws s3 cp $sourceArchive "s3://$sourceBucket/$sourceKey" `
  --profile asset-shepherd-admin `
  --region us-east-1

$buildId = aws codebuild start-build `
  --profile asset-shepherd-admin `
  --region us-east-1 `
  --project-name $buildProject `
  --environment-variables-override "name=IMAGE_TAG,value=$imageTag,type=PLAINTEXT" `
  --query 'build.id' `
  --output text
```

Inspect the build in **AWS Console → CodeBuild → Build projects →
`asset-shepherd-contest-runtime`**, or query it without exposing any credentials:

```powershell
aws codebuild batch-get-builds `
  --profile asset-shepherd-admin `
  --region us-east-1 `
  --ids $buildId `
  --query 'builds[0].{status:buildStatus,image:environment.environmentVariables[?name==`IMAGE_TAG`].value|[0],logs:logs.deepLink}'
```

The ECR repository and image lifecycle are retained if the build stack is deleted. The ephemeral
source archive expires automatically; never upload a working-directory zip or `.env` file.

## AgentCore and public web stacks

`cloudformation/agentcore-runtime.yaml` deploys the private ARM64 AgentCore Runtime and its
service-only execution role. `cloudformation/web-express.yaml` deploys the x86_64 ECS Express Mode
web service, encrypted command/DLQ queues, and the one-message Lambda dispatcher. The dispatcher
has no provider secret and may invoke only the configured runtime plus its `DEFAULT` endpoint.

The live request path is:

`browser → ECS Express → SQS → Lambda → AgentCore/Strands → Bedrock`

S3 owns immutable GLBs, evidence, packages, and Strands snapshots. DynamoDB owns conditional
workspace versions and command receipts. Do not place GLB bytes, provider keys, AWS credentials, or
free-form filesystem paths in SQS messages.

OpenAI and Meta are supported application adapters but are not configured on the public contest
stack yet. When enabled, store their production keys in AWS Secrets Manager, grant only the exact
AgentCore execution role `secretsmanager:GetSecretValue` on the selected secret ARNs, and inject
the chosen provider/model as non-secret configuration. Never put API keys in CloudFormation
parameters, container images, source archives, task environment values, or browser responses.
