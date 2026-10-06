# mido Internal Mic Fix

A small KernelSU module for the Redmi Note 4 (`mido`) vendor audio layout.

## Fix

Normal built-in recording is routed through the microphone mixer settings that
worked in a speakerphone call: two input channels, with the secondary mic first.
This restored internal recording and Gboard voice typing on the tested phone.

Only the `handset-mic` block in `/vendor/etc/mixer_paths_mtp.xml` is replaced.
The installer generates the file from the phone's own verified vendor XML;
speaker, earpiece, headphone and Bluetooth **output** paths are unchanged.

The module uses a single systemless bind mount during `post-fs-data`. A one-shot
late-start hook refreshes the existing audio HAL if it is already running and the
phone is not in a call. There is no persistent service, polling, audio capture,
framework hook or SELinux policy relaxation. No mounting metamodule is required.

## Tested on

- Redmi Note 4 / `mido`, Qualcomm msm8953
- qassa Android 10: `qassa_Sisu-v2.4_beta_1.s-byNgantu-mido-20260204-0736`
- KernelSU 3.1.0
- Internal recording and Gboard voice typing
- Bluetooth media connected, with recording still using the phone mic

This is a device-specific workaround, not a universal microphone repair. The
installer requires Android 10 and the exact tested stock mixer hash. It refuses
unknown configurations instead of replacing them blindly. If the vendor layout
changes after a ROM update, the boot hook does not mount the replacement.

The working mixer change was tested live. The packaged installer and hooks were
tested without installing a boot-time module; the first flash/reboot is still a
separate validation step.

## Bluetooth and scope

Connecting Bluetooth earbuds for playback does not itself force the recording
input to their mic; the user's successful test retained the phone mic.

This module fixes the built-in recording path. It does **not** disable Bluetooth
or override every app's explicit microphone choice. An app requesting the
Bluetooth hands-free/SCO mic, or a Bluetooth-routed call, may still use that mic.
Globally forcing those cases is a different, unverified policy change and is
intentionally not included. Stereo/dual-mic paths outside `handset-mic` are also
left untouched. The earpiece hardware fault is not repaired.

## Install

1. Download the ZIP from [Releases](https://github.com/khanra17/mido-internal-mic-fix/releases).
2. Flash it in KernelSU Manager.
3. Reboot.
4. Test a phone-mic recording and Gboard, then repeat with Bluetooth media connected.

Do not flash this ZIP in recovery. Disable other modules that replace this mixer
file before installation. Do not add this module on unrelated Redmi models.

## Uninstall

Disable or remove the module in KernelSU Manager and reboot. The original vendor
file is untouched; no microphone preferences or Bluetooth settings need restoring.
If audio fails, use KernelSU safe mode to disable the module and reboot.

## Build

```sh
python -m unittest discover -s tests -v
python tools/build.py
```

The builder creates a deterministic release ZIP and SHA-256 file in `dist/`.
Tests additionally require POSIX `awk`; the Android installer uses KernelSU's
bundled BusyBox. No Android SDK, NDK, JDK or native build is needed.

## License

Apache-2.0 for this project. The generated vendor XML retains its original
The Linux Foundation BSD notice; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
