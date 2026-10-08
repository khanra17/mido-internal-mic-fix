# Crash investigation: controller versus Android

## Findings

The 13:11 system_server crash is an unsigned division-by-zero in
VectorImpl::_shrink. The matching libutils BuildId is
`a91d6a649317e53ac3e9caab875949d2`. At 0x15e2c it loads the vector's immutable
item-size field (offset 0x20); at 0x15e30, zero branches to the UBSAN abort at
0x160ac. This is invalid vector state, not normal final-item removal. The caller
is BpBinder::unlinkToDeath during PowerManagerService wake-lock release.

The older 11:12 crash is different: ART JIT root-table sweeping dereferences
0x75006f00630063, resembling UTF-16 data in place of a pointer. Neither trace
establishes where the bad state originated. Our controller does not call
PowerManager, and process-local C++ memory cannot directly overwrite
system_server memory. Module involvement is NOT ruled out by this alone.

## Retracted Parcel claim

An initial audit counted only the fields before Parcel's nested classes and
mistakenly reported a 112-byte object. The full header includes mOpenAshmemSize
AFTER those classes, at offset 0x70. Actual NDK compiler layout is 120 bytes,
alignment 8. The ROM constructor's write at 0x70 is IN BOUNDS. No Parcel-size
overrun was established. The initial claim was corrected to the user before
any controller retry. No opaque Parcel replacement or system-library patch remains.

## Verified layouts and hardening

- Compiler layouts match inspected ROM constructor or marshalling footprints:
  Parcel 120, RefBase 16, IBinder 24, BBinder 40, PolicyCallback 48, ServiceDeath 24,
  String8/16 8, audio_port_config 216, audio_port 1308, audio_patch 6924.
- Added compile-time size/alignment assertions and selected audio-field offsets.
  Hashes identify libraries; they do not alone prove class-layout compatibility.
- Added --abi-self-test with canaries around native Parcel storage, integer/string
  round trip and explicit destructor. No service lookup, policy or audio transport.
- On-device local test PASSED; system_server PID 6854 and audioserver PID 6607
  remained unchanged, SELinux enforcing. Temporary executable removed immediately.
- Corrected actual C++ data races: stop/arming flags are lock-free atomics, including
  writes from Binder callbacks/signals and reads from the main thread. This is
  NOT a demonstrated fix for the Android heap/vector crashes.
- Added monotonic timestamps at source START/STOP and controller start/stop, plus
  shutdown reason (1 signal, 2 AudioSystem death, 3 AudioService death).

No app/framework hooks, APK/permission changes, system-library edits, SELinux
relaxation, HAL/audio-service restart or persistent prototype process was used.
Installed rc1 binary/config has not been updated. No new ZIP/release is published.

## Next discriminating test

The installed controller remains stopped after the earlier crash, and its policies
are gone. Ask the user to disconnect mido's incoming receiver, start its AudioRelay
Apps server, connect the working phone as its client and stop the server once.
Save work first: this may reproduce the Android crash. Collect fresh crash logs,
service PIDs and tombstone if it happens. Do not force app restarts.

If that baseline crashes without native routing, investigate the AudioRelay/ROM
path independently. If it does not, use a bounded, user-coordinated native control
retry with the current hardened build, starting capture-only. Restore single-client
remote Gboard before Telegram; keep Bluetooth and full duplex out of that test.

Crash resolution, service-death recovery and Bluetooth priority remain unverified.
