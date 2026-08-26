"""Generate tiny, deliberately invalid files for upload-boundary acceptance tests."""

from __future__ import annotations

from pathlib import Path
from struct import pack

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = PROJECT_ROOT / "fixtures" / "invalid_uploads"


def generate() -> tuple[Path, ...]:
    """Write a reproducible set of malformed or unsupported upload examples."""
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    clean_glb = (PROJECT_ROOT / "fixtures" / "clean_robot.glb").read_bytes()
    malformed_json = b"{oops}  "
    invalid_json_glb = (
        b"glTF"
        + pack("<II", 2, 12 + 8 + len(malformed_json))
        + pack("<II", len(malformed_json), 0x4E4F534A)
        + malformed_json
    )
    payloads = {
        "tiny-gibberish.glb": b"not-a-glb\n\x00\xff\x01",
        "truncated-clean-robot.glb": clean_glb[:64],
        "invalid-json-chunk.glb": invalid_json_glb,
        "minimal-ascii.fbx": (
            b"; FBX 7.4.0 project file\n"
            b"; deliberately incomplete upload-boundary fixture\n"
            b"FBXHeaderExtension: {\n"
            b"  FBXHeaderVersion: 1003\n"
            b"  FBXVersion: 7400\n"
            b"}\n"
        ),
    }
    generated: list[Path] = []
    for name, payload in payloads.items():
        path = OUTPUT_ROOT / name
        path.write_bytes(payload)
        generated.append(path)
    return tuple(generated)


if __name__ == "__main__":
    for generated_path in generate():
        print(generated_path.relative_to(PROJECT_ROOT))
