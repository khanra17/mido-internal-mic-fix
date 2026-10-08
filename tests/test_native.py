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

    def test_verified_layouts_and_local_self_test(self):
        source = (ROOT / 'native/relay_mic.cpp').read_text()
        layouts = (ROOT / 'native/abi_layouts.h').read_text()
        probe = (ROOT / 'native/abi_self_test.h').read_text()
        self.assertIn('sizeof(Parcel) == 120', layouts)
        self.assertIn('sizeof(audio_port) == 1308', layouts)
        self.assertIn('sizeof(audio_patch) == 6924', layouts)
        self.assertLess(source.index('if (abiSelfTest() != 0)'),
                        source.index('ProcessState::self()->startThreadPool()'))
        self.assertIn('parcel->~Parcel()', probe)
        self.assertIn('frame.before == marker && frame.after == marker', probe)
        self.assertNotIn('transact(', probe)

    def test_callback_and_signal_flags_are_lock_free_atomics(self):
        source = (ROOT / 'native/relay_mic.cpp').read_text()
        self.assertIn('std::atomic<int> stopping{0}, armed{1}', source)
        self.assertIn('std::atomic<int>::is_always_lock_free', source)
        self.assertNotIn('volatile sig_atomic_t stopping', source)
        self.assertIn('stopping.load(std::memory_order_relaxed)', source)
        self.assertIn('STOP monoMs=', source)

    def test_policy_only_has_a_required_bounded_timeout(self):
        source = (ROOT / 'native/relay_mic.cpp').read_text()
        self.assertIn('strcmp(argv[i], "--policy-only")', source)
        begin = source.index('    if (policyOnly) {')
        end = source.index('    char property[PROP_VALUE_MAX]', begin)
        gate = source[begin:end]
        self.assertIn('timeoutSeconds <= 0 || timeoutSeconds > 1800', gate)
        self.assertIn('return 2;', gate)
        self.assertIn('captureOnly = true;', gate)
        self.assertNotIn('--policy-only', (ROOT / 'service.sh').read_text())

    def test_cli_rejects_malformed_bounds_and_missing_values(self):
        source = (ROOT / 'native/relay_mic.cpp').read_text()
        self.assertNotIn('atoi(', source)
        self.assertIn("*p < '0' || *p > '9'", source)
        self.assertIn('parsed > INT_MAX', source)
        self.assertIn('++i >= argc || !nonnegativeInt(argv[i], uid)', source)
        self.assertIn('++i >= argc || !nonnegativeInt(argv[i], timeoutSeconds)', source)
        self.assertLess(source.index('const int64_t deadline ='),
                        source.index('status_t status = bridge.start(uid, captureOnly)'))

    def test_policy_only_blocks_transport_and_signal_arming(self):
        source = (ROOT / 'native/relay_mic.cpp').read_text()
        route = source.split('    status_t route(bool remoteMicrophone) {', 1)[1]
        route = route.split('    status_t fallback()', 1)[0]
        guard = route.split('        if (remoteMicrophone &&', 1)[0]
        self.assertIn('if (policyOnly_)', guard)
        self.assertIn('return NO_ERROR;', guard)
        self.assertNotIn('registerPolicy(', guard)
        self.assertNotIn('createAudioPatch(', guard)
        self.assertNotIn('connect(', guard)
        self.assertIn('const bool policyOnly_;', source)
        self.assertIn('Bridge bridge(policyOnly)', source)
        self.assertIn('!policyOnly && armed.load(std::memory_order_relaxed)', source)
        self.assertIn('if (captureOnly || policyOnly_)', source)

    def test_link_manifest_has_no_implementation(self):
        manifest = json.loads((ROOT / 'native/abi-symbols.json').read_text())
        self.assertEqual(set(manifest), {'libaudioclient.so', 'libbinder.so',
                                         'libutils.so', 'libc++.so'})
        self.assertTrue(all(kind in 'TWDBRV' for symbols in manifest.values()
                            for kind in symbols.values()))

    def test_native_autostart_is_safety_disabled(self):
        config = (ROOT / 'relay.conf').read_text()
        self.assertIn('RELAY_ENABLED=0', config)
        self.assertIn('system_server crashes', config)
        props = (ROOT / 'module.prop').read_text()
        self.assertIn('version=v2.0.0-rc1', props)
        self.assertIn('EXPERIMENTAL', props)

    def test_cleanup_errors_are_propagated(self):
        source = (ROOT / 'native/relay_mic.cpp').read_text()
        self.assertIn('status = bridge.fallback()', source)
        self.assertIn('const status_t cleanupStatus = bridge.cleanup()', source)
        self.assertIn('if (status == NO_ERROR) patch = AUDIO_PATCH_HANDLE_NONE', source)
        self.assertIn('CLEANUP_INCOMPLETE', source)


if __name__ == '__main__':
    unittest.main()
