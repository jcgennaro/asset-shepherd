# Shader Lantern approved deterministic-core checkpoint

**State:** complete for the approved inspect → plan → approve → repair → verify → package run,
Blender 5.1.2 import/re-export, and isolated Unreal 5.8 comparison.

## Raw handoff and approval

- Untouched filename: `stylized lantern 3d model.glb`
- Size: 12,813,168 bytes
- SHA-256: `be2c9cab8d4e51f7a948c7c54db7a10c932f24faf69bc3166ff724ccc00c49b9`
- Repository raw copy: `raw/asset.glb` (byte-identical)
- Workspace item ID: `2ba39d05-0e1e-4e4c-867c-7e38eb2c1d09`
- Workspace reference:
  `https://studio.tripo3d.ai/workspace/generate/2ba39d05-0e1e-4e4c-867c-7e38eb2c1d09`
- Human decision: the user approved the selected Tripo design as the Shader Lantern, stated an
  intended height of 1.2 meters, and approved `normalize-root-v1`.

The authenticated workspace displayed `08-21 19:35` in America/New_York, Smart Mesh, quad
topology, 50,787 faces, 50,674 vertices, and export settings `GLB` and `4k (Current)`. The item page
did not expose the exact Smart Mesh version or speed preset, so those provenance fields remain
unverified. The user confirmed commercial/public-use rights through the paid Tripo account.

## Exact commands

Run from the repository root in PowerShell. The first canonical-output command was deliberately
refused because its destination already contained the frozen prediction; no file was overwritten.
The fresh ignored build destination was then used and its results promoted after verification.

```powershell
uv run asset-shepherd run `
  validation/corpus/shader_lantern_01/raw/asset.glb `
  --profile validation/profiles/small_stylized_static_mesh.json `
  --approvals examples/approve_normalization.json `
  --output validation/corpus/shader_lantern_01/blind_asset_shepherd

uv run asset-shepherd run `
  validation/corpus/shader_lantern_01/raw/asset.glb `
  --profile validation/profiles/small_stylized_static_mesh.json `
  --approvals examples/approve_normalization.json `
  --output build/validation/shader-lantern-approved

$source = 'build/validation/shader-lantern-approved'
$destination = 'validation/corpus/shader_lantern_01/blind_asset_shepherd'
Copy-Item "$source/decisions.json","$source/job_result.json","$source/provenance.json",`
  "$source/repaired.glb","$source/report.md","$source/result.zip",`
  "$source/verification.json" -Destination $destination -Force
```

Blender inspection and round trip:

```powershell
$blender = 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'

& $blender --background --python validation/blender/inspect_glb.py -- `
  --asset validation/corpus/shader_lantern_01/raw/asset.glb `
  --output validation/corpus/shader_lantern_01/observed_real_world/blender_raw.json

& $blender --background --python validation/blender/inspect_glb.py -- `
  --asset validation/corpus/shader_lantern_01/blind_asset_shepherd/repaired.glb `
  --output validation/corpus/shader_lantern_01/observed_real_world/blender_shepherd.json `
  --save-blend build/validation/shader-lantern-blender/shepherd.blend `
  --reexport-glb build/validation/shader-lantern-blender/shepherd-reexport.glb

& $blender --background --python validation/blender/render_turntable.py -- `
  --asset validation/corpus/shader_lantern_01/raw/asset.glb `
  --output-dir validation/corpus/shader_lantern_01/observed_real_world/screenshots/raw

& $blender --background --python validation/blender/render_turntable.py -- `
  --asset validation/corpus/shader_lantern_01/blind_asset_shepherd/repaired.glb `
  --output-dir validation/corpus/shader_lantern_01/observed_real_world/screenshots/shepherd

uv run asset-shepherd inspect `
  build/validation/shader-lantern-blender/shepherd-reexport.glb `
  --profile validation/profiles/small_stylized_static_mesh.json `
  --output build/validation/shader-lantern-blender/reexport-inspection.json
```

Isolated Unreal setup and three-arm import comparison:

```powershell
$unreal = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$root = (Resolve-Path '.').Path.Replace('\','/')
$project = "$root/validation/unreal/AssetShepherdValidation.uproject"

& $unreal $project -unattended -nop4 -nosplash -nullrhi -stdout `
  -FullStdOutLogOutput -NoSourceControl -run=pythonscript `
  "-script=$root/validation/unreal/setup_validation_project.py --output $root/validation/corpus/shader_lantern_01/observed_real_world/unreal_setup.json"

& $unreal $project -unattended -nop4 -nosplash -nullrhi -stdout `
  -FullStdOutLogOutput -NoSourceControl -run=pythonscript `
  "-script=$root/validation/unreal/import_compare.py --raw $root/validation/corpus/shader_lantern_01/raw/asset.glb --shepherd $root/validation/corpus/shader_lantern_01/blind_asset_shepherd/repaired.glb --human-reference $root/build/validation/shader-lantern-blender/shepherd-reexport.glb --human-reference-role blender-re-export-control-not-human-cleaned --run-id shader_lantern_approved_01 --output $root/validation/corpus/shader_lantern_01/observed_real_world/unreal_comparison.json"
```

The Unreal visual pass opened `AssetShepherdValidation.uproject`, framed raw and Shepherd imports
individually in Unlit mode, and issued these console commands:

```text
HighResShot 1 filename=C:/Users/jcgen/Documents/asset-shepherd/validation/corpus/shader_lantern_01/observed_real_world/screenshots/unreal/raw.png
HighResShot 1 filename=C:/Users/jcgen/Documents/asset-shepherd/validation/corpus/shader_lantern_01/observed_real_world/screenshots/unreal/shepherd.png
```

Package audit:

```powershell
@'
import json
import zipfile
from pathlib import Path
from pygltflib import GLTF2

root = Path("validation/corpus/shader_lantern_01/blind_asset_shepherd")
expected = {
    "decisions.json", "inspection.json", "provenance.json", "repair_plan.json",
    "repaired.glb", "report.md", "verification.json",
}
with zipfile.ZipFile(root / "result.zip") as archive:
    assert set(archive.namelist()) == expected
    assert archive.testzip() is None
    for name in expected:
        data = archive.read(name)
        assert data == (root / name).read_bytes()
        if name.endswith(".json"):
            json.loads(data)
        if name == "repaired.glb":
            GLTF2.load_from_bytes(data)
print("ZIP_AUDIT_PASS")
'@ | uv run python -
```

## Tested cases and results

### Deterministic repair and verification

- Frozen inspection SHA-256:
  `a525917ccc7d952b66170ddcd4d6a487b9153fe38a044ef24c6a7226bb5e618b`.
- Frozen plan SHA-256:
  `4a7266479ccfe9cf066cdd78698bc40f0f339c41ebf2ee261212b2b02faa2301`.
- The candidate set remained exactly `rename-mesh-000`, `rename-node-001`, and
  `normalize-root-v1`.
- The two safe display-name repairs were auto-authorized. `normalize-root-v1` was recorded as
  `APPROVED` from the user approval file and executed with a uniform root-matrix diagonal of
  `0.012010941363516265` (the approved displayed value is `0.0120109414×`).
- Repaired SHA-256:
  `718722d6203dd0f0d62f86f42f0999e0d44c168f6f29767eee204d7d5631eebd`.
- Independent reload measured a 1.2-meter height, Y-up orientation, and grounded bounds. Vertex,
  triangle, material, and texture counts remained 77,545, 101,564, 1, and 3.
- The source hash remained unchanged, names became valid and unique, executed actions matched
  provenance, and a second plan was empty.
- Verification state is `PASSED_WITH_REMAINING_WARNINGS`. The only unresolved warning is
  `TRIANGLE_BUDGET_EXCEEDED`; the 1,564-triangle overage remains report-only and no topology was
  changed.

### Package audit

The ZIP passed CRC testing, contains the exact seven contracted artifacts, and each member is
byte-identical to its adjacent artifact. Every JSON member parses and `repaired.glb` loads as GLB
2.0. The ZIP contains no `job_result.json`; that file is a job-side convenience record and is not a
contracted ZIP member.

### Blender 5.1.2

- Raw and repaired imports both completed with one mesh, 77,545 vertices, 101,564 polygons, one
  material, and three packed/readable 4096² images. No image was missing.
- Raw dimensions were 55.988098 × 57.944229 × 99.908905 meters after Blender's glTF-to-Z-up axis
  conversion. Repaired dimensions were 0.672470 × 0.695965 × 1.200000 meters and remained grounded.
- Raw and repaired GLB `materials`, `textures`, `images`, `samplers`, `accessors`, and
  `bufferViews` records are byte-for-byte equivalent; the binary buffer SHA-256 is identically
  `f3cfe3ca82e9f554540f28b6d45cca375d4470c147b2df8934549572d9e0417a`. Mesh metadata differs only
  by the approved display name.
- Four proportionally framed 768×768 raw/repaired views visually match. Per-view full-frame pixel
  MAE is 0.055–0.082/255 and RMSE is 0.425–0.584/255.
- Blender re-export succeeded with SHA-256
  `05bb285ed2e9973b19853e4dc4047e0bb654184e8bf4cee974363b016c0d6496`. It independently reloads at
  1.2 meters with one material and three readable images. Its four rendered views differ from the
  Shepherd candidate by only 0.00028–0.00033/255 MAE.

### Unreal 5.8

- The isolated comparison project and map setup completed with zero errors.
- Raw, Shepherd, and Blender-re-export control arms each imported one static mesh, one material,
  and three textures. Raw bounds represent 99.9089 meters; Shepherd and Blender-control bounds
  represent 1.2 meters and are grounded.
- Raw and Shepherd imports emitted the same non-fatal unsupported `FB_ngon_encoding` warning and
  no import errors.
- Individually framed 1495×549 Unlit screenshots preserve silhouette, material coverage, texture
  color, normal response, opaque behavior, and non-emissive behavior. No anomaly was observed; the
  raw-foreground pixel comparison measured 0.464/255 MAE.
- Unreal's generated LOD0 render counts differ between arms, while the source GLB accessors and
  binary geometry are byte-identical. This is attributed to Unreal import/Nanite build thresholds,
  not a source geometry mutation.

## Artifact tree

```text
shader_lantern_01/
├── checkpoint.md
├── generation-card.md
├── prompt.md
├── provenance.json
├── raw/
│   └── asset.glb
├── blind_asset_shepherd/
│   ├── decisions.json
│   ├── inspection.json
│   ├── job_result.json
│   ├── provenance.json
│   ├── repair_plan.json
│   ├── repaired.glb
│   ├── report.md
│   ├── result.zip
│   └── verification.json
└── observed_real_world/
    ├── adjudication.json
    ├── blender_raw.json
    ├── blender_shepherd.json
    ├── unreal_comparison.json
    ├── unreal_setup.json
    └── screenshots/
        ├── raw/{front,right,back,left}.png
        ├── shepherd/{front,right,back,left}.png
        └── unreal/{raw,shepherd}.png
```

`repaired.glb`, `result.zip`, the `.blend`, Blender re-export, and generated Unreal content remain
reproducible evidence and follow the repository's generated-binary policy. The canonical JSON,
Markdown, and deliberately selected visual evidence are retained with this checkpoint.

## Known limitations

- The source GLB material is explicitly `OPAQUE`, has no emissive texture, and has a zero emissive
  factor. It does contain base-color, metallic/roughness, and normal textures plus
  `KHR_materials_specular`. Asset Shepherd preserved all exported material/texture state, but this
  checkpoint cannot claim that the Tripo preview's apparent glass or glow was exported. That is a
  source-export/corpus limitation, not an observed repair regression.
- Blender re-export split 1,373 additional vertices and warned that multiple image shader nodes can
  map to the first glTF sampler. Counts of triangles/materials/textures, physical result, and visual
  evidence remained stable; this round-trip output is a consumer control, not the delivered file.
- The third Unreal arm is that Blender re-export control, not a human-cleaned reference. Therefore
  this completes the requested isolated Unreal comparison but not the addendum's full three-way RW4
  human-reference gate.
- Manual cleanup time was not measured. Debug Beetle and Cloudforge Workbench are still needed for
  the four-asset RW2 flock.
- `TRIANGLE_BUDGET_EXCEEDED` deliberately remains unresolved. Topology optimization is out of scope.
