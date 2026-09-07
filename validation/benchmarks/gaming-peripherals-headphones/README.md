# Gaming peripherals: keep only the headphones

**Status: pending user test.** Possible voiceover/demo story, not a validated success claim.

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
