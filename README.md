# mido Mic Fix + AudioRelay Input

KernelSU microphone repair for the tested Redmi Note 4 (`mido`) Android 10
vendor layout, with a **native AudioRelay-input controller under development**.

> **Development branch—not a validated AudioRelay release.** The native controller
> is disabled by default (`RELAY_ENABLED=0`). Do not enable it at boot or distribute
> this build as a working remote-microphone module. The existing [v1.0.0 release](https://github.com/khanra17/mido-internal-mic-fix/releases/tag/v1.0.0)
> remains the supported upper-mic-only build.

## Original microphone repair—preserved

Normal built-in recording uses the settings that worked in a speakerphone call:
two input channels, secondary mic first. This restored internal recording and
Gboard voice typing on the tested phone.

Only `handset-mic` in `/vendor/etc/mixer_paths_mtp.xml` is replaced. The installer
generates the replacement from the phone's verified XML. Speaker, earpiece,
headphone and Bluetooth output paths remain byte-for-byte unchanged. The module
ID remains `mido_internal_mic_fix`, allowing an eventual in-place update.

A single systemless bind mount runs during `post-fs-data`. The original boot-only
HAL refresh is preserved, guarded against an active call. No mounting metamodule
or SELinux relaxation is used. Unknown vendor layouts are rejected.

## Intended AudioRelay behavior

- **Receiver playing:** route only AudioRelay's received microphone stream into
  ordinary microphone/voice-recognition/voice-communication inputs.
- **Receiver stopped/disconnected:** remove that virtual input and keep the
  original repaired upper-mic routing. No transport remains processing silence.
- **Never** capture mido's mixed speaker/caller output for microphone substitution.
- Do not match `REMOTE_SUBMIX` recording source 8, preserving the separate outgoing
  playback-capture route for later full-duplex testing.

Android sees AudioRelay's received stream as its app's decoded media track. The
controller isolates **that package UID + media usage**, not global playback.
It cannot infer whether the sending device selected its microphone or its own
speaker audio. **Select microphone capture on the sending/working phone.**
Do not send mixed playback to the receiver and expect it to become a safe mic.

Connection detection uses the private receiver mix's playback START/STOP activity,
not a network-socket hook. Disconnect/reconnect timing and behavior during ongoing
recording/calls still require validation; they are not guaranteed by this build.
Explicit app-selected/Bluetooth/SCO routes are outside the tested scope.

### Required app setting on mido

AudioRelay → **Settings → Exclusive audio → Deactivated (Play during phone calls)**.
Keep the received stream's volume unmuted. This avoids the interruption that
previously stopped usable audio when Gboard requested exclusive audio focus.
See the [AudioRelay FAQ](https://docs.audiorelay.net/faq). No app preferences,
permissions, assistant roles or focus policies are modified by the module.

## Overhead and implementation

No LSPosed/Xposed, injected libraries, APK, Java/Dex daemon, framework/app hooks,
or blanket microphone-priority overrides are included in the native design.

The C++ daemon registers standard privileged audio policies and waits for Binder
activity callbacks. Its main loop sleeps in `poll()` until an event or termination
signal; there is no 500 ms activity polling, permanent shell supervisor, or dumpsys
loop. The shell only performs bounded startup work and then `exec`s the daemon.
A single startup checksum subprocess verifies the exact supported private ABI.

PCM remains inside audioserver's native software patch (`PatchRecord`/`PatchTrack`).
The controller does not run an app `AudioRecord`, copy/resample PCM itself, or save
voice samples. The current stripped binary is about **25 KiB** and reuses platform
libraries rather than bundling another C++ runtime. **RAM/CPU/battery measurements
are pending; no zero-overhead or battery-life claim is made.**

Private Android 10 Binder/audio APIs are ROM-specific. The daemon verifies the
framework and audio-library SHA-256 values before issuing Binder calls; an unknown
ABI leaves the original mic repair alone. Android's audio service owns each policy
and can remove it on callback-Binder death. Graceful cleanup explicitly removes
its input, patch and policies. Crash/fallback behavior still needs device tests.

## Validation status

- Original mixer fix: tested on qassa `v2.4_beta_1.s`, Android 10, KernelSU 3.1.0.
- Temporary Java **controller with native PCM transport**: remote Gboard typing
  confirmed after private-input availability and AudioRelay-focus corrections.
  Those Java files were routing diagnostics, **not hooks**, and are not packaged.
- C++ controller: builds; policy registration and source START callback observed.
- During the C++ capture-only test, `system_server` crashed in ART/JIT garbage
  collection. The controller detected service death and cleaned up. The stack
  does **not** establish whether this was caused by the test. Investigation paused
  live injection; no KernelSU update was installed.
- C++ remote typing, Telegram, ongoing-recording disconnect/reconnect, simultaneous
  outgoing streaming, latency, idle overhead and first-flash boot behavior: **pending**.

A downloadable remote-input release will only be published after applicable tests
pass. See [docs/VALIDATION.md](docs/VALIDATION.md).

## Installation / rollback

Use the supported v1.0.0 ZIP in KernelSU Manager for the original repair; reboot
and test built-in recording/Gboard. Do not flash in recovery or on unrelated devices.
Disable competing mixer-file modules. Disabling/removing this module and rebooting
restores untouched vendor files. KernelSU safe mode can disable a broken module.
Bluetooth media does not itself require its mic, but apps explicitly requesting
Bluetooth hands-free/SCO may still use that route. The earpiece hardware fault is
not repaired. This is a userspace KernelSU module, **not a replacement kernel image**.

## Build the development ZIP

Python, POSIX `awk`, and Android NDK **r27d / 27.3.13750724** are required:

```sh
python tools/build_native.py --ndk /path/to/android-ndk-r27d
python -m unittest discover -s tests -v
python tools/build.py
```

The builder fetches only necessary headers from pinned Android 10 AOSP sources.
Link-only stubs contain exported symbol names, **not ROM implementations**. Neither
stubs, private headers, ROM libraries, prototype logs nor audio samples enter the
ZIP. Generated dependencies/binaries live in ignored `build/` and `bin/` folders.
The packager preserves ELF bytes and creates a deterministic ZIP + SHA-256 file
under `dist/`. Shell syntax and host tests do not replace on-device validation.

## License

Apache-2.0. The generated vendor XML retains its original The Linux Foundation
BSD notice; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Build-only AOSP
headers retain their upstream notices; they are not shipped with the module.
