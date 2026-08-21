# Tripo generation card: Patchling Courier

## Request

- Generate exactly 3 candidates.
- Select 1 using the criteria below.
- Export the selected candidate as an untouched textured GLB.
- Place it at `validation/corpus/patchling_01/raw/asset.glb`.

## Exact prompt

```text
Create a single isolated stylized 3D game asset of a friendly small repair-courier automaton named Patchling. It is an original whimsical shepherd-inspired helper robot with a clearly readable face and front direction, compact stable feet, a braided cable tail or scarf, one asymmetrical utility satchel, a crook-shaped repair wrench, and a small geometric wayfinding post attached to its backpack. Use painted metal, rubber, cloth, glass, and one warm emissive diagnostic light. Include a clear translucent visor if feasible. Strong clean silhouette, charming fantasy-technology design, detailed PBR textures, game-ready proportions, full body visible, centered, no background, no ground plane, no text, no letters, no logos, no weapons, no human, no extra detached props, no franchise resemblance.
```

## Selection criteria

Prefer a clear front/back, visible stable feet, strong texture variety, an asymmetric silhouette,
visor or emissive detail, moderate complexity, no recognizable franchise resemblance, and no skin,
animation, or morph targets. Do not choose solely for cleanliness; a plausible natural import defect
is useful if the asset remains a static-mesh candidate.

## Export settings

- Format: GLB.
- Include/embed PBR materials and textures.
- No rigging, skin, animation, or morph-target export.
- Preserve original generated geometry; no cleanup, scale, rename, decimation, or re-export.
- Disable Draco/mesh compression if Tripo exposes that option.
- Keep selectable texture dimensions at or below 4096 without manually resizing textures.

## Do not inspect or modify before ingestion

Do not open the selected GLB in Blender, Unreal, or another DCC. Do not inspect or change hierarchy,
transforms, names, pivots, materials, textures, or geometry. Copy the untouched export directly to
the destination path so Asset Shepherd's blind result is frozen before human diagnosis.

## Provenance to record

Fill the adjacent `provenance.json` with generation UTC date, any prompt edits verbatim, Tripo
model/mode, generation settings, selection reason, export settings, notes, and confirmation that the
selected output may be used publicly in the repository and demo. Leave `raw_sha256` empty; the
registration tool computes it from the untouched file.
