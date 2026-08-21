# Asset Shepherd Inspection

- Source: `asset.glb`
- SHA-256: `dc2f03ae8ed368f46c2a4ac9e2ebb71f23e980b0c9e6913c685d011e273f418d`
- Repair eligibility: `ELIGIBLE_STATIC_MESH`
- Dimensions: 0.771484 x 0.998047 x 0.673828 meters
- Geometry: 26135 vertices, 18727 triangles

## Findings

| Severity | Code | Finding | Action |
|---|---|---|---|
| ERROR | `HEIGHT_OUT_OF_RANGE` | Physical size is outside the project tolerance | APPROVAL_REQUIRED |
| ERROR | `MESH_NAME_INVALID` | Mesh names violate the project pattern | AUTO_SAFE |
| ERROR | `NODE_NAME_INVALID` | Node names violate the project pattern | AUTO_SAFE |
