# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NativeSafetyTests(unittest.TestCase):
    def test_arm64_elf_and_no_bundled_runtime(self):
        binary = (ROOT / 'bin/arm64-v8a/mido-relay-mic').read_bytes()
        self.assertEqual(binary[:5], b'\x7fELF\x02')
        self.assertEqual(int.from_bytes(binary[18:20], 'little'), 183)
        self.assertLess(len(binary), 65536)
        self.assertNotIn(b'libc++_shared.so', binary)

    def test_source_is_isolated_and_no_app_recorder(self):
        source = (ROOT / 'native/relay_mic.cpp').read_text()
        self.assertIn('kMatchUid); request.writeInt32(uid)', source)
        self.assertIn('kMatchUsage); request.writeInt32(1)', source)
        self.assertIn('presets[] = {1, 5, 6, 7, 9}', source)
        self.assertIn('kLoopBackOnly = 2', source)
        self.assertNotIn('AudioRecord(', source)
        self.assertNotIn('AudioTrack(', source)
        self.assertNotIn('setAssistantUid', source)
        self.assertIn('poll(&event, 1, waitMs)', source)

    def test_abi_guard_precedes_binder_start(self):
        source = (ROOT / 'native/relay_mic.cpp').read_text()
        self.assertLess(source.index('if (!verifiedAudioAbi())'),
                        source.index('ProcessState::self()->startThreadPool()'))
        guard = (ROOT / 'native/abi_guard.h').read_text()
        self.assertIn('/system/framework/framework.jar', guard)
        self.assertIn('/system/lib64/libaudioclient.so', guard)
        self.assertIn('kRegister = 72', source)
        self.assertIn('kUnregister = 74', source)

    def test_link_manifest_has_no_implementation(self):
        manifest = json.loads((ROOT / 'native/abi-symbols.json').read_text())
        self.assertEqual(set(manifest), {'libaudioclient.so', 'libbinder.so',
                                         'libutils.so', 'libc++.so'})
        self.assertTrue(all(kind in 'TWDBRV' for symbols in manifest.values()
                            for kind in symbols.values()))

    def test_unvalidated_feature_is_disabled(self):
        config = (ROOT / 'relay.conf').read_text()
        self.assertIn('RELAY_ENABLED=0', config)
        self.assertNotIn('RELAY_ENABLED=1', config)


if __name__ == '__main__':
    unittest.main()
