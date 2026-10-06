#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build a deterministic KernelSU ZIP using only the Python standard library."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = (
    "module.prop", "customize.sh", "common.sh", "patch-mixer.awk",
    "post-fs-data.sh", "service.sh", "skip_mount",
    "LICENSE", "THIRD_PARTY_NOTICES.md", "README.md",
)
EXECUTABLES = {"customize.sh", "post-fs-data.sh", "service.sh"}


def build(destination: Path) -> Path:
    props = dict(
        line.split("=", 1)
        for line in (ROOT / "module.prop").read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    )
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / f"mido-internal-mic-fix-{props['version']}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as bundle:
        for name in PAYLOAD:
            data = (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
            entry = zipfile.ZipInfo(name, date_time=(2000, 1, 1, 0, 0, 0))
            entry.create_system = 3
            mode = 0o755 if name in EXECUTABLES else 0o644
            entry.external_attr = (stat.S_IFREG | mode) << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(entry, data, compresslevel=9)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(
        f"{digest}  {archive.name}\n", encoding="ascii", newline="\n"
    )
    return archive


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    result = build(args.out.resolve())
    print(result)
    print(result.with_suffix(".zip.sha256").read_text(encoding="ascii").strip())


if __name__ == "__main__":
    main()
