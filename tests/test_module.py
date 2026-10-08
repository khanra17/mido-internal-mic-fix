# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
STOCK = """<?xml version="1.0" encoding="ISO-8859-1"?>
<mixer>
    <!-- unrelated settings must survive -->
    <path name="speaker">
        <ctl name="LINE_OUT" value="Switch" />
    </path>
    <path name="handset-mic">
        <path name="adc1" />
        <ctl name="IIR1 INP1 MUX" value="DEC1" />
        <ctl name="DEC1 Volume" value="96" />
        <ctl name="DEC2 Volume" value="96" />
    </path>
    <path name="headphones">
        <ctl name="HPHL" value="Switch" />
    </path>
    <path name="voice-rec-mic">
        <path name="handset-mic" />
    </path>
</mixer>
"""
EXPECTED = [
    {"name": "MI2S_TX Channels", "value": "Two"},
    {"name": "ADC3 Volume", "value": "6"},
    {"name": "DEC1 MUX", "value": "ADC2"},
    {"name": "ADC2 MUX", "value": "INP3"},
    {"name": "ADC1 Volume", "value": "6"},
    {"name": "DEC2 MUX", "value": "ADC1"},
]


class PatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.awk = shutil.which("awk")
        if cls.awk is None:
            raise unittest.SkipTest("POSIX awk is required for patch tests")

    def patch(self, source):
        return subprocess.run(
            [self.awk, "-f", str(ROOT / "patch-mixer.awk")],
            input=source, capture_output=True, text=True, check=False
        )

    def test_exact_working_controls_and_unchanged_other_paths(self):
        result = self.patch(STOCK)
        self.assertEqual(result.returncode, 0, result.stderr)
        old = {p.attrib["name"]: p for p in ET.fromstring(STOCK)}
        new = {p.attrib["name"]: p for p in ET.fromstring(result.stdout)}
        self.assertEqual([p.attrib for p in new["handset-mic"]], EXPECTED)
        self.assertEqual(set(old), set(new))
        for name in old:
            if name != "handset-mic":
                # ElementTree drops comments into the preceding element's tail.
                # The raw-text assertion below checks that surrounding whitespace is preserved.
                old[name].tail = new[name].tail = None
                self.assertEqual(ET.tostring(old[name]), ET.tostring(new[name]))
        # Check the actual text outside the replaced block, not just XML semantics.
        def omit_block(text):
            text = re.sub(r"    <!-- Use the working speakerphone.*? -->\n", "", text)
            return re.sub(
                r'    <path name="handset-mic">\n.*?    </path>\n',
                "", text, flags=re.S
            )
        self.assertEqual(omit_block(STOCK), omit_block(result.stdout))

    def test_missing_path_fails(self):
        result = self.patch(STOCK.replace('name="handset-mic"', 'name="other-mic"'))
        self.assertNotEqual(result.returncode, 0)

    def test_duplicate_path_fails(self):
        block = '    <path name="handset-mic">\n    </path>\n'
        self.assertNotEqual(self.patch(STOCK.replace("</mixer>", block + "</mixer>")).returncode, 0)

    def test_unterminated_path_fails(self):
        self.assertNotEqual(
            self.patch(STOCK[:STOCK.index('        <path name="adc1"')]).returncode, 0
        )

    def test_no_forward_reference_to_speakerphone_path(self):
        output = self.patch(STOCK).stdout
        path = ET.fromstring(output).find("./path[@name='handset-mic']")
        self.assertTrue(all(child.tag == "ctl" for child in path))


class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("module_build", ROOT / "tools/build.py")
        cls.builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.builder)

    def test_deterministic_zip_and_checksum(self):
        import hashlib
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            first = self.builder.build(base / "first")
            second = self.builder.build(base / "second")
            self.assertEqual(first.read_bytes(), second.read_bytes())
            digest = hashlib.sha256(first.read_bytes()).hexdigest()
            self.assertEqual(
                first.with_suffix(".zip.sha256").read_text(encoding="ascii"),
                f"{digest}  {first.name}\n"
            )

    def test_zip_contains_only_module_files_with_correct_permissions(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = self.builder.build(Path(temp))
            with zipfile.ZipFile(archive) as bundle:
                self.assertEqual(set(bundle.namelist()), set(self.builder.PAYLOAD))
                self.assertEqual(bundle.read("skip_mount"), b"")
                for entry in bundle.infolist():
                    data = bundle.read(entry)
                    if entry.filename == self.builder.BINARY:
                        self.assertEqual(data, (ROOT / entry.filename).read_bytes())
                        self.assertTrue(data.startswith(b"\x7fELF"))
                    else:
                        self.assertNotIn(b"\r", data)
                    expected = 0o755 if entry.filename in self.builder.EXECUTABLES else 0o644
                    self.assertEqual(stat.S_IMODE(entry.external_attr >> 16), expected)
                    self.assertFalse(entry.filename.startswith(("/", "META-INF/")))
                    self.assertNotIn("..", Path(entry.filename).parts)

    def test_rejects_invalid_native_executables(self):
        import struct
        valid = (ROOT / self.builder.BINARY).read_bytes()
        self.builder.validate_native(valid)
        malformed = [valid[:8]]
        wrong_arch = bytearray(valid)
        struct.pack_into('<H', wrong_arch, 18, 62)  # x86-64, not AArch64.
        malformed.append(wrong_arch)
        no_entry = bytearray(valid)
        struct.pack_into('<Q', no_entry, 24, 0)
        malformed.append(no_entry)
        shared_library = bytearray(valid)
        phoff = struct.unpack_from('<Q', valid, 32)[0]
        phsize, phcount = struct.unpack_from('<HH', valid, 54)
        for index in range(phcount):
            offset = phoff + index * phsize
            if struct.unpack_from('<I', valid, offset)[0] == 3:
                struct.pack_into('<I', shared_library, offset, 0)  # No PT_INTERP.
        malformed.append(shared_library)
        for data in malformed:
            with self.subTest(size=len(data)):
                with self.assertRaises(ValueError):
                    self.builder.validate_native(data)

    def test_module_properties_and_integrity_guards(self):
        props = dict(line.split("=", 1) for line in
                     (ROOT / "module.prop").read_text().splitlines() if line)
        self.assertEqual(props["id"], "mido_internal_mic_fix")
        self.assertTrue(props["versionCode"].isdigit())
        common = (ROOT / "common.sh").read_text()
        self.assertRegex(common, r"STOCK_SHA256=[0-9a-f]{64}\n")
        self.assertRegex(common, r"FIXED_SHA256=[0-9a-f]{64}\n")
        self.assertNotIn("REPLACE_FIXED_SHA256", common)


if __name__ == "__main__":
    unittest.main()
