# Hosted model-spending safety and judge access

## Agreed policy

The user selected a **$10 per UTC day site-wide emergency ceiling** on 2026-09-06.
Warnings go to the existing private operations SNS topic at **$5 and $8**. This is
abuse/runaway-cost protection, not a normal judge quota. No 24-runs/day shared hard cap
or individual judge email invitation requirement is introduced.

Use one dedicated shared judge login in Devpost's **private testing instructions**.
Keep practical free access available through October 8, 2026; an emergency ceiling
is not proof of unrestricted-access compliance. Monitor warnings and investigate
unexpected use before adjusting the ceiling. The judge account and private credential
handoff require owner activation. On 2026-09-06, Cognito accepted an invitation to the
owner-approved dedicated Gmail alias, with status `FORCE_CHANGE_PASSWORD`. No password
was generated locally, read, logged, or stored by the agent. The owner must set its permanent
password in a private browser window and save it in a password manager before sharing it
privately. Subsequent readback confirms permanent-password activation (`CONFIRMED`);
email verification remains false and a fresh judge-account end-to-end test is still needed.
The existing invite-only Cognito authentication remains in place.

The September screenshot supplied by the user totals $6.39 in AWS service costs.
That snapshot is not a remaining-credit balance and excludes direct OpenAI/Meta invoices.
This limit does **not** cap ECS, ALB, VPC, S3, DynamoDB, AgentCore, Guardrails, taxes,
or other AWS charges. It starts accounting on deployment, without backfilling past runs.

## How admission works

Both web target-intake calls (including the bounded retry) and every Strands model
request in the repair loop use one DynamoDB ledger. An atomic transaction reserves
the entire supported input/output token envelope before transmission, records a call
receipt, and acquires one of three site-wide model-call leases. No model request starts
if the transaction fails, its remaining room is insufficient, or all leases are occupied.

The standard provider service tier and existing output limits remain bounded. Direct
OpenAI SDK retries are disabled; Bedrock SDK total attempts are one in both intake and
workflow clients. New Strands
requests each need a new reservation. Internal geometry tools do not consume this ledger.
The wrapper preserves stateful Responses conversation semantics and refuses its unused
alternative structured-output path rather than permitting an unmetered call.

Complete provider usage refunds unused reservation once, transactionally. Cache discounts
are deliberately not assumed. OpenAI cached input is already in input tokens; Bedrock
separately reported cache input is added. Missing usage, uncertain transport outcomes,
process loss, and failed reconciliation retain the full reservation. Leases expire after
30 minutes, longer than the configured provider sockets; an expired lease never refunds
spending automatically. A call crossing midnight settles against its original UTC day.
Admission needs room for the next reservation, so it can pause slightly below $10.

The public message explains a spending pause and that saved assets/downloads remain
available. Browsing and downloads do not request a spending reservation. Existing per-turn
limits, typed approval, and authentication remain unchanged. No automatic replay occurs.

## Reviewed rate envelopes

Amounts are integer micro-USD, rounded up. USD per million tokens equals micro-USD per token.
These are conservative safety estimates, **not exact invoices**.

| Enabled provider/model | Input / output USD per million | Reserved input / output | Maximum reservation |
| --- | --- | --- | --- |
| Direct OpenAI `gpt-5.6-luna` | 0.50 / 1.80 | 1,050,000 / 8,192 | $0.539746 |
| Bedrock Converse `moonshotai.kimi-k2.5` | 0.60 / 3.00 | 262,144 / 16,384 | $0.206439 |

Luna uses conservative long-context and cache-write multipliers over the published
standard rates; its per-request service tier is explicitly `default`. The actual shorter
intake output cap remains 4,096. Sources reviewed 2026-09-06:
[OpenAI Luna model pricing](https://developers.openai.com/api/docs/models/gpt-5.6-luna)
and [AWS Bedrock pricing](https://aws.amazon.com/bedrock/pricing/).

Any other provider/model fails closed until its rate, maximum request envelope, usage
semantics, and hidden retries have been reviewed. This includes the currently inaccessible
Bedrock Luna profile and any future hosted Meta integration. Local experiments without
the ledger setting remain unchanged. Contributor/training opt-in is **not enabled for judges**.
Provider price changes or usage outside the reviewed envelope require operator review;
an application token estimate cannot guarantee an exact provider billing ceiling.

## Deployment and operations

Both `web-express.yaml` and `agentcore-runtime.yaml` require the same parameters:

- `DailyModelUsd=10`
- `SpendAlertTopicArn=<existing confirmed operations topic ARN>`

Both set `ASSET_SHEPHERD_SPEND_TABLE` to the existing workspace table and provide
`ASSET_SHEPHERD_DAILY_MODEL_USD` and `ASSET_SHEPHERD_SPEND_ALERT_TOPIC`. No new table,
monitoring daemon, or hosted service is created. Both roles gain only `sns:Publish` to
that exact topic. Existing item permissions cover the DynamoDB transactions, per
[AWS transaction IAM documentation](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis-iam.html).

Ledger partition keys are `SPEND#YYYY-MM-DD`, with `TOTAL`, `CALL#<random-id>`, and
`ALERT#50/80/100` sort keys. `TOTAL.charged` includes unresolved and active reservations.
`SPEND#SLOTS` holds the three leases. TTL retention is 45 days for accounting, with
shorter lease expiry. Records contain provider/model, state, and amounts—not asset
content, owner emails, credentials, or conversation text. No public endpoint exposes them.

Alert markers suppress ordinary duplicate deliveries. Failed SNS delivery can be retried
by later threshold checks after 60 seconds; uncertain delivery can produce duplicates.
Alerts are best effort, not a second enforcement mechanism. A 100% subject means there
is insufficient unreserved headroom for the next request, not that exactly $10 was billed.
There is no scheduled alert retry worker. Review the daily ledger if delivery errors appear.

On a warning, read that day's `TOTAL` and receipts using an authorized AWS console/CLI
session. Compare SETTLED amounts and UNKNOWN/RESERVED receipts against provider usage
before deciding whether the ceiling needs an explicit increase. Do not delete accounting
to resume requests; change the parameter consistently in both stacks if authorized.
Keep the normal AWS billing budget and provider-side account limits independently.

Gallery deletion must never delete `SPEND#` records. Existing admin purge targets only
the chosen workspace/session prefixes and `WORKSPACE#`/`COMMAND#` records. A public
permanent-trash feature still needs its own concurrency/ownership-safe implementation.

## Verification

Offline tests cover rate rounding, cache accounting, missing usage, every intake request,
streaming failures, denial before HTTP/model work, bounded slots, UTC rollover, duplicate
settlement protection, public messages, provider-factory wiring, and both cloud templates.
No paid model or injection-attempt tests are used.

A real DynamoDB check in an isolated random `SPENDTEST#` namespace admitted one of two
simultaneous Luna reservations against $1 of room. It settled to 680 micro-USD and stayed
there after duplicate settlement. Both temporary records were deleted and the namespace
verified empty. No saved workspace was touched and no model call was made.

The full local gate passes: 357 tests, three opt-in skips, Ruff, formatting, Pyright, and
lock validation. Source `15b0798` passed both AWS CodeBuild images, including Linux upload
acknowledgement and ARM64 fixed-resolution evidence-renderer/import/health checks.
Reviewed deployment changes modify only the two compute resources and their roles, without
replacement. The sole new permission is SNS Publish to the exact existing operations topic.
IAM simulations allow the required ledger item actions and that SNS action for both roles.
