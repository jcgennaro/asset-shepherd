# Tripo generation card: <display name>

## Request

- Candidates: `<2 or 3>`
- Final export: untouched textured `GLB`
- Destination: `validation/corpus/<asset_id>/raw/asset.glb`

## Exact prompt

```text
<approved prompt copied verbatim>
```

## Candidate selection

Select one candidate for silhouette, PBR variety, semantic orientation, originality, static-mesh
eligibility, realistic complexity, and demo appeal. Retaining a plausible natural failure is useful;
do not select solely for cleanliness.

## Export settings

- GLB with PBR materials and textures embedded.
- No rig, skin, animation, or morph targets.
- Preserve original geometry; do not clean, scale, rename, decimate, or re-export.
- Disable Draco/mesh compression if the exporter exposes that option.
- Keep texture dimensions at or below 4096 when selectable without editing the asset.

## Before handoff

Do not open the selected GLB in Blender or Unreal. Do not inspect or modify its hierarchy, transforms,
names, materials, textures, or geometry. Copy the untouched export directly to the destination.

Record `generation_date_utc`, exact prompt edits, model/mode, settings, selection reason, export
settings, notes, and public-use confirmation in the adjacent `provenance.json`. Asset Shepherd will
compute `raw_sha256` during registration.
