"""Independent controlled mutations for realistic GLB validation copies."""

# pygltflib does not publish PEP 561 metadata.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

import argparse
import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import numpy as np
from numpy.typing import NDArray
from pygltflib import GLTF2, Material, Node, Scene

from asset_shepherd.glb import geometry_counts, load_glb, validate_loaded_glb
from asset_shepherd.models import ActionClass
from asset_shepherd.validation.models import (
    MutationKind,
    MutationManifest,
    MutationOperation,
)
from asset_shepherd.validation.register import hash_file

_TOOL_VERSION = "asset-shepherd-validation-mutations-v1"


class MutationError(ValueError):
    """Raised when a controlled variant cannot preserve its stated invariants."""


def _matrix_list(matrix: NDArray[np.float64]) -> list[float]:
    return [float(value) for value in matrix.T.reshape(-1)]


def _active_root_nodes(gltf: GLTF2) -> tuple[Scene, list[int]]:
    scenes = gltf.scenes
    if not scenes:
        raise MutationError("GLB has no scene to mutate")
    scene_index = cast(int | None, gltf.scene)
    scene = scenes[scene_index if scene_index is not None else 0]
    roots = list(scene.nodes or [])
    if not roots:
        raise MutationError("Active scene has no root nodes")
    return scene, roots


def _normalization_chaos(gltf: GLTF2) -> tuple[MutationOperation, ...]:
    scene, roots = _active_root_nodes(gltf)
    nodes = gltf.nodes
    meshes = gltf.meshes
    scale = np.diag([100.0, 100.0, 100.0, 1.0])
    rotation = np.asarray(
        [
            [0.0, -1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    translation = np.eye(4, dtype=np.float64)
    translation[1, 3] = 100.0
    matrix = translation @ rotation @ scale
    wrapper_index = len(nodes)
    nodes.append(
        Node(
            name="validation chaos",
            matrix=_matrix_list(matrix),
            children=roots,
        )
    )
    scene.nodes = [wrapper_index]

    expected_name_codes = {"NODE_NAME_INVALID"}
    affected_names = [f"node:{wrapper_index}"]
    if len(nodes) >= 3:
        nodes[0].name = "duplicate part"
        nodes[1].name = "duplicate part"
        nodes[2].name = None
        expected_name_codes.update({"NODE_NAME_DUPLICATE", "NODE_NAME_MISSING"})
        affected_names.extend(("node:0", "node:1", "node:2"))
    if len(meshes) >= 3:
        meshes[0].name = "bad mesh"
        meshes[1].name = "bad mesh"
        meshes[2].name = None
        expected_name_codes.update(
            {"MESH_NAME_INVALID", "MESH_NAME_DUPLICATE", "MESH_NAME_MISSING"}
        )
        affected_names.extend(("mesh:0", "mesh:1", "mesh:2"))
    return (
        MutationOperation(
            kind=MutationKind.SCALE_MISMATCH,
            description="Multiply represented size by 100 through a new root transform.",
            parameters={"uniform_scale": 100.0},
            affected_elements=(f"node:{wrapper_index}",),
            expected_finding_codes=("HEIGHT_OUT_OF_RANGE",),
            expected_action_classes=(ActionClass.APPROVAL_REQUIRED,),
        ),
        MutationOperation(
            kind=MutationKind.SIDEWAYS_ORIENTATION,
            description="Rotate the source roots 90 degrees around positive Z.",
            parameters={"rotation_degrees_z": 90.0},
            affected_elements=(f"node:{wrapper_index}",),
            expected_finding_codes=("ORIENTATION_NOT_Y_UP",),
            expected_action_classes=(ActionClass.APPROVAL_REQUIRED,),
        ),
        MutationOperation(
            kind=MutationKind.FLOATING_GEOMETRY,
            description="Translate the transformed asset above the Y=0 ground plane.",
            parameters={"translation_m": [0.0, 100.0, 0.0]},
            affected_elements=(f"node:{wrapper_index}",),
            expected_finding_codes=("NOT_GROUNDED",),
            expected_action_classes=(ActionClass.APPROVAL_REQUIRED,),
        ),
        MutationOperation(
            kind=MutationKind.NAME_CORRUPTION,
            description="Create missing, duplicate, and invalid display names where available.",
            parameters={},
            affected_elements=tuple(affected_names),
            expected_finding_codes=tuple(sorted(expected_name_codes)),
            expected_action_classes=(ActionClass.AUTO_SAFE,),
        ),
    )


def _hierarchy_trap(gltf: GLTF2) -> tuple[MutationOperation, ...]:
    scene, roots = _active_root_nodes(gltf)
    nodes = gltf.nodes
    empty_leaf_index = len(nodes)
    nodes.append(Node(name="ValidationEmptyLeaf"))
    nested_index = len(nodes)
    nodes.append(
        Node(
            name="ValidationNestedParent",
            translation=[0.25, 0.0, 0.0],
            children=[*roots, empty_leaf_index],
        )
    )
    negative_index = len(nodes)
    nodes.append(
        Node(
            name="ValidationNegativeBranch",
            scale=[-1.0, 1.0, 1.0],
        )
    )
    scene.nodes = [nested_index, negative_index]
    return (
        MutationOperation(
            kind=MutationKind.PIVOT_DISPLACEMENT,
            description="Offset the original hierarchy laterally under a nested parent.",
            parameters={"translation_m": [0.25, 0.0, 0.0]},
            affected_elements=(f"node:{nested_index}",),
            expected_finding_codes=(),
            expected_action_classes=(ActionClass.REPORT_ONLY,),
        ),
        MutationOperation(
            kind=MutationKind.EMPTY_HIERARCHY,
            description="Add a named empty leaf below the nested parent.",
            parameters={},
            affected_elements=(f"node:{empty_leaf_index}", f"node:{nested_index}"),
            expected_finding_codes=(),
            expected_action_classes=(ActionClass.REPORT_ONLY,),
        ),
        MutationOperation(
            kind=MutationKind.NEGATIVE_SCALE,
            description="Add an isolated negative-scale branch without altering visible geometry.",
            parameters={"scale": [-1.0, 1.0, 1.0]},
            affected_elements=(f"node:{negative_index}",),
            expected_finding_codes=("NEGATIVE_DETERMINANT_TRANSFORM",),
            expected_action_classes=(ActionClass.REPORT_ONLY,),
        ),
    )


def _material_texture_bloat(
    gltf: GLTF2,
    *,
    material_target: int,
    texture_target: int,
) -> tuple[MutationOperation, ...]:
    materials = gltf.materials
    textures = gltf.textures
    original_material_count = len(materials)
    original_texture_count = len(textures)
    material_target = max(material_target, original_material_count + 1)
    texture_target = max(texture_target, original_texture_count + 1)
    if not materials:
        materials.append(Material(name="ValidationUnusedMaterial"))
    while len(materials) < material_target:
        duplicate = copy.deepcopy(materials[0])
        duplicate.name = f"ValidationUnusedMaterial_{len(materials):02d}"
        materials.append(duplicate)
    if not textures:
        raise MutationError("material_texture_bloat requires a source with an embedded texture")
    while len(textures) < texture_target:
        textures.append(copy.deepcopy(textures[0]))
    return (
        MutationOperation(
            kind=MutationKind.MATERIAL_BLOAT,
            description="Add provably unused material records beyond the project budget.",
            parameters={
                "source_material_count": original_material_count,
                "target_material_count": material_target,
            },
            affected_elements=tuple(
                f"material:{index}" for index in range(original_material_count, material_target)
            ),
            expected_finding_codes=("MATERIAL_BUDGET_EXCEEDED",),
            expected_action_classes=(ActionClass.REPORT_ONLY,),
        ),
        MutationOperation(
            kind=MutationKind.TEXTURE_BLOAT,
            description="Duplicate texture records while preserving their embedded image source.",
            parameters={
                "source_texture_count": original_texture_count,
                "target_texture_count": texture_target,
            },
            affected_elements=tuple(
                f"texture:{index}" for index in range(original_texture_count, texture_target)
            ),
            expected_finding_codes=("TEXTURE_BUDGET_EXCEEDED",),
            expected_action_classes=(ActionClass.REPORT_ONLY,),
        ),
    )


def create_controlled_variant(
    source: Path,
    output: Path,
    manifest_path: Path,
    *,
    base_asset_id: str,
    variant: str,
    created_at: datetime | None = None,
    material_target: int = 9,
    texture_target: int = 17,
) -> MutationManifest:
    """Mutate a copy, validate it, and emit exact machine-readable ground truth."""
    source = source.resolve(strict=True)
    output = output.resolve(strict=False)
    manifest_path = manifest_path.resolve(strict=False)
    if source == output:
        raise MutationError("Controlled mutation must not overwrite its source")
    if output.exists() or manifest_path.exists():
        raise MutationError("Controlled mutation outputs must not already exist")
    source_hash = hash_file(source)
    source_gltf = load_glb(source)
    source_counts = geometry_counts(source_gltf)
    source_materials = len(source_gltf.materials)
    source_textures = len(source_gltf.textures)
    mutated = load_glb(source)
    if variant == "normalization_chaos":
        operations = _normalization_chaos(mutated)
    elif variant == "hierarchy_trap":
        operations = _hierarchy_trap(mutated)
    elif variant == "material_texture_bloat":
        operations = _material_texture_bloat(
            mutated,
            material_target=material_target,
            texture_target=texture_target,
        )
    else:
        raise MutationError(f"Unknown controlled variant: {variant}")
    output.parent.mkdir(parents=True, exist_ok=True)
    if not mutated.save_binary(str(output)):
        raise MutationError("pygltflib could not save the controlled variant")
    variant_gltf = load_glb(output)
    validate_loaded_glb(variant_gltf)
    variant_counts = geometry_counts(variant_gltf)
    geometry_preserved = variant_counts == source_counts
    if not geometry_preserved:
        raise MutationError("Controlled mutation unexpectedly changed geometry counts")
    source_unchanged = hash_file(source) == source_hash
    if not source_unchanged:
        raise MutationError("Controlled mutation changed its source")
    materials_preserved = len(variant_gltf.materials) >= source_materials
    textures_preserved = len(variant_gltf.textures) >= source_textures
    manifest = MutationManifest(
        mutation_id=f"{base_asset_id}_{variant}",
        base_asset_id=base_asset_id,
        source_sha256=source_hash,
        variant_sha256=hash_file(output),
        created_at=created_at or datetime.now(UTC),
        tool_version=_TOOL_VERSION,
        operations=operations,
        expected_post_repair_invariants=(
            "source_sha256_unchanged",
            "vertex_count_preserved",
            "triangle_count_preserved",
            "original_materials_preserved",
            "original_textures_preserved",
        ),
        source_unchanged_verified=source_unchanged,
        variant_parse_verified=True,
        geometry_preserved=geometry_preserved,
        materials_preserved=materials_preserved,
        textures_preserved=textures_preserved,
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        f"{json.dumps(manifest.model_dump(mode='json'), indent=2, sort_keys=True)}\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def main() -> None:
    """Generate one controlled realistic variant from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "variant",
        choices=("normalization_chaos", "hierarchy_trap", "material_texture_bloat"),
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--base-asset-id", required=True)
    args = parser.parse_args()
    manifest = create_controlled_variant(
        args.source,
        args.output,
        args.manifest,
        base_asset_id=args.base_asset_id,
        variant=args.variant,
    )
    print(json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
