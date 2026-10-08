#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Package a deterministic KernelSU ZIP after tools/build_native.py."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import stat
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = (
    "module.prop", "customize.sh", "common.sh", "patch-mixer.awk",
    "post-fs-data.sh", "service.sh", "skip_mount",
    "LICENSE", "THIRD_PARTY_NOTICES.md", "README.md", "relay.conf",
    "uninstall.sh", "bin/arm64-v8a/mido-relay-mic", "docs/VALIDATION.md",
)
BINARY = "bin/arm64-v8a/mido-relay-mic"
EXECUTABLES = {"customize.sh", "post-fs-data.sh", "service.sh", "uninstall.sh", BINARY}


def validate_native(data: bytes) -> None:
    """Require a real ELF64 little-endian AArch64 PIE/EXEC, not a .so or stub."""
    if len(data) < 64 or data[:7] != b"\x7fELF\x02\x01\x01":
        raise ValueError("Expected a complete ELF64 little-endian executable")
    kind, machine, version, entry, phoff = struct.unpack_from("<HHIQQ", data, 16)
    ehsize, phsize, phcount = struct.unpack_from("<HHH", data, 52)
    if (kind not in (2, 3) or machine != 183 or version != 1 or not entry or
            ehsize != 64 or phsize != 56 or not 0 < phcount <= 64 or phoff < 64 or
            phoff + phsize * phcount > len(data)):
        raise ValueError("Invalid AArch64 executable header/program table")
    interpreter = executable_load = False
    for index in range(phcount):
        ptype, flags, offset, address, _, size, memory_size, _ = struct.unpack_from(
            "<IIQQQQQQ", data, phoff + index * phsize)
        if offset + size > len(data):
            raise ValueError("ELF program segment is truncated")
        if ptype == 3:
            interpreter = data[offset:offset + size] == b"/system/bin/linker64\0"
        if ptype == 1 and flags & 1 and address <= entry < address + memory_size:
            executable_load = True
    if not interpreter or not executable_load:
        raise ValueError("ELF must have Android linker64 and executable LOAD segments")


def build(destination: Path) -> Path:
    props = dict(
        line.split("=", 1)
        for line in (ROOT / "module.prop").read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    )
    native = (ROOT / BINARY).read_bytes()
    validate_native(native)  # Fail before creating a partial ZIP.
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / f"mido-internal-mic-fix-{props['version']}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as bundle:
        for name in PAYLOAD:
            data = native if name == BINARY else (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
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
