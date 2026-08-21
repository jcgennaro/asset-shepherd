# Patchling blind-baseline checkpoint

**State:** complete; raw provenance, public-use rights, blind results, and visual adjudication are
recorded.

## Raw handoff

- Untouched filename: `friendly repair robot 3d model.glb`
- Size: 4,860,944 bytes
- SHA-256: `dc2f03ae8ed368f46c2a4ac9e2ebb71f23e980b0c9e6913c685d011e273f418d`
- Repository raw copy: `raw/asset.glb` (ignored, byte-identical, not committed)
- Product version: `61e18d686625320c1b0306f6bf105ed917fa380b`

## Tripo provenance and rights

- Workspace item ID: `853e8986-e0e3-4d8e-a977-439ac9155787`
- Workspace reference:
  `https://studio.tripo3d.ai/workspace/generate/853e8986-e0e3-4d8e-a977-439ac9155787`
- Tripo mode: Smart Mesh P1.0, Fast, 25,000 target polygons, quad topology target.
- Tripo UI timestamp: `08-21 17:49` in an America/New_York browser session, recorded as
  `2026-08-21T21:49:00Z`.
- Export panel: GLB, filename `friendly repair robot 3d model`, texture resolution `4k (Current)`.
- Rights: the user confirmed on 2026-08-21 that the asset was generated with a paid Tripo account
  and has commercial rights for public repository and demo use.

The UUID is recorded conservatively as a Tripo workspace item ID. It is not described as a model
version or generation-job ID, and the link is not assumed to be publicly accessible.

## Exact workflow commands

```powershell
uv run asset-shepherd plan validation/corpus/patchling_01/raw/asset.glb `
  --profile profiles/unreal_indie_robot.json `
  --output validation/corpus/patchling_01/blind_asset_shepherd

uv run asset-shepherd run validation/corpus/patchling_01/raw/asset.glb `
  --profile validation/profiles/small_stylized_static_mesh.json `
  --approvals validation/templates/no-approvals.json `
  --output validation/corpus/patchling_01/blind_asset_shepherd

& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background `
  --python validation/blender/inspect_glb.py -- `
  --asset validation/corpus/patchling_01/raw/asset.glb `
  --output validation/corpus/patchling_01/observed_real_world/blender_raw.json

& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background `
  --python validation/blender/inspect_glb.py -- `
  --asset validation/corpus/patchling_01/blind_asset_shepherd/repaired.glb `
  --output validation/corpus/patchling_01/observed_real_world/blender_shepherd.json

uv run python -m asset_shepherd.validation.register `
  validation/corpus/patchling_01/raw/asset.glb `
  --provenance validation/corpus/patchling_01/provenance.json
```

## Blind result

- The GLB parses and is eligible as a static mesh.
- Represented dimensions are 0.771484 × 0.998047 × 0.673828 meters and it is grounded and Y-up.
- It contains 26,135 vertices, 18,727 triangles, one mesh, one node, one material, one texture, and
  one readable embedded 4096 × 4096 JPEG.
- It has no skin, animation, morph targets, negative determinant, or non-uniform transform.
- The addendum's 0.9–1.5 m compact-asset height preference is satisfied.
- The canonical plan contains only two policy-safe display-name repairs. There is no human approval
  card and no normalization transform.
- Verification is `PASSED_PROJECT_READY`; source hash, geometry, bounds, material, texture, and image
  availability are preserved. A second plan is empty.

The first measurement used the existing 1.8 m robot profile and proposed an unnecessary 1.8035225×
scale transform. That prediction is preserved under
`observed_real_world/profile_mismatch_unreal_indie_robot/`. The canonical rerun uses a general
small-stylized-static-mesh profile derived directly from the addendum's approved height range. No
asset-ID dispatch or product-code special case was added.

## Independent consumer result

Blender 5.1.2 imports both raw and Shepherd outputs successfully. Both have identical bounds, one
mesh object, 26,135 vertices, 18,727 polygons, one material, one packed 4096 × 4096 image, and no
missing image. The repaired output changes only the invalid mesh and node display names.

## Visual adjudication

The asset has a strong friendly courier-robot silhouette, stable feet, readable front/back,
asymmetric backpack, shepherd-like collar, repair tool, and warm accent. It is a good mascot and demo
candidate. Blender turntables show no visible raw-versus-Shepherd regression, and the user approved
continuing with it after review. Both objective name findings are adjudicated as true positives.

The one-material limitation is not repaired: material creation or artistic texture editing is outside
the MVP. Patchling remains the visual hero and preservation case, while later corpus assets carry the
multi-material, transparency, emissive, and normal-map stress coverage.

## Known limitations

- The export has one opaque, double-sided material and only a base-color JPEG. It has no normal,
  occlusion, metallic-roughness, emissive, or transparency texture/channel.
- The screen is visually blank rather than an expressive face; the tool is a conventional wrench
  rather than clearly crook-shaped; the wayfinding-post motif is ambiguous.
- At 18,727 triangles it is slightly below the preferred 20,000-triangle lower bound, though well
  within the hard 100,000-triangle budget.
- Unreal comparison and the human-cleaned reference do not exist yet.
- The Tripo workspace reference may require the owner's authenticated account and is provenance,
  not a public reproducibility dependency.
