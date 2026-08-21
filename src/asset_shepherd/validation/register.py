"""Register an untouched real-world GLB without modifying the raw file."""

import argparse
import json
from hashlib import sha256
from pathlib import Path

from asset_shepherd.glb import load_glb, validate_loaded_glb
from asset_shepherd.validation.models import AssetProvenance


class RegistrationError(ValueError):
    """Raised when an asset cannot enter the blind corpus safely."""


def hash_file(path: Path) -> str:
    """Calculate SHA-256 without loading a potentially large asset into memory."""
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def register_raw_asset(asset_path: Path, provenance_path: Path) -> AssetProvenance:
    """Validate, hash, and register one immutable GLB after human facts are complete."""
    asset_path = asset_path.resolve(strict=True)
    provenance_path = provenance_path.resolve(strict=True)
    provenance = AssetProvenance.model_validate_json(provenance_path.read_text(encoding="utf-8"))
    missing = provenance.registration_errors()
    if missing:
        raise RegistrationError(f"Provenance is incomplete: {', '.join(missing)}")
    before_hash = hash_file(asset_path)
    if provenance.raw_sha256 and provenance.raw_sha256 != before_hash:
        raise RegistrationError("Existing provenance hash does not match the raw asset")
    loaded = load_glb(asset_path)
    validate_loaded_glb(loaded)
    after_hash = hash_file(asset_path)
    if after_hash != before_hash:
        raise RegistrationError("Raw asset changed while it was being registered")
    registered = AssetProvenance.model_validate(
        {
            **provenance.model_dump(mode="python"),
            "raw_sha256": before_hash,
        }
    )
    temporary_path = provenance_path.with_suffix(".json.tmp")
    temporary_path.write_text(
        f"{json.dumps(registered.model_dump(mode='json'), indent=2, sort_keys=True)}\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary_path.replace(provenance_path)
    return registered


def main() -> None:
    """Register one raw GLB from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asset", type=Path)
    parser.add_argument("--provenance", type=Path, required=True)
    args = parser.parse_args()
    registered = register_raw_asset(args.asset, args.provenance)
    print(json.dumps(registered.model_dump(mode="json"), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
