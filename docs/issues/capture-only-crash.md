# Hardened capture-only crash, 2026-10-08

The user confirmed mido's upper mic worked during capture-only testing, then
reported another Android crash. No virtual-mic policy was registered or enabled.

## Sequence

- AudioRelay Apps-server-only start/connect/stop, with the native controller stopped:
  user reported no crash. Service PIDs remained unchanged; no new tombstone.
- Hardened controller started at 15:58:19 IST with ABI checks, local Parcel self-test,
  lock-free atomic stop flags, UID-isolated source/dummy policies and 30-minute cutoff.
- Source START at monoMs10919723: native capture patch155 succeeded.
- Source STOP at10980512: patch155 released and fallback succeeded.
- Source START at10983164: capture patch170 succeeded.
- Service death at10985167, approximately two seconds later: controller stopped,
  patch170 released, private outputs disconnected. Policy cleanup reported DEAD_OBJECT.

At 16:09:26 IST, system_server6854 SIGSEGV in libbpf_android findMapEntry, called by
libnetdbpf/interface statistics and NetworkStatsService.getTotalStats. Bad address
0x78656e20746547; register x0 contains ASCII "Get next". This is a THIRD distinct
trace, not the earlier ART GC or Binder/wake-lock abort. The text-valued pointer
suggests corruption but does not identify its producer. Thread-safety hardening
and verified native footprints did NOT resolve the Android crash.

The negative server-only trial and repeated positive native-capture trials increase
concern about this native path, but changing stacks still do not prove the exact
cause. Capture-only excludes Bluetooth, microphone substitution and simultaneous
mido Apps-server streaming as requirements for this latest failure.

## Safety actions

- Archived tombstone00, controller log, crash/audio metadata and matching BPF libraries
  on the PC; no voice recordings.
- Controller already exited. Removed its temporary binary/log/lock/PID directory.
- Set installed relay.conf RELAY_ENABLED=0; original module remains enabled with
  matching vendor/module bind inode66321:1183598 and original mixer SHA256.
- SELinux remains enforcing. No app actions, global audio-service restart, reboot,
  framework hooks or system-library edits were performed by the assistant.
- Disabled development autostart and changed the GitHub rc1 release to draft.
  Stable v1.0.0 remains available. No new replacement ZIP was installed/published.

## Offline follow-up

[Matching-ROM ABI/wire audit](offline-abi-audit.md) found no signature, layout or
serialization mismatch explaining the crashes. BPF disassembly identifies damaged
callback captures; matching StringPrintf/Status helpers use compatible layouts.
The first corrupting operation remains unresolved. This is not a fixed build.

The missing incoming-receiver-only baseline WITHOUT the controller should precede
another native trial. The earlier server-only baseline did not cover that path.
If justified afterward, separately isolate policy registration from patch transport;
do not repeat the same crash trial or add daemon/service restart loops.
Bluetooth/call validation is paused.
