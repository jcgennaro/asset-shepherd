"""Export HTML title cards with isolated headless Chrome; no app/model calls."""

import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent
chrome = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
for name in (
    "market",
    "roles",
    "toolkit",
    "architecture-1",
    "architecture-2",
    "architecture-3",
    "architecture-4",
    "models",
    "thanks",
):
    subprocess.run(
        [
            str(chrome),
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--hide-scrollbars",
            "--force-device-scale-factor=1",
            "--window-size=1920,1080",
            "--user-data-dir=" + str(root.parents[2] / "build" / "pitch-slides-browser"),
            "--screenshot=" + str(root / (name + ".png")),
            (root / "index.html").as_uri() + "#" + name,
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    print(name + ".png")
