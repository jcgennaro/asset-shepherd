# Smartpad Tablet: clipped evidence and provider comparison

Date: 2026-09-04 (local); hosted failure saved 2026-09-05 UTC.

Source SHA-256: `c4ed1944da0f21561fa15f96bbae734e9a8e92f7c90c20e506af1126ce657dea`.
The private source and original artifacts remain in the workspace store, not this document.
Local diagnostic artifacts are under ignored `build/validation/tablet-render-failure/`.

## Failure and cause

The hosted Kimi K2.5 run inspected the source successfully, then failed visual sensing. The saved
front image was 512 x 512, right/back images were 404 x 404, and left was 317 x 317. The back mask
touched the right edge and the left mask touched both right/bottom edges. The validator correctly
rejected `back.png: asset is clipped`. The screenshot really was cropped; this was not an overly
strict validator or a Bedrock content-policy intervention.

The vendored model-viewer's adaptive render scale changes on a slow software GPU. Its `toBlob`
implementation uses reduced render-buffer dimensions to crop the full-size display canvas.
The dedicated headless evidence page now sets the public static `minimumRenderScale` to 1 and
rejects unexpected capture dimensions. This does not alter the interactive viewer, send larger
images to the model, or relax evidence quality checks. Render contract 7 invalidates old caches.

Kimi retried the plan ten times, encountering the same failed prerequisite each time. A Strands
after-tools hook now stops after two identical visual-sensing failures in one invocation, even
across different tool names. It retains the actual error and invocation ledger before returning
control. Argument-validation failures are not classified as renderer failures. All primary and
recovery agents use the hook; an explicit new invocation resets the counters. The UI explains
rendering/clipping failures without exposing private provider diagnostics or claiming that no
earlier repair exists.

## Bounded live comparisons

The confirmed target, profile, provenance, and source were copied unchanged for the comparisons.
They ran on the local fixed harness using the existing DPAPI-protected API credentials. No hosted
workspace was retried or overwritten. Neither comparison supplied consequential approval.

| Model | Harness | Time | Input tokens | Output tokens | Outcome |
|---|---|---:|---:|---:|---|
| Kimi K2.5, Bedrock | Original hosted renderer | 167.31 s | 117,798 | 3,980 | Turn limit; 1 render failure and 10 rejected plan calls |
| Luna, xhigh, OpenAI API | Fixed local renderer | 53.14 s | 46,543 | 4,074 | Valid proposal, native approval interrupt |
| Muse Spark 1.3 Contributor, effective high | Fixed local renderer | 69.07 s | 47,618 | 4,445 | Valid proposal, native approval interrupt |

Both comparison models requested uniform fitting and display-name cleanup, retained the single
semantic piece, avoided simplification of the 4,992-triangle mesh, and avoided an unsupported yaw
guess. Both chose footprint-bottom pivot placement; Luna also explicitly requested grounding.
Muse's prose says "1cm" but the actual tool uses proportional best-fit bounds, not an exact
independent thickness constraint. These are proposal-stage observations, not verified repaired
outputs or a broad model-quality ranking.

Each successful comparison made one inspect, one render, one plan, and one execution-tool call.
The execution call raised the native approval interrupt and performed no mutation. Strands counts
that interrupt as a tool error in these metrics; it is not a failed repair. Source hashes remained
unchanged. The fixed renderer's four views each measured 512 x 512 with minimum frame margins of
16.6% or 23.0%. The historic cloud and new local timings include different runtime environments,
so they cannot isolate model latency from infrastructure or renderer fixes.

Reproduce a proposal-only comparison with `scripts/replay_saved_assessment.py`, supplying a private
saved source directory containing `source.glb`, `profile.json`, `intent.json`, and `workspace.json`,
a new output directory, and an explicitly selected provider/model. Supply credentials only through
the existing protected launcher pattern. Muse Contributor requires the evaluation-only training
consent flag; production must use standard non-Contributor mode. No injection-attempt testing is
permitted or needed for this regression.
