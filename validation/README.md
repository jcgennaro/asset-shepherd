# Real-world validation

The [real-world validation plan](../docs/REAL_WORLD_VALIDATION_PLAN.md) controls this evidence layer.
It is intentionally separate from Asset Shepherd product behavior.

The sequence for every untouched asset is:

1. Copy the untouched Tripo GLB to `corpus/<asset_id>/raw/asset.glb` without DCC inspection.
2. Complete the typed provenance record and confirm public-use rights.
3. Register the raw hash with `uv run python -m asset_shepherd.validation.register`.
4. Run and freeze the blind inspect → plan → approve or reject → repair → verify → package artifacts.
5. Only then run Blender and Unreal evidence and complete human adjudication.
6. Derive controlled variants from copies with `asset_shepherd.validation.mutations`.

Regenerate the checked-in schemas with:

```powershell
uv run python -m asset_shepherd.validation.schema_export --output validation/schemas
```

Render a case-study report after adjudication with:

```powershell
uv run python -m asset_shepherd.validation.report `
  --provenance validation/corpus/<asset_id>/provenance.json `
  --adjudication validation/corpus/<asset_id>/observed_real_world/adjudication.json `
  --output validation/corpus/<asset_id>/report.md
```

Raw and generated binary evidence is ignored until rights and repository-size handling are known.
Tracked prompts, schemas, manifests, scripts, and reports keep the process reproducible.
