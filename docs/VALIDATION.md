# AudioRelay native-controller release gate

This branch is development-only. `RELAY_ENABLED=0`; no native autostart release.
Original installed mixer module/hash remains unchanged.

## Confirmed

- UID-isolated incoming AudioRelay media is not mido's mixed playback.
- Internal audioserver software patch transports PCM without a competing root app recorder.
- Temporary Java-controlled native bridge delivered the WORKING PHONE's mic to Gboard.
- Required mido setting: Exclusive audio = Deactivated (Play during phone calls).
- C++ native controller registers policies and receives source MIXING callback.
- ABI-pinned native executable builds with warnings as errors; about 25 KiB stripped.
- Build needs no redistributed device libraries: link-only exported-symbol stubs suffice.

## Investigate before retry

2026-10-08, approximately 11:12 IST: system_server died with SIGSEGV in
`art::jit::JitCodeCache::SweepRootTables` during GC. Native capture controller
received service death and logged cleanup; no active substitution remains.
This coincided with a native control/Gboard test, but the stack does not prove
causation. Do not hide or label this as a passed native test.

A separate initial development mistake used generic AOSP IAudioService ordinals.
The tested ROM has register/unregister ordinals 72/74, verified by read-only Stub
reflection. The attempted ordinal 70 was HDMI-system-audio setting; this phone
has no matching HDMI service and `mHdmiSystemAudioSupported` remained false.
Correct ordinals and mandatory framework/library checksum guard are now in code.
No more unverified Binder transactions or global service restarts during testing.

## Required temporary on-device checks

1. Controlled retry after crash review; prove sustained PCM on exact private source.
2. Enable C++ virtual input only after source evidence, then prove Gboard listens to
   working phone, not mido; confirm actual addressed input and unsilenced state.
3. Telegram call to a separate recipient: only working-phone mic heard.
4. Disconnect during ongoing typing/recording/call: upper-mic fallback; reconnect:
   remote mic returns without restarting the recording app, or document limitations.
5. Repeat idle connection, silence, network loss, stream restart and process termination.
6. Graceful stop + forced Binder-owner death: no private inputs/policies/patch residue;
   original hash/mount and enforcing SELinux preserved.
7. Concurrent mido playback → working phone stream: no caller/playback-to-mic feedback.
8. Measure idle RAM/CPU/wakeups and active transport; compare latency/buffering.
9. Only after these checks: enable default autostart, review source/build, run CI,
   merge, tag and publish release ZIP/checksum. User performs first install/reboot.

No PCM samples are saved. Diagnostics contain configuration, counters and levels.
