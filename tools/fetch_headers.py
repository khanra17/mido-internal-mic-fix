#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fetch only required private ABI headers from pinned Android 10 AOSP sources.

Generated build dependencies are not installed on Android or committed to Git.
Their upstream license notices are preserved. No ROM binaries are downloaded.
"""
import base64
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "build" / "aosp-include"
TAG = "android-10.0.0_r47"
BASES = {
    "binder": ("frameworks/native", "libs/binder/include"),
    "utils": ("system/core", "libutils/include"),
    "cutils": ("system/core", "libcutils/include"),
    "android-base": ("system/core", "base/include"),
    "log": ("system/core", "liblog/include"),
    "android": ("system/core", "liblog/include"),
}
SYSTEM_BASES = (
    ("system/media", "audio/include"),
    ("system/media", "audio_effects/include"),
    ("system/core", "libsystem/include"),
)
INCLUDE = re.compile(r'^\s*#\s*include\s*(?:<([^>]+)>|"([^"]+)")', re.M)


def fetch(name):
    output = DEST / name
    if output.exists():
        return name, output.read_text(encoding="utf-8")
    top = name.split("/", 1)[0]
    candidates = SYSTEM_BASES if top == "system" else (BASES[top],)
    for repo, directory in candidates:
        url = f"https://android.googlesource.com/platform/{repo}/+/{TAG}/{directory}/{name}?format=TEXT"
        for retry in range(3):
            try:
                with urllib.request.urlopen(url, timeout=30) as response:
                    data = base64.b64decode(response.read())
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(data)
                return name, data.decode("utf-8")
            except urllib.error.HTTPError as error:
                if error.code == 404:
                    break
                if retry == 2:
                    raise
                time.sleep(1)
    raise RuntimeError(f"Pinned AOSP header not found: {name}")


def main():
    pending = {"binder/Binder.h", "binder/Parcel.h", "binder/ProcessState.h",
               "binder/IServiceManager.h", "utils/String16.h", "utils/String8.h",
               "system/audio.h", "system/audio_policy.h"}
    seen = set()
    with ThreadPoolExecutor(max_workers=6) as pool:
        while pending:
            batch = sorted(pending - seen)
            pending = set()
            seen.update(batch)
            for name, content in pool.map(fetch, batch):
                print(name)
                for angle, quoted in INCLUDE.findall(content):
                    dep = angle or quoted
                    if quoted and "/" not in dep:
                        dep = str(Path(name).parent / dep).replace("\\", "/")
                    top = dep.split("/", 1)[0]
                    if (top in BASES and top != "android") or top == "system" or dep == "android/log.h":
                        if dep not in seen:
                            pending.add(dep)
    print(f"{len(seen)} headers in {DEST}")


if __name__ == "__main__":
    main()
