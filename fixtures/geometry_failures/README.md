# Geometry failure fixtures

These GLBs have valid containers and can be uploaded into the full Asset Shepherd workflow.
Describe either one as a 1.82 m upright static robot prop so target-specific scale and pose findings do not obscure the intended geometry test.

- `degenerate_triangle.glb` contains one triangle with a repeated vertex index. Asset Shepherd should report the degenerate face and its resulting unused vertex data, leave the geometry unchanged, and allow the otherwise eligible asset to continue.
- `malformed_attributes.glb` declares one fewer normal than positions in its first primitive. Asset Shepherd may still report measurable duplicate tuples, but `MALFORMED_GEOMETRY_ATTRIBUTES` must block repair because it cannot prove that the vertex attributes are valid.

The adjacent manifests record the expected finding code and SHA-256 hash. Regenerate all four artifacts with:

```powershell
uv run python scripts/generate_geometry_failure_fixtures.py
```
