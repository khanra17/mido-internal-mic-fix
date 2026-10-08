# AudioRelay native-controller release gate

**Rc1 was withdrawn after another system_server crash during the hardened native
capture-only retry.** Development and installed-device autostart are now disabled
(`RELAY_ENABLED=0`). The original upper-mic repair remains enabled. Stable v1.0.0
is unchanged. No more live native trials until the failure is better isolated.
See [issues/capture-only-crash.md](issues/capture-only-crash.md).

## Confirmed

- UID-isolated incoming AudioRelay media is not mido's mixed playback.
- Internal audioserver software patch transports PCM without a competing root app recorder.
- Temporary Java-controlled native bridge delivered the WORKING PHONE's mic to Gboard.
- Required mido setting: Exclusive audio = Deactivated (Play during phone calls).
- C++ native controller registers policies and receives source MIXING callback.
- ABI-pinned native executable builds with warnings as errors; about 25 KiB stripped.
- Build needs no redistributed device libraries: link-only exported-symbol stubs suffice.

## Known risk to disclose before install/retry

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

## Required on-device checks before stable promotion

These apply to a future candidate AFTER crash isolation. Do not install withdrawn
rc1. Receiver-only baseline and the prepared (not yet run) policy-only diagnostic
are documented in [issues/policy-only-isolation.md](issues/policy-only-isolation.md).

1. User installs a validated candidate in KernelSU and reboots with rollback
   available. Test upper mic with AudioRelay disconnected; verify startup guards.
2. Connect a proven working-phone MICROPHONE stream. Rc1 enables the private input
   when the receiver mix starts; prove Gboard listens to the working phone, not mido,
   and verify actual addressed input, sustained PCM and unsilenced state.
3. Telegram call to a separate recipient: only working-phone mic heard.
4. Disconnect during ongoing typing/recording/call: upper-mic fallback; reconnect:
   remote mic returns without restarting the recording app, or document limitations.
5. Repeat idle connection, silence, network loss, stream restart and process termination.
6. Graceful stop + forced Binder-owner death: no private inputs/policies/patch residue;
   original hash/mount and enforcing SELinux preserved.
7. Concurrent mido playback → working phone stream: no caller/playback-to-mic feedback.
8. Measure idle RAM/CPU/wakeups and active transport; compare latency/buffering.
9. Only after these checks: review findings/source/build, rerun CI and promote a
   stable release. Keep native autostart disabled until crash validation passes;
   rc1's historical autostart exception was not proof of runtime stability.

## First installed rc1 result

User confirmed both disconnected upper-mic and connected remote Gboard input after
flashing/rebooting rc1. Full-duplex Apps-server mode echoed the incoming stream;
stopping the server coincided with a new system_server Binder/wake-lock crash.
The controller exited on service death; remote routing no longer reactivates by
client reconnection alone. **Do not use simultaneous Apps server/client yet.**
See [issues/rc1-post-install.md](issues/rc1-post-install.md) for evidence and limits.
Telegram and robust recovery remain pending; no crash-causation claim is made.

## Rc1 preparation

- Removed all our temporary scripts, JARs, binaries, log directory and native lock
  from the phone; diagnostics archived on the PC only. No prototype policies or
  processes remain. Original mixer hash/mount unchanged; SELinux enforcing.
- Native cleanup now preserves failures/handles, propagates errors and prevents
  further activation after teardown failure. Uninstall waits for graceful exit.
- Packager rejects malformed, wrong-architecture or non-executable ELF files.
- Native binary is about 25 KiB; CPU/RAM/battery figures remain unmeasured.

No PCM samples are saved. Diagnostics contain configuration, counters and levels.
