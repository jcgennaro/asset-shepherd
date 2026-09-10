# Gaming peripherals: keep only the headphones

**Status: user-reported visual success with Luna xhigh; downloaded candidate passes corrected
offline deterministic verification with remaining warnings (2026-09-09, D126).**

The initial user estimate was almost 100 parts. The saved evidence establishes **55 exact
components**, of which 43 were removed and 12 retained. The screenshots show headphones separated
from the peripherals, but label the candidate rejected/not ready. D126 traced that rejection to
incompatible component-count definitions in verification, not a failed triangle budget. The
offline correction does not rewrite the historical hosted result or establish full target readiness.

## Saved run and offline reverification

- Workspace: `5488cf452a504f28ba302bdb0348d290`.
- Hosted execution: 2026-09-10 02:14:02–02:15:59 UTC (September 9 evening in New York).
- Approved action: retain only the headphones; remove 43 selected components and rename node/mesh.
- Triangles: **18,417 → 12,459**, below the normal-gameplay 15,000 soft cap.
- Output SHA-256: `b28b5c90d7a149caa087b5e281a052340e1e78af143e782157abd795fb2b77a4`.
- Downloaded GLB: 5,149,560 bytes. Index-only removal retains unused source vertex data, so this
  operation is not file-size optimization.
- Original verification: failed only the count comparison (12 planned vertex-connected components
  versus 25 edge-connected islands). Exact surviving geometry and resources passed.
- D126 offline verification: all 30 deterministic checks pass, including a consistent 12 → 12
  component count and independent Trimesh reload. Source/output hashes and frozen profile hash
  were checked against the downloaded provenance; neither GLB was rewritten.
- Remaining warnings: disconnected forms, non-manifold/inconsistently wound edges, unused vertices.
- Candidate dimensions: approximately 48.05 × 50.78 × 29.30 cm; target was 18 × 20 × 9 cm.
  Scaling was not part of this executed turn. No new model call or visual reassessment was made.

The owner supplied `gaming-headphones-evidence.zip` and `gaming-headphones-candidate.glb` locally.
The regenerated local report is `build/headphones-reverification.json`; original evidence remains
unchanged. The evidence ZIP does not establish model ID, token usage, or cost; Luna xhigh remains
owner-reported. No downstream Unreal acceptance or general success-rate claim follows from this run.

## Source

- [Untouched GLB](raw/asset.glb): 5,074,436 bytes (about 5.1 MB).
- [Tripo generation workspace](https://studio.tripo3d.ai/workspace/generate/7cea46d6-e541-4bf8-b14e-8bbc92b7d182).
- [Source hash, rights confirmation, and provenance](source.json).

Exact user-supplied generation prompt:

> a set of stylish gamer's PC peripherals, including headphones, keyboard, and mouse. use yellow, blue, and light beige accents.

The user reports that the result contains headphones, a keyboard, a PC, and another unidentified
object. No component IDs or counts have been assumed, and no asset-specific behavior is added to
the product. The source has only been copied and hashed, not repaired or re-exported.

## Intended test

Upload the original and explain: **“Out of this set, I only want the headphones.”** Confirm the
intended engine, dimensions, and viewing use with the agent rather than inventing a target here.
Review the labeled removal proposal before approving it. The headphones may consist of several
disconnected components; a single semantic object does not necessarily mean a single component.

Check that the result keeps the complete headphones—including both earcups and the headband—while
removing unwanted objects, preserving visible materials and textures, and remaining downloadable.
If the geometry is inseparable with supported tools, an honest limitation is preferable to
destructive guessing. Record refinements and failures as well as successes.

## Run record to complete after the user's test

- Hosted workspace ID, date, deployed version, and provider/model.
- Exact target description, confirmed target, and viewing use.
- Proposed component selections and the user's actual approvals.
- Before/after screenshots and downloaded result/evidence hashes.
- Verification outcome, visible preservation, and any unresolved findings.
- Elapsed time, recorded token usage, and cost estimate when available.
- User visual assessment and whether this is suitable for the demo.

Do not trash the test workspace before saving the evidence needed for this record.

## Possible voiceover angle — conditional on results

“I asked a generator for a set of gaming peripherals, but I only need the headphones for my game.
Instead of manually picking apart the whole scene, I can explain what I want to keep and review
Asset Shepherd's proposed changes.”

Only add an outcome statement after the saved run and the user's visual assessment support it.
This story does not establish broad accuracy, a measured time saving, or downstream Unreal
acceptance. Generation details remain incomplete, so this benchmark does not close the formal
real-world validation gates.
