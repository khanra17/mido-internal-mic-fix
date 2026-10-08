# mido Mic Fix + AudioRelay Input

KernelSU microphone repair for the tested Redmi Note 4 (`mido`) Android 10
vendor layout, with an **experimental native AudioRelay-input controller**.

> **Rc1 is withdrawn after repeated Android system_server crashes.** Native
> autostart is disabled (`RELAY_ENABLED=0`); do not enable it. The latest hardened
> capture-only retry also crashed, without microphone substitution. Investigation
> is ongoing. Stable [v1.0.0](https://github.com/khanra17/mido-internal-mic-fix/releases/tag/v1.0.0)
> remains available for upper-mic-only use.

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
- Installed C++ rc1: user confirmed upper-mic and remote Gboard input after reboot.
- Native trials produced three system_server crashes: ART GC, Binder/wake-lock
  cleanup, and network statistics. The latest occurred during capture-only mode
  after a receiver reconnect. Exact causation remains unresolved.
- Server-only trial without the controller did not crash. Thread-safety hardening
  and ABI checks did not resolve the native capture-only failure.
- Simultaneous outgoing Apps-server streaming echoed the incoming mic; unsupported.
- Telegram, robust fallback/recovery, Bluetooth priority, latency and resource use
  remain unverified. Live native tests are paused; rc1 downloads withdrawn.

See [docs/VALIDATION.md](docs/VALIDATION.md) and
[crash evidence](docs/issues/capture-only-crash.md).

## Installation / rollback

Use stable [v1.0.0](https://github.com/khanra17/mido-internal-mic-fix/releases/tag/v1.0.0)
for the original upper-mic repair. Install its ZIP through KernelSU Manager and
reboot. Do not install rc1 or enable the development controller.

For an existing rc1 installation, keep `RELAY_ENABLED=0` in the installed module's
`relay.conf`. This preserves the original mixer repair without the native daemon.
The test device has already been set to this safe state.

Do not flash in recovery or on unrelated devices. Disable competing mixer-file
modules. If Android/audio becomes unstable, **disable/remove rc1 in KernelSU and
reboot**; use KernelSU safe mode if normal boot is unavailable. Keep v1.0.0 for
rollback. Set `RELAY_ENABLED=0` in the module's `relay.conf` and reboot if you want
only the original mic repair. No prototype JARs/scripts are needed on the phone.

The daemon does not repeatedly restart itself or Android services after failure.
If it exits, `relay.log` under `/data/adb/modules/mido_internal_mic_fix/` contains
its startup/cleanup status. Provide that log when reporting failures; do not change
ABI guards or globally relax privacy/SELinux to make it start.
Bluetooth media does not itself require its mic, but apps explicitly requesting
Bluetooth hands-free/SCO may still use that route. The earpiece hardware fault is
not repaired. This is a userspace KernelSU module, **not a replacement kernel image**.

## Build the experimental ZIP

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
