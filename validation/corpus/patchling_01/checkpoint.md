# Patchling blind-baseline checkpoint

**State:** provisional; raw provenance still needs human completion and public-use confirmation.

## Raw handoff

- Untouched filename: `friendly repair robot 3d model.glb`
- Size: 4,860,944 bytes
- SHA-256: `dc2f03ae8ed368f46c2a4ac9e2ebb71f23e980b0c9e6913c685d011e273f418d`
- Repository raw copy: `raw/asset.glb` (ignored, byte-identical, not committed)
- Product version: `085545efdda09aa3a77aa115ce521ab4dfecb3b0`

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

## Preliminary visual assessment

The asset has a strong friendly courier-robot silhouette, stable feet, readable front/back,
asymmetric backpack, shepherd-like collar, repair tool, and warm accent. It is a good mascot and demo
candidate. Human visual adjudication remains required.

## Known limitations

- The export has one opaque, double-sided material and only a base-color JPEG. It has no normal,
  occlusion, metallic-roughness, emissive, or transparency texture/channel.
- The screen is visually blank rather than an expressive face; the tool is a conventional wrench
  rather than clearly crook-shaped; the wayfinding-post motif is ambiguous.
- At 18,727 triangles it is slightly below the preferred 20,000-triangle lower bound, though well
  within the hard 100,000-triangle budget.
- Unreal comparison and the human-cleaned reference do not exist yet.
- Generation time, Tripo model/mode and settings, selection rationale, export settings, and
  public-use rights still require human provenance.
