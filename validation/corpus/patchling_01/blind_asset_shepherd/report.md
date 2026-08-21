# Asset Shepherd Repair Report

- Source: `asset.glb`
- Source SHA-256: `dc2f03ae8ed368f46c2a4ac9e2ebb71f23e980b0c9e6913c685d011e273f418d`
- Repair eligibility: `ELIGIBLE_STATIC_MESH`
- Verification: `PASSED_PROJECT_READY`

## Before and after

- Before dimensions: 0.771484 x 0.998047 x 0.673828 m
- After dimensions: 0.771484 x 0.998047 x 0.673828 m
- After minimum Y: 0 m

## Findings

- `MESH_NAME_INVALID` (ERROR, AUTO_SAFE): Mesh names violate the project pattern
- `NODE_NAME_INVALID` (ERROR, AUTO_SAFE): Node names violate the project pattern

## Decisions and actions

- `rename-mesh-000`: AUTO_AUTHORIZED via POLICY; Rename mesh:0 to Mesh_000 while preserving its index.
- `rename-node-000`: AUTO_AUTHORIZED via POLICY; Rename node:0 to Node_000 while preserving its index.

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
- `EXECUTED_ACTIONS_IN_PROVENANCE`: PASS — Every executed repair action appears exactly in provenance.
- `REJECTIONS_PRESERVED`: PASS — Rejected actions were not executed and remain rejected for this job.
- `SECOND_PLAN_EMPTY`: PASS — A second version-1 planning pass proposes no non-rejected repairs.

## Remaining warnings

- None.
