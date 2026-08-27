"""Deterministic original robot fixture generation."""

# pygltflib is typed internally but does not publish PEP 561 metadata.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

import argparse
import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from struct import pack
from typing import Final, cast

import numpy as np
from pygltflib import (
    ARRAY_BUFFER,
    ELEMENT_ARRAY_BUFFER,
    FLOAT,
    GLTF2,
    SCALAR,
    UNSIGNED_SHORT,
    VEC3,
    Accessor,
    Asset,
    Attributes,
    Buffer,
    BufferView,
    Material,
    Mesh,
    Node,
    PbrMetallicRoughness,
    Primitive,
    Scene,
)

from asset_shepherd.glb import geometry_counts, load_glb, save_glb, world_bounds
from asset_shepherd.models import (
    Bounds3D,
    BudgetPolicy,
    ExpectedHeight,
    FixtureManifest,
    NamingPolicy,
    OrientationPolicy,
    ProjectProfile,
    RepairPolicy,
)

GENERATOR: Final = "Asset Shepherd deterministic fixture generator v1"


@dataclass(frozen=True)
class RobotPart:
    """One baked box primitive in the original robot fixture."""

    name: str
    center: tuple[float, float, float]
    size: tuple[float, float, float]
    material: int


ROBOT_PARTS: Final = (
    RobotPart("LeftFoot", (-0.22, 0.08, 0.02), (0.30, 0.16, 0.40), 2),
    RobotPart("RightFoot", (0.22, 0.08, 0.02), (0.30, 0.16, 0.40), 2),
    RobotPart("LeftLeg", (-0.22, 0.45, 0.0), (0.18, 0.60, 0.18), 0),
    RobotPart("RightLeg", (0.22, 0.45, 0.0), (0.18, 0.60, 0.18), 0),
    RobotPart("Hips", (0.0, 0.78, 0.0), (0.64, 0.18, 0.32), 2),
    RobotPart("Torso", (0.0, 1.12, 0.0), (0.72, 0.55, 0.36), 0),
    RobotPart("ChestPanel", (0.0, 1.13, 0.195), (0.34, 0.28, 0.05), 1),
    RobotPart("LeftArm", (-0.50, 1.11, 0.0), (0.22, 0.58, 0.22), 0),
    RobotPart("RightArm", (0.50, 1.11, 0.0), (0.22, 0.58, 0.22), 0),
    RobotPart("Neck", (0.0, 1.43, 0.0), (0.15, 0.14, 0.15), 2),
    RobotPart("Head", (0.0, 1.58, 0.0), (0.42, 0.30, 0.34), 0),
    RobotPart("LeftEye", (-0.10, 1.61, 0.185), (0.08, 0.08, 0.04), 3),
    RobotPart("RightEye", (0.10, 1.61, 0.185), (0.08, 0.08, 0.04), 3),
    RobotPart("AntennaStem", (0.0, 1.755, 0.0), (0.05, 0.05, 0.05), 2),
    RobotPart("AntennaTip", (0.0, 1.795, 0.0), (0.09, 0.05, 0.09), 1),
)


def fixture_profile() -> ProjectProfile:
    """Return the version-1 profile used by deterministic fixtures."""
    return ProjectProfile(
        profile_id="unreal-indie-robot-v1",
        name="Unreal Indie Robot",
        engine="unreal",
        asset_type="static_mesh",
        expected_height_cm=ExpectedHeight(target=180.0, tolerance=10.0),
        orientation=OrientationPolicy(
            require_y_up_geometry=True,
            infer_vertical_from_dominant_extent=True,
            require_ground_contact=True,
            ground_tolerance_cm=1.0,
        ),
        naming=NamingPolicy(
            pattern=r"^[A-Z][A-Za-z0-9_]*$",
            require_unique_node_names=True,
            require_unique_mesh_names=True,
        ),
        budgets=BudgetPolicy(
            max_triangles=100_000,
            max_materials=8,
            max_textures=16,
            max_texture_dimension=4096,
        ),
        repair_policy=RepairPolicy(
            auto_rename=True,
            require_approval_for_normalization_transform=True,
        ),
    )


def _box_geometry(part: RobotPart) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    center = np.asarray(part.center, dtype=np.float32)
    x, y, z = np.asarray(part.size, dtype=np.float32) / 2.0
    face_data = (
        ((1.0, 0.0, 0.0), ((x, -y, -z), (x, y, -z), (x, y, z), (x, -y, z))),
        ((-1.0, 0.0, 0.0), ((-x, -y, z), (-x, y, z), (-x, y, -z), (-x, -y, -z))),
        ((0.0, 1.0, 0.0), ((-x, y, -z), (-x, y, z), (x, y, z), (x, y, -z))),
        ((0.0, -1.0, 0.0), ((-x, -y, z), (-x, -y, -z), (x, -y, -z), (x, -y, z))),
        ((0.0, 0.0, 1.0), ((-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z))),
        ((0.0, 0.0, -1.0), ((x, -y, -z), (-x, -y, -z), (-x, y, -z), (x, y, -z))),
    )
    positions: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    indices: list[int] = []
    for normal, corners in face_data:
        start = len(positions)
        positions.extend(tuple((np.asarray(corner) + center).tolist()) for corner in corners)
        normals.extend([normal] * 4)
        indices.extend((start, start + 1, start + 2, start, start + 2, start + 3))
    return (
        np.asarray(positions, dtype=np.float32),
        np.asarray(normals, dtype=np.float32),
        np.asarray(indices, dtype=np.uint16),
    )


def _materials() -> list[Material]:
    colors = (
        ("RobotBlue", [0.08, 0.32, 0.72, 1.0], 0.15, 0.55),
        ("RobotOrange", [1.0, 0.34, 0.05, 1.0], 0.05, 0.45),
        ("RobotDark", [0.06, 0.08, 0.12, 1.0], 0.55, 0.35),
        ("RobotGlow", [0.1, 0.9, 1.0, 1.0], 0.0, 0.2),
    )
    return [
        Material(
            name=name,
            pbrMetallicRoughness=PbrMetallicRoughness(
                baseColorFactor=color,
                metallicFactor=metallic,
                roughnessFactor=roughness,
            ),
            emissiveFactor=[0.0, 0.0, 0.0] if name != "RobotGlow" else [0.05, 0.45, 0.5],
        )
        for name, color, metallic, roughness in colors
    ]


def build_robot(*, broken: bool) -> GLTF2:
    """Build the clean robot or its deterministic broken derivative."""
    blob = bytearray()
    views: list[BufferView] = []
    accessors: list[Accessor] = []
    meshes: list[Mesh] = []

    def append_view(data: bytes, *, target: int) -> int:
        while len(blob) % 4:
            blob.append(0)
        offset = len(blob)
        blob.extend(data)
        views.append(BufferView(buffer=0, byteOffset=offset, byteLength=len(data), target=target))
        return len(views) - 1

    for part in ROBOT_PARTS:
        positions, normals, indices = _box_geometry(part)
        position_view = append_view(positions.tobytes(), target=ARRAY_BUFFER)
        normal_view = append_view(normals.tobytes(), target=ARRAY_BUFFER)
        index_view = append_view(indices.tobytes(), target=ELEMENT_ARRAY_BUFFER)
        position_accessor = len(accessors)
        accessors.append(
            Accessor(
                bufferView=position_view,
                componentType=FLOAT,
                count=len(positions),
                type=VEC3,
                min=positions.min(axis=0).tolist(),
                max=positions.max(axis=0).tolist(),
            )
        )
        normal_accessor = len(accessors)
        accessors.append(
            Accessor(
                bufferView=normal_view,
                componentType=FLOAT,
                count=len(normals),
                type=VEC3,
                min=[-1.0, -1.0, -1.0],
                max=[1.0, 1.0, 1.0],
            )
        )
        index_accessor = len(accessors)
        accessors.append(
            Accessor(
                bufferView=index_view,
                componentType=UNSIGNED_SHORT,
                count=len(indices),
                type=SCALAR,
                min=[int(indices.min())],
                max=[int(indices.max())],
            )
        )
        meshes.append(
            Mesh(
                name=f"{part.name}Mesh",
                primitives=[
                    Primitive(
                        attributes=Attributes(POSITION=position_accessor, NORMAL=normal_accessor),
                        indices=index_accessor,
                        material=part.material,
                    )
                ],
            )
        )

    nodes = [Node(name="RobotRoot", children=list(range(1, len(ROBOT_PARTS) + 1)))]
    nodes.extend(Node(name=part.name, mesh=index) for index, part in enumerate(ROBOT_PARTS))
    materials = _materials()
    if broken:
        root_transform = np.eye(4, dtype=np.float64)
        root_transform[:3, :3] = np.asarray(
            [[0.0, 100.0, 0.0], [-100.0, 0.0, 0.0], [0.0, 0.0, 100.0]]
        )
        root_transform[1, 3] = 100.0
        nodes[0].matrix = root_transform.T.reshape(-1).tolist()
        nodes[0].name = "robot root"
        nodes[1].name = "duplicate part"
        nodes[2].name = "duplicate part"
        nodes[3].name = None
        nodes[4].name = "4Leg"
        meshes[0].name = "bad mesh"
        meshes[1].name = "bad mesh"
        meshes[2].name = None
        meshes[3].name = "3InvalidMesh"
        while len(materials) <= fixture_profile().budgets.max_materials:
            index = len(materials)
            materials.append(
                Material(
                    name=f"UnusedWarningMaterial{index:02d}",
                    pbrMetallicRoughness=PbrMetallicRoughness(
                        baseColorFactor=[0.2, 0.2, 0.2, 1.0],
                        metallicFactor=0.0,
                        roughnessFactor=1.0,
                    ),
                )
            )

    gltf = GLTF2(
        asset=Asset(version="2.0", generator=GENERATOR),
        scene=0,
        scenes=[Scene(name="RobotScene", nodes=[0])],
        nodes=nodes,
        meshes=meshes,
        accessors=accessors,
        bufferViews=views,
        buffers=[Buffer(byteLength=len(blob))],
        materials=materials,
    )
    gltf.set_binary_blob(bytes(blob))
    return gltf


def _bounds_model(path: Path) -> Bounds3D:
    bounds = world_bounds(load_glb(path))
    minimum_m = (float(bounds.minimum[0]), float(bounds.minimum[1]), float(bounds.minimum[2]))
    maximum_m = (float(bounds.maximum[0]), float(bounds.maximum[1]), float(bounds.maximum[2]))
    dimensions_m = (
        float(bounds.dimensions[0]),
        float(bounds.dimensions[1]),
        float(bounds.dimensions[2]),
    )
    return Bounds3D(
        minimum_m=minimum_m,
        maximum_m=maximum_m,
        dimensions_m=dimensions_m,
        minimum_cm=(minimum_m[0] * 100.0, minimum_m[1] * 100.0, minimum_m[2] * 100.0),
        maximum_cm=(maximum_m[0] * 100.0, maximum_m[1] * 100.0, maximum_m[2] * 100.0),
        dimensions_cm=(
            dimensions_m[0] * 100.0,
            dimensions_m[1] * 100.0,
            dimensions_m[2] * 100.0,
        ),
    )


def _write_model(path: Path, model: ProjectProfile | FixtureManifest) -> None:
    payload = json.dumps(model.model_dump(mode="json"), indent=2, sort_keys=True)
    path.write_text(f"{payload}\n", encoding="utf-8", newline="\n")


def _write_fixture_manifest(
    glb_path: Path,
    *,
    fixture_id: str,
    defect_codes: tuple[str, ...],
    original_asset: bool,
) -> Path:
    loaded = load_glb(glb_path)
    counts = geometry_counts(loaded)
    manifest = FixtureManifest(
        fixture_id=fixture_id,
        glb_filename=glb_path.name,
        sha256=sha256(glb_path.read_bytes()).hexdigest(),
        expected_bounds_m=_bounds_model(glb_path),
        expected_vertex_count=counts.vertices,
        expected_triangle_count=counts.triangles,
        expected_material_count=len(loaded.materials),
        expected_defect_codes=defect_codes,
        original_asset=original_asset,
    )
    manifest_path = glb_path.with_suffix(".expected.json")
    _write_model(manifest_path, manifest)
    return manifest_path


def generate_geometry_failure_fixtures(clean_path: Path, output_dir: Path) -> tuple[Path, ...]:
    """Create parseable GLBs that exercise objective geometry failure handling."""
    output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []

    degenerate_path = output_dir / "degenerate_triangle.glb"
    degenerate = load_glb(clean_path)
    index_accessor_index = degenerate.meshes[0].primitives[0].indices
    if index_accessor_index is None:
        msg = "The clean fixture must have indexed geometry."
        raise ValueError(msg)
    index_accessor = degenerate.accessors[index_accessor_index]
    if index_accessor.bufferView is None or index_accessor.componentType != UNSIGNED_SHORT:
        msg = "The clean fixture must use an unsigned-short index buffer."
        raise ValueError(msg)
    index_view = degenerate.bufferViews[index_accessor.bufferView]
    index_offset = (index_view.byteOffset or 0) + (index_accessor.byteOffset or 0)
    blob = bytearray(degenerate.binary_blob() or b"")
    blob[index_offset : index_offset + 12] = pack("<HHHHHH", 0, 0, 2, 1, 2, 3)
    degenerate.set_binary_blob(bytes(blob))
    save_glb(degenerate, degenerate_path)
    degenerate_manifest = _write_fixture_manifest(
        degenerate_path,
        fixture_id="degenerate_triangle",
        defect_codes=("DEGENERATE_TRIANGLES_DETECTED", "UNUSED_VERTEX_DATA_DETECTED"),
        original_asset=False,
    )
    generated.extend((degenerate_path, degenerate_manifest))

    malformed_path = output_dir / "malformed_attributes.glb"
    malformed = load_glb(clean_path)
    normal_accessor_index = cast(int | None, malformed.meshes[0].primitives[0].attributes.NORMAL)
    if normal_accessor_index is None:
        msg = "The clean fixture must have a normal attribute."
        raise ValueError(msg)
    malformed.accessors[normal_accessor_index].count -= 1
    save_glb(malformed, malformed_path)
    malformed_manifest = _write_fixture_manifest(
        malformed_path,
        fixture_id="malformed_attributes",
        defect_codes=(
            "ATTRIBUTE_SAFE_DUPLICATE_TUPLES_DETECTED",
            "MALFORMED_GEOMETRY_ATTRIBUTES",
        ),
        original_asset=False,
    )
    generated.extend((malformed_path, malformed_manifest))
    return tuple(generated)


def generate_fixtures(output_dir: Path, profile_dir: Path) -> tuple[Path, ...]:
    """Regenerate all version-1 fixture artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    profile_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    profile_path = profile_dir / "unreal_indie_robot.json"
    _write_model(profile_path, fixture_profile())
    generated.append(profile_path)

    for fixture_id, broken in (("clean_robot", False), ("broken_robot", True)):
        glb_path = output_dir / f"{fixture_id}.glb"
        save_glb(build_robot(broken=broken), glb_path)
        defect_codes = (
            (
                "HEIGHT_OUT_OF_RANGE",
                "ORIENTATION_NOT_Y_UP",
                "NOT_GROUNDED",
                "NODE_NAME_INVALID",
                "NODE_NAME_MISSING",
                "NODE_NAME_DUPLICATE",
                "MESH_NAME_INVALID",
                "MESH_NAME_MISSING",
                "MESH_NAME_DUPLICATE",
                "MATERIAL_BUDGET_EXCEEDED",
            )
            if broken
            else ()
        )
        manifest_path = _write_fixture_manifest(
            glb_path,
            fixture_id=fixture_id,
            defect_codes=defect_codes,
            original_asset=True,
        )
        generated.extend((glb_path, manifest_path))
    return tuple(generated)


def main() -> None:
    """Generate fixture GLBs, manifests, and the fixture project profile."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("fixtures"))
    parser.add_argument("--profiles", type=Path, default=Path("profiles"))
    args = parser.parse_args()
    generate_fixtures(args.output, args.profiles)


if __name__ == "__main__":
    main()
