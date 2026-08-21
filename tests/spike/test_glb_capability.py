"""M2 proof that the selected GLB stack can round-trip required content."""

# pygltflib and parts of Trimesh do not publish complete PEP 561 metadata.
# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from io import BytesIO
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image as PillowImage
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
    Image,
    Material,
    Mesh,
    Node,
    PbrMetallicRoughness,
    Primitive,
    Scene,
    Texture,
    TextureInfo,
)

from asset_shepherd.glb import (
    add_normalization_root,
    geometry_counts,
    load_glb,
    save_glb,
    validate_loaded_glb,
    world_bounds,
)


def _pad_four(data: bytes) -> bytes:
    return data + b"\x00" * (-len(data) % 4)


def _make_spike_glb(path: Path) -> None:
    positions = np.asarray(
        [
            [-0.5, 0.0, -0.5],
            [0.5, 0.0, -0.5],
            [0.5, 1.0, -0.5],
            [-0.5, 1.0, -0.5],
            [-0.5, 0.0, 0.5],
            [0.5, 0.0, 0.5],
            [0.5, 1.0, 0.5],
            [-0.5, 1.0, 0.5],
        ],
        dtype=np.float32,
    )
    indices = np.asarray(
        [
            0,
            2,
            1,
            0,
            3,
            2,
            4,
            5,
            6,
            4,
            6,
            7,
            0,
            1,
            5,
            0,
            5,
            4,
            2,
            3,
            7,
            2,
            7,
            6,
            1,
            2,
            6,
            1,
            6,
            5,
            3,
            0,
            4,
            3,
            4,
            7,
        ],
        dtype=np.uint16,
    )
    png = BytesIO()
    PillowImage.new("RGBA", (2, 2), color=(80, 140, 220, 255)).save(png, format="PNG")
    index_bytes = _pad_four(indices.tobytes())
    position_bytes = _pad_four(positions.tobytes())
    image_bytes = png.getvalue()
    image_offset = len(index_bytes) + len(position_bytes)
    blob = index_bytes + position_bytes + _pad_four(image_bytes)

    gltf = GLTF2(
        asset=Asset(version="2.0", generator="Asset Shepherd M2 spike"),
        scene=0,
        scenes=[Scene(name="SpikeScene", nodes=[0])],
        nodes=[Node(name="OriginalRoot", mesh=0, extras={"sentinel": "preserve"})],
        meshes=[
            Mesh(
                name="SpikeMesh",
                primitives=[Primitive(attributes=Attributes(POSITION=1), indices=0, material=0)],
            )
        ],
        accessors=[
            Accessor(
                bufferView=0,
                componentType=UNSIGNED_SHORT,
                count=len(indices),
                type=SCALAR,
                min=[0],
                max=[7],
            ),
            Accessor(
                bufferView=1,
                componentType=FLOAT,
                count=len(positions),
                type=VEC3,
                min=positions.min(axis=0).tolist(),
                max=positions.max(axis=0).tolist(),
            ),
        ],
        bufferViews=[
            BufferView(
                buffer=0,
                byteOffset=0,
                byteLength=indices.nbytes,
                target=ELEMENT_ARRAY_BUFFER,
            ),
            BufferView(
                buffer=0,
                byteOffset=len(index_bytes),
                byteLength=positions.nbytes,
                target=ARRAY_BUFFER,
            ),
            BufferView(
                buffer=0,
                byteOffset=image_offset,
                byteLength=len(image_bytes),
            ),
        ],
        buffers=[Buffer(byteLength=len(blob))],
        images=[Image(name="EmbeddedPixel", bufferView=2, mimeType="image/png")],
        textures=[Texture(name="EmbeddedTexture", source=0)],
        materials=[
            Material(
                name="TexturedMaterial",
                pbrMetallicRoughness=PbrMetallicRoughness(
                    baseColorTexture=TextureInfo(index=0),
                    metallicFactor=0.0,
                    roughnessFactor=0.8,
                ),
            )
        ],
        extensions={"VENDOR_asset_shepherd_spike": {"sentinel": 42}},
        extensionsUsed=["VENDOR_asset_shepherd_spike"],
    )
    gltf.set_binary_blob(blob)
    gltf.save_binary(str(path))


def test_glb_round_trip_preserves_content_and_applies_root_transform(tmp_path: Path) -> None:
    """Rename and transform a GLB, then independently reload and measure it."""
    source = tmp_path / "source.glb"
    output = tmp_path / "output.glb"
    _make_spike_glb(source)

    gltf = load_glb(source)
    validate_loaded_glb(gltf)
    assert geometry_counts(gltf).vertices == 8
    assert geometry_counts(gltf).triangles == 12
    np.testing.assert_allclose(world_bounds(gltf).minimum, [-0.5, 0.0, -0.5])
    np.testing.assert_allclose(world_bounds(gltf).maximum, [0.5, 1.0, 0.5])

    gltf.nodes[0].name = "RenamedRoot"
    normalization = np.diag([2.0, 2.0, 2.0, 1.0])
    normalization[1, 3] = 3.0
    normalization_root = add_normalization_root(
        gltf,
        normalization,
        name="AssetShepherdNormalization",
    )
    save_glb(gltf, output)

    reloaded = load_glb(output)
    validate_loaded_glb(reloaded)
    assert reloaded.nodes[0].name == "RenamedRoot"
    assert reloaded.scenes[0].nodes == [normalization_root]
    assert reloaded.nodes[normalization_root].children == [0]
    assert reloaded.nodes[0].extras == {"sentinel": "preserve"}
    assert reloaded.extensions == {"VENDOR_asset_shepherd_spike": {"sentinel": 42}}
    assert len(reloaded.materials) == 1
    assert len(reloaded.textures) == 1
    assert len(reloaded.images) == 1
    assert geometry_counts(reloaded) == geometry_counts(gltf)
    np.testing.assert_allclose(world_bounds(reloaded).minimum, [-1.0, 3.0, -1.0])
    np.testing.assert_allclose(world_bounds(reloaded).maximum, [1.0, 5.0, 1.0])

    independent_scene = trimesh.load_scene(output, process=False)
    assert independent_scene.bounds is not None
    np.testing.assert_allclose(
        independent_scene.bounds,
        [[-1.0, 3.0, -1.0], [1.0, 5.0, 1.0]],
        atol=1e-6,
    )
