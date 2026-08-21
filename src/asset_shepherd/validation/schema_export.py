"""Deterministically export the addendum's real-world validation schemas."""

import argparse
import json
from pathlib import Path
from typing import Final

from pydantic import BaseModel

from asset_shepherd.validation.models import (
    Adjudication,
    AssetProvenance,
    MutationManifest,
)

VALIDATION_SCHEMA_MODELS: Final[dict[str, type[BaseModel]]] = {
    "adjudication.schema.json": Adjudication,
    "asset_provenance.schema.json": AssetProvenance,
    "mutation_manifest.schema.json": MutationManifest,
}


def export_validation_schemas(output_dir: Path) -> tuple[Path, ...]:
    """Write stable Draft 2020-12 schemas for corpus records."""
    output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    for filename, model in sorted(VALIDATION_SCHEMA_MODELS.items()):
        schema = model.model_json_schema(mode="serialization")
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema["$id"] = f"https://asset-shepherd.dev/schemas/validation/v1/{filename}"
        path = output_dir / filename
        path.write_text(
            f"{json.dumps(schema, indent=2, sort_keys=True)}\n",
            encoding="utf-8",
            newline="\n",
        )
        generated.append(path)
    return tuple(generated)


def main() -> None:
    """Export validation schemas from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("validation/schemas"))
    args = parser.parse_args()
    export_validation_schemas(args.output)


if __name__ == "__main__":
    main()
