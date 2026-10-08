#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build the ABI-pinned arm64 controller; no copied ROM libraries are required.

Link-only stubs contain public symbol names, NOT implementations, and are never
packaged. The executable dynamically uses verified on-device platform libraries.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

import fetch_headers

ROOT = Path(__file__).resolve().parents[1]
NDK_VERSION = "27.3.13750724"


def run(command):
    subprocess.run([str(x) for x in command], check=True)


def build(ndk):
    properties = (ndk / "source.properties").read_text()
    if f"Pkg.Revision = {NDK_VERSION}" not in properties:
        raise RuntimeError(f"Use NDK {NDK_VERSION} (r27d)")
    host = "windows-x86_64" if sys.platform == "win32" else "linux-x86_64"
    suffix = ".exe" if sys.platform == "win32" else ""
    tools = ndk / "toolchains/llvm/prebuilt" / host / "bin"
    clang = tools / f"clang{suffix}"
    cxx = tools / f"clang++{suffix}"
    out = ROOT / "build/native"
    stubdir = out / "link-stubs"
    stubdir.mkdir(parents=True, exist_ok=True)
    fetch_headers.main()
    manifest = json.loads((ROOT / "native/abi-symbols.json").read_text())
    for library, symbols in manifest.items():
        definitions = ["/* Link-only ABI symbols. NEVER load/install this library. */"]
        for name, kind in symbols.items():
            if kind in ("T", "W"):
                definitions.append(f'__attribute__((visibility("default"))) void {name}(void) {{}}')
            elif kind in ("D", "B", "R", "V"):
                definitions.append(f'__attribute__((visibility("default"))) char {name}[512];')
            else:
                raise RuntimeError(f"Unsupported ABI symbol type: {name} {kind}")
        source = stubdir / (library + ".c")
        source.write_text("\n".join(definitions) + "\n", newline="\n")
        run([clang, "--target=aarch64-linux-android29", "-shared", "-fPIC", "-nostdlib",
             f"-Wl,-soname,{library}", source, "-o", stubdir / library])
    obj = out / "relay_mic.o"
    run([cxx, "--target=aarch64-linux-android29", "-std=c++17", "-Os", "-fPIE",
         "-fno-rtti", "-fno-exceptions", "-ffunction-sections", "-fdata-sections",
         "-Wall", "-Wextra", "-Werror", "-I" + str(ROOT / "build/aosp-include"),
         "-c", ROOT / "native/relay_mic.cpp", "-o", obj])
    destination = ROOT / "bin/arm64-v8a/mido-relay-mic"
    destination.parent.mkdir(parents=True, exist_ok=True)
    run([cxx, "--target=aarch64-linux-android29", "-nostdlib++", "-pie",
         "-Wl,--gc-sections", "-Wl,-z,relro,-z,now", "-Wl,--build-id=sha1",
         obj, "-L" + str(stubdir), "-laudioclient", "-lbinder", "-lutils", "-lc++",
         "-o", destination])
    run([tools / f"llvm-strip{suffix}", destination])
    details = subprocess.check_output([tools / f"llvm-readelf{suffix}", "-d", "-r", destination], text=True)
    if "R_AARCH64_COPY" in details or "RUNPATH" in details or "RPATH" in details:
        raise RuntimeError("Unsafe copy relocation or build-time library path in executable")
    print(f"{destination} ({destination.stat().st_size} bytes)")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ndk", type=Path, default=os.environ.get("ANDROID_NDK_HOME"))
    args = parser.parse_args()
    if args.ndk is None:
        parser.error("Provide --ndk PATH or ANDROID_NDK_HOME")
    build(args.ndk.resolve())
