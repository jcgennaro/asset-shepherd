# Blender validation

Blender is an independent local consumer and evidence extractor, not a hosted product dependency.
Background scripts in this directory must import copies or derived outputs, record the Blender
version and metrics, and never rewrite the raw corpus export.

`inspect_glb.py` performs a fresh background import, records structural evidence, checks that the
source hash remains unchanged, and can optionally save a `.blend` and re-export a GLB.

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background `
  --python validation/blender/inspect_glb.py -- `
  --asset validation/corpus/patchling_01/raw/asset.glb `
  --output validation/corpus/patchling_01/observed_real_world/blender_raw.json
```

Visual anomalies still require human adjudication. The script does not silently clean or modify the
imported asset.
