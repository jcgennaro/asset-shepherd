# Shattered-heart collar provider benchmark

This real generated GLB is a useful stress case because it looks coherent, measures roughly
1.90 × 0.62 × 1.88 m despite being a pet-collar-sized object, contains 783,571 triangles, and exposes
65 exact disconnected components to the agent. All 65 components fall into one scale-relative
near-contact group. That makes the case simultaneously useful for scale correction, false-positive
component handling, visual judgment, turn latency, and token-cost measurement.

The confirmed Unreal target is approximately 15 × 3 × 12 cm. Asset Shepherd uses proportional
best-fit scaling, so 11.84 × 3.89 × 11.73 cm is a valid result: it is the largest uniform fit inside
that box, not an attempt to force every dimension independently.

## Recorded runs

| Run | Topology judgment | Turns | Final state | Recorded agent time | Recorded tokens |
|---|---|---:|---|---:|---:|
| Bedrock Converse / Kimi K2.5 | Removed 64 proposed fragments; verification found 12 bodies, then refinement scaled the survivor | 2 | Passed with warnings | 167.25 s known, plus unretained pre-approval time | 257,998 lower bound |
| Direct OpenAI / GPT-5.6 Luna xhigh | Preserved the visually coherent near-contact assembly and scaled it immediately | 1 | Passed with warnings | 161.74 s | 412,929 exact for Shepherd |

Kimi was slow but effective after explicit refinement. Luna reached the same final dimensions in one
repair turn and was faster in wall-clock workflow time, but it needed the 15 × 3 × 12 cm dimensions
stated explicitly during intake and used substantially more recorded context tokens. The token
totals are not directly comparable: the old Kimi runtime lost pre-approval metrics, while the Luna
run used the new per-invocation ledger. Neither total includes semantic-intake calls.

## Kimi chronology

1. Kimi inferred the correct approximate target from the plain description.
2. It identified 65 exact disconnected components and classified C2–C65 as tiny fragments.
3. The approved first candidate removed 20,630 triangles, but independent verification reported
   **Attempted — verification did not confirm** because 12 exact bodies remained instead of one.
4. The candidate also remained at the original oversized world scale. The user refined with:
   `please shrink to the target size of 15 x 3 x 12 cm`.
5. The next turn uniformly scaled and grounded the candidate, producing
   11.84 × 3.89 × 11.73 cm and passing verification with triangle-budget and unused-vertex warnings.

The first after-action summary was too optimistic about component removal even though the check row
correctly said verification failed. Future reporting should lead with the failed deterministic
check and describe the retained candidate as partial progress.

## Luna chronology

1. Luna's first intake estimate without explicit dimensions was 16 × 18 × 2 cm. The description was
   revised to include the confirmed 15 × 3 × 12 cm target before the run.
2. Luna observed the same 65 exact bodies, 86 virtual-weld bodies, and one near-contact group. It
   judged the bodies to be intentional necklace construction rather than removable debris.
3. It proposed one reversible root normalization, grounding, and safe display-name cleanup. It
   explicitly declined welding because 81,091 coincident positions protect UV seams.
4. The approved result preserved all 783,571 triangles, measured
   11.84 × 3.89 × 11.73 cm, grounded at Y=0, and passed every deterministic verification check.

This is the safer topology decision for an automated MVP because visual coherence and near-contact
evidence do not prove that tiny bodies are disposable. Kimi's reduced candidate remains useful as a
user-approved alternative and as a test of partial component-removal verification.

## Conversation and observability findings

The refinement text previously appeared only after the synchronous model call completed. The web
notebook now appends the user's message immediately as a pending right-side conversation turn, then
keeps the working state below it while the request is in flight.

The workflow runtime now writes `output/agent_invocations.json` after every completed Shepherd
provider call, before an approval interrupt or server reconstruction can discard metrics. Final
`agent_result.json` aggregates that ledger. This makes future multi-turn duration, token, and tool
totals exact across interrupt/resume boundaries. Target-intake usage is still outside this ledger and
must be reported separately before end-to-end cost comparisons can be called exact.

## Rights and local evidence

The raw GLB is copied locally to `raw/asset.glb`, and the three user-supplied screenshots are copied
to `evidence/`. Both directories are ignored. The hash and run records are tracked, but the binary
asset and screenshots must not enter the public repository until public-use rights are explicitly
confirmed. See [source.json](source.json) for the current gate.
