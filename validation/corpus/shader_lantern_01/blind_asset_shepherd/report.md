# Asset Shepherd Inspection

- Source: `asset.glb`
- SHA-256: `be2c9cab8d4e51f7a948c7c54db7a10c932f24faf69bc3166ff724ccc00c49b9`
- Repair eligibility: `ELIGIBLE_STATIC_MESH`
- Dimensions: 55.9881 x 99.9089 x 57.9442 meters
- Geometry: 77545 vertices, 101564 triangles

## Findings

| Severity | Code | Finding | Action |
|---|---|---|---|
| ERROR | `HEIGHT_OUT_OF_RANGE` | Physical size is outside the project tolerance | APPROVAL_REQUIRED |
| ERROR | `MESH_NAME_INVALID` | Mesh names violate the project pattern | AUTO_SAFE |
| ERROR | `NODE_NAME_INVALID` | Node names violate the project pattern | AUTO_SAFE |
| WARNING | `TRIANGLE_BUDGET_EXCEEDED` | Triangle budget exceeded | REPORT_ONLY |
