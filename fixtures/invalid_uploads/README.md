# Invalid upload fixtures

These deliberately tiny files exercise the upload boundary without involving the agent:

- `tiny-gibberish.glb` has neither the GLB magic bytes nor a complete header.
- `truncated-clean-robot.glb` is the first 64 bytes of the valid generated robot fixture.
- `invalid-json-chunk.glb` has a complete GLB 2.0 header and an invalid JSON chunk.
- `minimal-ascii.fbx` resembles the start of an ASCII FBX file but uses an unsupported extension.

Regenerate them with `uv run python scripts/generate_invalid_upload_fixtures.py`.
