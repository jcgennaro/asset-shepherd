# Deterministic-core checkpoint

**Date:** 2026-08-21

**Scope:** M6 deterministic inspect → plan → approve/reject → repair → verify → package

**Reviewed baseline:** `b129fdce8548a8a0569af693305c83be39c1541f`

This checkpoint adds no product scope. It exercises the rejected approval path, a compliant
control asset, the contracted package, and an independent Blender import. Generated evidence is
written below `build/checkpoints/deterministic-core/`, which is ignored by Git.

## Exact commands

Run from the repository root in PowerShell with the locked `uv` environment.

```powershell
uv run asset-shepherd run fixtures/broken_robot.glb --profile profiles/unreal_indie_robot.json --approvals examples/reject_normalization.json --output build/checkpoints/deterministic-core/rejected

uv run asset-shepherd run fixtures/clean_robot.glb --profile profiles/unreal_indie_robot.json --approvals examples/approve_none.json --output build/checkpoints/deterministic-core/clean-control-fixed

uv run asset-shepherd run fixtures/broken_robot.glb --profile profiles/unreal_indie_robot.json --approvals examples/approve_normalization.json --output build/checkpoints/deterministic-core/approved-audit

uv run pytest tests/test_workflow.py -q

uv run python -c "import json; from pathlib import Path; from zipfile import ZipFile; from jsonschema.validators import validator_for; root=Path('build/checkpoints/deterministic-core/approved-audit'); expected={'repaired.glb','inspection.json','repair_plan.json','decisions.json','verification.json','provenance.json','report.md'}; mapping={'inspection.json':'inspection.schema.json','repair_plan.json':'repair_plan.schema.json','decisions.json':'decisions.schema.json','verification.json':'verification.schema.json','provenance.json':'provenance.schema.json'}; [(lambda data,schema:(validator_for(schema).check_schema(schema),validator_for(schema)(schema).validate(data)))(json.loads((root/name).read_text()),json.loads((Path('schemas')/schema_name).read_text())) for name,schema_name in mapping.items()]; report=(root/'report.md').read_text(); assert all(section in report for section in ('## Before and after','## Findings','## Decisions and actions','## Verification checks','## Remaining warnings')); archive=ZipFile(root/'result.zip'); assert set(archive.namelist())==expected; assert all(archive.read(name)==(root/name).read_bytes() for name in expected); print('validated_artifacts=',sorted(expected)); print('zip_members=',archive.namelist()); print('artifact_bytes=',{name:(root/name).stat().st_size for name in sorted(expected)})"

$asset = (Resolve-Path 'build/checkpoints/deterministic-core/approved-audit/repaired.glb').Path
$blender = 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
& $blender --background --factory-startup --python-expr "import bpy; path=r'''$asset'''; result=bpy.ops.import_scene.gltf(filepath=path); meshes=[obj for obj in bpy.context.scene.objects if obj.type=='MESH']; assert result=={'FINISHED'}; assert meshes; print('ASSET_SHEPHERD_BLENDER_IMPORT', {'result': sorted(result), 'objects': len(bpy.context.scene.objects), 'meshes': len(meshes), 'vertices': sum(len(obj.data.vertices) for obj in meshes), 'polygons': sum(len(obj.data.polygons) for obj in meshes)})"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

The output directories must not already exist because the workflow deliberately refuses to mix
or overwrite job artifacts.

## Tested cases

### Rejected approval

- Input: `fixtures/broken_robot.glb`.
- Approval decision: `normalize-root-v1` set to `false`.
- The nine `AUTO_SAFE` naming actions executed; `normalize-root-v1` did not.
- `decisions.json` records `normalize-root-v1` as `REJECTED` from
  `USER_APPROVAL_FILE`.
- `provenance.json` excludes the normalization from `executed_actions` and preserves the rejection
  in its decision records.
- Verification checks `REJECTED_NORMALIZATION_NOT_APPLIED` and `REJECTIONS_PRESERVED` both pass.
- The unresolved `HEIGHT_OUT_OF_RANGE`, `ORIENTATION_NOT_Y_UP`, and `NOT_GROUNDED` findings remain
  explicit, along with the intentionally report-only `MATERIAL_BUDGET_EXCEEDED` warning.
- Final state: `PASSED_WITH_REMAINING_WARNINGS`.

### Clean control

- Input: the already compliant `fixtures/clean_robot.glb`.
- Inspection returned no findings, the plan returned no candidates, and the decision and executed
  action lists were empty.
- Final state: `PASSED_PROJECT_READY`; every verification check passed.
- Source and packaged `repaired.glb` are byte-identical, both with SHA-256
  `379fd969d04cd996d927e7ebe45d2b031808b2170d61fb21a2ea8885c666d75b`.
- The checkpoint exposed and fixed an unnecessary GLB reserialization. A no-action job now copies
  source bytes exactly while still packaging the required `repaired.glb` candidate.

### Approved package and real-consumer import

- All five contracted JSON artifacts validate against their checked-in JSON schemas.
- `report.md` is non-empty and contains every contracted report section.
- The result ZIP contains exactly the seven contracted files, and every member is byte-identical
  to the corresponding on-disk artifact.
- Blender 5.1.2 imported `repaired.glb` with result `FINISHED` in factory-startup/background mode.
  Blender created 20 scene objects, including 16 mesh objects with 368 vertices and 186 polygons.
- The approved deterministic verification remains `PASSED_WITH_REMAINING_WARNINGS` because the
  material-budget finding is report-only.

## Artifact tree

Each run directory also contains `job_result.json` and `result.zip`; the ZIP itself contains only
the seven contracted artifacts.

```text
build/checkpoints/deterministic-core/
├── rejected/
│   ├── decisions.json
│   ├── inspection.json
│   ├── job_result.json
│   ├── provenance.json
│   ├── repair_plan.json
│   ├── repaired.glb
│   ├── report.md
│   ├── result.zip
│   └── verification.json
├── clean-control-fixed/
│   └── (same nine job files)
└── approved-audit/
    ├── decisions.json
    ├── inspection.json
    ├── job_result.json
    ├── provenance.json
    ├── repair_plan.json
    ├── repaired.glb
    ├── report.md
    ├── result.zip
    │   ├── decisions.json
    │   ├── inspection.json
    │   ├── provenance.json
    │   ├── repair_plan.json
    │   ├── repaired.glb
    │   ├── report.md
    │   └── verification.json
    └── verification.json
```

Approved-audit artifact sizes were:

| Artifact | Bytes | Validation |
|---|---:|---|
| `repaired.glb` | 24,548 | Deterministic reload/validation, Trimesh bounds check, Blender 5.1.2 import |
| `inspection.json` | 14,354 | `inspection.schema.json` |
| `repair_plan.json` | 8,035 | `repair_plan.schema.json` |
| `decisions.json` | 2,043 | `decisions.schema.json` |
| `verification.json` | 5,041 | `verification.schema.json` |
| `provenance.json` | 4,769 | `provenance.schema.json` |
| `report.md` | 3,837 | Required sections present and ZIP byte comparison |

## Results

All three cases completed with the expected state. The targeted workflow suite passed with six
tests. The rejection stayed rejected, the clean control remained byte-identical, every contracted
artifact validated, ZIP membership was exact, and Blender independently consumed the approved
asset.

## Known limitations

- Blender acceptance covers the deterministic approved robot fixture, not arbitrary third-party
  GLBs or every glTF extension.
- Runtime structural validation still includes `pygltflib`'s partial/provisional validator rather
  than the official Khronos validator; the independent Trimesh and Blender reloads reduce but do
  not eliminate that limitation.
- The rejected run intentionally still applies `AUTO_SAFE` naming repairs. It preserves the
  rejected scale/orientation/grounding decision and does not silently normalize geometry.
- The broken fixture intentionally remains over the profile's material budget because material
  merging is outside the MVP repair contract.
