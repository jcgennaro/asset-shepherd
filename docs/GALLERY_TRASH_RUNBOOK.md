# Gallery trash

## Scope

Gallery offers a compact trashcan on saved assets and upload drafts. Its accessible label names
the asset. A native OK/Cancel confirmation asks: "Deletion is permanent and removes the workspace
and any stored files. Are you sure?" Cancel prevents both POST and the busy state. Detailed
shared-Gallery, accounting, and retention information remains in FAQ rather than on every card.
Existing login and same-origin enforcement protect the route. This is not a soft-delete bin.

Local deletion removes only the validated workspace directory, including original/candidate GLBs,
archives, evidence, and conversation state. Related local redo drafts are discarded too. Active
upload checks must finish first. Description/redo/upload/trash share a local mutation lock.

Hosted cleanup verifies the configured application owner, then deletes **all S3 versions and
delete markers** under exactly:

- `workspaces/<workspace-id>/`
- `sessions/session_<workspace-id>/`

It also deletes `COMMAND#<workspace-id>` receipts and the owner-bound `WORKSPACE#<workspace-id>`
pointer. The pointer is removed last; failed cleanup remains visible and retryable, with reads
and writes fenced by `deletion_status=DELETING`. Gallery rechecks GSI results against consistent
STATE reads so a removed slot is not revived by index lag. Spending partitions are never touched.

The current web cache is erased. Other task-local caches disappear on task/runtime replacement;
they are no longer addressable through the application once the authoritative pointer is gone.
Minimal CloudWatch operational logs and cost accounting follow their independent retention.
Downloaded user copies are outside this operation's scope. Do not promise forensic erasure.

## Concurrency and failure recovery

`LOCK#<workspace-id> / MUTATION` is an exclusive DynamoDB token, shared by full AgentCore
invocations, web queue admission, artifact persistence, and trash. Reentrant calls inside the
same repository invocation reuse it. The lock is conditionally released by its exact token.
Queue admission writes the receipt under the lock, then releases it **before** SQS delivery so
an immediate consumer is not falsely blocked. Trash winning between release and delivery makes
the late message unclaimable rather than reviving the deleted workspace.
Queued messages whose receipts were removed cannot claim work. A returning Lambda must not
recreate a deleted receipt.

Locks deliberately have **no automatic expiry**: a timed-out observer does not prove that a
writer has stopped. After a process crash, Trash may continue to report busy. An operator must
verify that the associated runtime invocation, web operation, and queue activity have stopped
before conditionally removing that exact lock token. Do not clear every lock, shorten a lease,
or run the older administrator purge script against an active writer.

If cleanup partially fails, fix the underlying permission/service problem and retry Trash on
the same card. Do not delete the STATE pointer first to make the card disappear.

## Deployment gate

Deploy the runtime fencing change before exposing the web trash action. Drain old in-flight
commands, then update the web image, dispatcher bundle, and web task IAM policy. New permissions
are `s3:ListBucketVersions` with existing workspace/session prefix restrictions and
`s3:DeleteObjectVersion` on those artifact prefixes only. No new service or paid model call is
needed. Existing DynamoDB item permissions cover locks.

Existing AgentCore sessions can retain old code even after DEFAULT points at the new version
([AWS session-version troubleshooting](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-troubleshooting.html)).
After proving the queue and workspace receipts idle, retire the known old runtime sessions before
enabling Trash; this removes process caches, not the durable asset or Strands history. During the
D124 rollout all six saved Gallery runtime sessions were already absent. Runtime 12 / DEFAULT
was READY before the web update began.

Validate with a disposable synthetic fixture only: create a workspace and versioned/session
artifacts, exercise Trash, verify both S3 prefixes and DynamoDB records are empty, and confirm
the Gallery slot and old artifact routes are gone. Verify unrelated assets and `SPEND#` records
are untouched. Never use a saved user test run for destructive acceptance.

Local regression coverage includes confirmation/POST-only behavior, full local removal, drafts
and redo cleanup, stale queue admission, other-owner denial, live writer exclusion, partial
failure/retry, version/delete-marker removal, and preservation of unrelated assets/accounting.
Hosted rollout and acceptance evidence are recorded in `PROJECT_STATUS.md`.
