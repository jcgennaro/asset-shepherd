# Asset Shepherd Repair Report

- Source: `asset.glb`
- Source SHA-256: `be2c9cab8d4e51f7a948c7c54db7a10c932f24faf69bc3166ff724ccc00c49b9`
- Repair eligibility: `ELIGIBLE_STATIC_MESH`
- Verification: `PASSED_WITH_REMAINING_WARNINGS`

## Before and after

- Before dimensions: 55.9881 x 99.9089 x 57.9442 m
- After dimensions: 0.67247 x 1.2 x 0.695965 m
- After minimum Y: 0 m

## Findings

- `HEIGHT_OUT_OF_RANGE` (ERROR, APPROVAL_REQUIRED): Physical size is outside the project tolerance
- `MESH_NAME_INVALID` (ERROR, AUTO_SAFE): Mesh names violate the project pattern
- `NODE_NAME_INVALID` (ERROR, AUTO_SAFE): Node names violate the project pattern
- `TRIANGLE_BUDGET_EXCEEDED` (WARNING, REPORT_ONLY): Triangle budget exceeded

## Decisions and actions

- `rename-mesh-000`: AUTO_AUTHORIZED via POLICY; Rename mesh:0 to Mesh_000 while preserving its index.
- `rename-node-001`: AUTO_AUTHORIZED via POLICY; Rename node:1 to Node_001 while preserving its index.
- `normalize-root-v1`: APPROVED via USER_APPROVAL_FILE; Apply one reversible root normalization transform.

## Verification checks

- `SOURCE_UNCHANGED`: PASS — The original source hash is unchanged and matches the plan.
- `OUTPUT_HASH_RECORDED`: PASS — The candidate hash matches repair outcome and provenance.
- `GLTF_VALIDATION`: PASS — The saved output parses as GLB 2.0 and passes selected structural validation.
- `INDEPENDENT_REINSPECTION`: PASS — A fresh disk reload produced a complete deterministic inspection.
- `VERTEX_COUNT_PRESERVED`: PASS — Vertex Count Preserved
- `TRIANGLE_COUNT_PRESERVED`: PASS — Triangle Count Preserved
- `MATERIAL_COUNT_PRESERVED`: PASS — Material Count Preserved
- `TEXTURE_COUNT_PRESERVED`: PASS — Texture Count Preserved
- `NAMES_VALID_AND_UNIQUE`: PASS — All node and mesh names satisfy the profile and uniqueness rules.
- `INDEPENDENT_GEOMETRY_RELOAD`: PASS — Trimesh independently reloads the GLB and agrees on world bounds.
- `APPROVED_SCALE_WITHIN_TOLERANCE`: PASS — Approved physical scale is within the project height tolerance.
- `EXECUTED_ACTIONS_IN_PROVENANCE`: PASS — Every executed repair action appears exactly in provenance.
- `REJECTIONS_PRESERVED`: PASS — Rejected actions were not executed and remain rejected for this job.
- `SECOND_PLAN_EMPTY`: PASS — A second version-1 planning pass proposes no non-rejected repairs.

## Remaining warnings

- TRIANGLE_BUDGET_EXCEEDED: Triangle budget exceeded
