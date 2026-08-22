# Unreal validation

This directory is an isolated, content-only Unreal 5.8 validation project. It never touches the
user's production game project and does not turn Asset Shepherd into an Unreal plugin.

Create or refresh the fixed comparison map:

```powershell
$unreal = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$root = (Resolve-Path '.').Path.Replace('\','/')
$project = "$root/validation/unreal/AssetShepherdValidation.uproject"

& $unreal $project -unattended -nop4 -nosplash -nullrhi -stdout `
  -FullStdOutLogOutput -NoSourceControl -run=pythonscript `
  "-script=$root/validation/unreal/setup_validation_project.py --output $root/build/validation/unreal-setup.json"
```

After all three comparable GLBs exist, use `import_compare.py` through the same commandlet and pass
`--raw`, `--shepherd`, `--human-reference`, `--run-id`, and `--output`. Each run gets isolated content
destinations. The script applies equivalent automated import settings, places the first imported
static mesh on fixed pedestals, and records object paths, bounds, material slots, textures, available
mesh counts, and the commandlet-log location. Paths forwarded inside `-script` should be absolute;
otherwise the commandlet can resolve them relative to the engine binary directory. When the third
arm is a diagnostic control rather than a human-cleaned asset, pass an explicit
`--human-reference-role` label so the evidence cannot overstate the RW4 gate.

The checked-in project config uses DX12/SM6 because Unreal 5.8 can import these GLBs as Nanite
assets, which cannot render in the validation viewport under SM5. The config intentionally contains
no generated Android file-server token.

Open `AssetShepherdValidation.uproject` for the visual pass. Use the fixed comparison camera, capture
raw, Shepherd, and human-reference screenshots at the same resolution, and record warnings, missing
materials, normals, shading, UVs, ground contact, pivot behavior, and remaining manual minutes in the
asset adjudication record. Generated Unreal content and caches are intentionally ignored because the
checked-in scripts recreate them.
