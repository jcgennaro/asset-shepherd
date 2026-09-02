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
| Direct OpenAI / GPT-5.6 Luna xhigh / prompt v16 | Preserved all intentional parts and simplified normalized input from 783,571 to 56,885 triangles | 1 plus bounded recovery | Passed with warnings | 123.75 s | 376,106 |
| Bedrock Converse / Kimi K2.5 / prompt v16 | Preserved all intentional parts and produced the identical deterministic 56,885-triangle candidate | 1 approval interrupt | Passed with warnings | 94.96 s | 159,666 |

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

## Viewing-use simplification chronology

The prompt-v16 feature comparison starts from Luna's already normalized 30,204,752-byte result so
neither provider spends the test turn on scale, grounding, or names. The confirmed use is **normal
gameplay**, which freezes a 15,000-triangle soft cap. The target story explicitly identifies the
many disconnected decorative construction parts as intentional.

Luna inspected and rendered the asset, preserved the coherent 65-body assembly, and proposed only
the new approval-required mesh simplification. The deterministic reducer protected 63 components
and 3,611 triangles face-for-face. The verified output contains 56,885 triangles and 52,917 vertex
tuples and measures 7,710,004 bytes. It remains above the soft cap because the reducer stopped at
its attribute and component-preservation constraints; the report says so rather than pretending an
attempt reached the requested target. Materials, textures, UVs, normals, names, bounds, and source
bytes passed independent checks.

The approved run ended before packaging and its first recovery exposed clipped shared-scale views.
The source and candidate were both present, but `<model-viewer>` had clamped camera distance from
the primary model's orbit range. The renderer now expands that range after load and gives comparison
captures additional framing headroom. A real Chromium regression puts two equal-size assets in the
same scene and proves every object-mask edge has clear margin. The same saved Luna run then resumed,
completed visual reassessment, and packaged without repeating the mutation.

After interactive AWS reauthentication, Kimi K2.5 made the same isolated recommendation: preserve
the intentional disconnected construction and apply only `simplify-mesh-v1`. It produced the exact
same deterministic candidate as Luna (`0ac0c3d0…`): 56,885 triangles, 52,917 vertex tuples, and
7,710,004 bytes. It completed in 94.96 seconds using 159,666 recorded tokens, with no post-approval
recovery. That is 23% less observed time and 58% fewer recorded tokens than this Luna run. It is not
a controlled general model ranking because Luna's ledger includes an early end-turn and renderer-
failure recovery; it does show that both provider adapters reach the same safe mutation on this case.

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
