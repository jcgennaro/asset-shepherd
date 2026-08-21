# Tripo generation card: Shader Lantern

## Request

- Generate exactly 3 candidates.
- Use Smart Mesh P1.0, Fast, 25,000 target polygons, and quad topology if those controls remain
  available; record any changed labels exactly.
- Select 1 candidate using the criteria below.
- Export the selected candidate as an untouched textured GLB.
- Place it at `validation/corpus/shader_lantern_01/raw/asset.glb`.

## Exact prompt

```text
Create a single isolated stylized 3D game prop called the Shader Lantern: a whimsical fantasy-technology workshop lantern used by tiny repair agents. It has a sturdy grounded base, thin protective cage elements, a glass or translucent chamber, a warm emissive core, painted metal, worn rubber grips, and subtle cloth or cord details. Strong clean silhouette, detailed PBR textures, game-ready, centered, full object visible, no background, no ground plane, no text, no letters, no logos, no characters, no extra detached objects, no franchise resemblance.
```

## Selection criteria

Prefer clearly visible glass or transparency, a distinct warm emissive surface, thin intact cage
geometry, an obvious base and upright direction, multiple material slots or PBR texture channels,
strong silhouette, no recognizable franchise resemblance, and no skin, animation, or morph targets.
Retain a plausible natural material/import defect if the asset remains usable as a static mesh.

## Export settings

- Format: GLB.
- Texture resolution: 4K Current (or the nearest available setting at or below 4096).
- Include/embed all generated materials and textures.
- No rigging, skin, animation, or morph-target export.
- Preserve original generated geometry; no cleanup, scale, rename, decimation, or re-export.
- Disable Draco/mesh compression if Tripo exposes that option.
- Do not run Tripo PBR, Edit, Upscale, Retopo, or another post-process on the selected raw candidate.

## Do not inspect or modify before ingestion

Do not open the selected GLB in Blender, Unreal, or another DCC. Do not inspect or change hierarchy,
transforms, names, pivots, materials, textures, or geometry. Copy the untouched export directly to
the destination path so Asset Shepherd's blind prediction is frozen before human diagnosis.

## Provenance to return with the file

Record the generation UTC date, Tripo workspace link, exact model/mode and settings, why this
candidate was selected, exact export-panel values, intended real-world height or range, and
confirmation that the selected output may be used publicly in the repository and demo.
