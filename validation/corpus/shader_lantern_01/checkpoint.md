# Shader Lantern blind-ingestion checkpoint

**State:** registered and frozen at the required physical-normalization approval; no repair,
verification, Blender import, Unreal import, or visual adjudication has occurred.

## Raw handoff

- Untouched filename: `stylized lantern 3d model.glb`
- Size: 12,813,168 bytes
- SHA-256: `be2c9cab8d4e51f7a948c7c54db7a10c932f24faf69bc3166ff724ccc00c49b9`
- Repository raw copy: `raw/asset.glb` (byte-identical)
- Workspace item ID: `2ba39d05-0e1e-4e4c-867c-7e38eb2c1d09`
- Workspace reference:
  `https://studio.tripo3d.ai/workspace/generate/2ba39d05-0e1e-4e4c-867c-7e38eb2c1d09`

The authenticated workspace displayed `08-21 19:35` in America/New_York, Smart Mesh, quad
topology, 50,787 faces, 50,674 vertices, and the export panel values `GLB` and `4k (Current)`.
The item page did not expose the exact Smart Mesh version or speed preset, so provenance records
those fields as unverified rather than inferring them. The user handed off the untouched export and
had already confirmed that this paid Tripo account grants commercial rights for public repository
and demo use.

## Exact commands

```powershell
Get-FileHash -Algorithm SHA256 `
  -LiteralPath 'C:\Users\jcgen\Downloads\stylized lantern 3d model.glb'

Copy-Item `
  -LiteralPath 'C:\Users\jcgen\Downloads\stylized lantern 3d model.glb' `
  -Destination 'validation\corpus\shader_lantern_01\raw\asset.glb'

uv run python -m asset_shepherd.validation.register `
  validation/corpus/shader_lantern_01/raw/asset.glb `
  --provenance validation/corpus/shader_lantern_01/provenance.json

uv run asset-shepherd plan `
  validation/corpus/shader_lantern_01/raw/asset.glb `
  --profile validation/profiles/small_stylized_static_mesh.json `
  --output validation/corpus/shader_lantern_01/blind_asset_shepherd
```

## Frozen blind result

- The GLB parses and is eligible as a static mesh.
- Represented dimensions are 55.988098 × 99.908905 × 57.944229 meters. It is grounded and its
  dominant extent is already Y-up.
- It contains 77,545 vertices, 101,564 triangles, two nodes, one mesh, one material, three textures,
  and three readable embedded 4096 × 4096 images.
- Embedded PBR resources include a JPEG base-color image, PNG roughness/metallic image, and JPEG
  normal image. Used extensions are `FB_ngon_encoding`, `KHR_materials_specular`, and
  `KHR_materials_volume`; none is required.
- It has no skin, animation, morph targets, negative determinant, or non-uniform scale.
- Safe candidates rename one mesh and one node without changing index references.
- The 101,564-triangle count exceeds the selected 100,000-triangle profile budget by 1,564 and is
  correctly report-only. Asset Shepherd does not alter topology.
- `normalize-root-v1` proposes a reversible `0.0120109414` uniform root scale, changing the
  represented height from 99.908905 meters to 1.2 meters. It requires human approval.

## Frozen artifact tree

```text
shader_lantern_01/
├── checkpoint.md
├── generation-card.md
├── prompt.md
├── provenance.json
├── raw/
│   └── asset.glb
├── blind_asset_shepherd/
│   ├── inspection.json
│   ├── repair_plan.json
│   └── report.md
└── observed_real_world/
    └── adjudication.json
```

## Pending decision and limitations

The selected general small-stylized-static-mesh profile targets 1.2 meters with a ±0.3-meter
tolerance, but the user has not supplied an intended real-world height for this lantern. The
contract assigns physical-scale approval or rejection to the user. Asset Shepherd therefore has not
executed either the normalization or the safe name repairs, and `decisions.json`, `verification.json`,
`provenance.json` for the job, `repaired.glb`, and `result.zip` do not yet exist.

No one has opened or visually diagnosed the Lantern after this blind prediction. Blender and Unreal
evidence, appearance assessment, transparency/emissive adjudication, and material-preservation
claims remain intentionally pending until the approval is resolved and the blind output is frozen.
