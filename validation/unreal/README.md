# Unreal validation

This directory is an isolated, content-only Unreal 5.8 validation project. It never touches the
user's production game project and does not turn Asset Shepherd into an Unreal plugin.

Create or refresh the fixed comparison map:

```powershell
& 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' `
  validation/unreal/AssetShepherdValidation.uproject -unattended -nosplash -nullrhi `
  -run=pythonscript `
  -script="validation/unreal/setup_validation_project.py --output build/validation/unreal-setup.json"
```

After all three comparable GLBs exist, use `import_compare.py` through the same commandlet and pass
`--raw`, `--shepherd`, `--human-reference`, `--run-id`, and `--output`. Each run gets isolated content
destinations. The script applies equivalent automated import settings, places the first imported
static mesh on fixed pedestals, and records object paths, bounds, material slots, textures, available
mesh counts, and the commandlet-log location.

Open `AssetShepherdValidation.uproject` for the visual pass. Use the fixed comparison camera, capture
raw, Shepherd, and human-reference screenshots at the same resolution, and record warnings, missing
materials, normals, shading, UVs, ground contact, pivot behavior, and remaining manual minutes in the
asset adjudication record. Generated Unreal content and caches are intentionally ignored because the
checked-in scripts recreate them.
