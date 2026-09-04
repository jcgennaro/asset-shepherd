# Asset Shepherd AWS infrastructure

The checked-in infrastructure is intentionally incremental. The state stack is live; container,
AgentCore, and public-web stacks follow only after their acceptance gates pass.

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
