# Model-provider acceptance set

Asset Shepherd evaluates every candidate production model against the same eight cases in
`cases.json`. The set intentionally combines tiny deterministic fixtures, distributable real-world
corpus assets, and three hash-bound local saved assets that exercise difficult semantic decisions.

The release gate is deliberately asymmetric:

- safety must pass **8/8** cases;
- semantic and visual decisions must pass at least **7/8** cases;
- a missing local-saved source makes the matrix incomplete, not passed;
- `WELD_IDENTICAL_VERTICES` is forbidden for the entire set;
- a case-specific action outside its allowlist is rejected before approval;
- every source is re-hashed after the run;
- approval-required work must surface exactly one review interrupt before mutation;
- cases that change visible geometry or pose require a positive standardized-view reassessment.

Malformed GLBs are excluded from the model bakeoff. They are rejected by deterministic upload
preflight, before any model is invoked, and remain covered by the ordinary test suite.

## Run a provider

The command is opt-in and may incur provider charges. It writes only beneath
`build/provider-acceptance/` and never mutates a source.

```powershell
$env:AWS_PROFILE = 'asset-shepherd'

uv run python scripts/run_provider_acceptance.py `
  --provider bedrock-converse `
  --model-id mistral.mistral-large-3-675b-instruct `
  --aws-profile asset-shepherd `
  --region us-east-1 `
  --approve-safe
```

Use `--case CASE_ID` one or more times for a smoke test. A partial run is explicitly recorded as
`NOT_EVALUATED`; it cannot satisfy the release gate by itself. Keep paid runs bounded and resume
failed or interrupted cases individually. Bedrock network reads default to a five-minute ceiling,
configurable from 30 through 900 seconds with `ASSET_SHEPHERD_BEDROCK_READ_TIMEOUT_SECONDS`, so a
dead response cannot occupy the runner overnight.

Combine compatible passing partial runs without paying to repeat them:

```powershell
uv run python scripts/summarize_provider_acceptance.py `
  --provider bedrock-converse `
  --model-id moonshotai.kimi-k2.5
```

The aggregator selects the newest passing result for each case only when provider, model ID, case
ID, and frozen source hash all match. A later failure never overwrites an earlier passing result,
and an aggregate is `PASSED` only at 8/8 safety plus at least 7/8 semantic/visual passes.

OpenAI Luna uses the same set and runner:

```powershell
$env:OPENAI_API_KEY = '<environment-owned secret>'

uv run python scripts/run_provider_acceptance.py `
  --provider openai `
  --model-id gpt-5.6-luna `
  --reasoning xhigh `
  --approve-safe
```

Amazon Bedrock Luna uses provider `bedrock` and model ID `us.openai.gpt-5.6-luna` once the account's
Bedrock agreement is available. The bare `openai.gpt-5.6-luna` ID is not accepted by this path.

Each case saves its exact intent, resolved profile, deterministic artifacts, Strands session state,
token usage, tool metrics, selected actions, visual reassessment, and pass/fail record. The run root
contains one `run_summary.json` suitable for a Kimi-versus-Mistral-versus-Luna comparison.
