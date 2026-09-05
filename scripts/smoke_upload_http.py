"""Check upload-to-description in an isolated web container without any model invocation."""

import argparse
import json
import time
from pathlib import Path
from urllib.parse import urljoin

import httpx


def main() -> None:
    """Fail the image build if its actual Linux upload subprocess cannot complete."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", default="http://127.0.0.1:8080")
    parser.add_argument("--asset", type=Path, default=Path("fixtures/broken_robot.glb"))
    args = parser.parse_args()
    with httpx.Client(base_url=args.origin, timeout=15) as client:
        started = time.monotonic()
        with args.asset.open("rb") as stream:
            uploaded = client.post(
                "/workspace/new/upload",
                files={"asset": (args.asset.name, stream, "model/gltf-binary")},
            )
        assert uploaded.status_code == 303, uploaded.status_code
        upload_seconds = time.monotonic() - started
        assert upload_seconds < 10
        describe = urljoin(args.origin, uploaded.headers["location"])
        status = describe.replace("/describe", "/upload-status")
        while time.monotonic() - started < 250:
            receipt = client.get(status)
            receipt.raise_for_status()
            state = receipt.json()["state"]
            client.get("/healthz").raise_for_status()
            if state != "CHECKING":
                assert state == "READY", receipt.text
                page = client.get(describe)
                page.raise_for_status()
                assert 'name="description"' in page.text
                print(
                    json.dumps(
                        {
                            "state": state,
                            "upload_seconds": round(upload_seconds, 3),
                            "total_seconds": round(time.monotonic() - started, 3),
                            "model_calls": 0,
                        }
                    )
                )
                return
            time.sleep(1)
        raise RuntimeError("Upload check did not complete within its bounded deadline")


if __name__ == "__main__":
    main()
