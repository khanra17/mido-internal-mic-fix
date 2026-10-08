# Policy-only isolation: idle phase checked, active phase pending

## Receiver-only baseline after reboot

The user rebooted independently, kept native control disabled, received the working
phone's microphone and disconnected/reconnected multiple times without a crash.
Read-only inspection at20:55 IST on2026-10-08 found:

- `RELAY_ENABLED=0`, no controller process and no addressed private policies.
- system_server1369, audioserver587; uptime approximately3h17m.
- Latest tombstone remains the16:09 crash from before reboot. No new system_server
  crash in the crash buffer; separate Calendar/YouTube app exceptions are present.
- Original mixer SHA256 and matching bind/module inode unchanged; SELinux enforcing.

This is a negative receiver-only baseline, not a verified crash fix. Reboot cleared
prior process state, so it is not an otherwise identical comparison with the
previous native trial. Both receiver-only and Apps-server-only baselines have now
been tried without native control and reported no Android crash.

## First attempt: reconnects occurred after timeout

The temporary controller ran from21:12:27 to21:27:28 IST, then timed out and
reported `CLEANUP_COMPLETE`. No source START/STOP or POLICY_ONLY_ACTIVITY was
observed. Both private outputs disconnected and both policies unregistered.

PlaybackActivityMonitor records AudioRelay's three cycles at21:37:42–21:37:56,
21:38:03–21:38:09 and21:38:16–21:38:23. They occurred AFTER the controller exited.
The user reported no crash; service PIDs1369/587 and latest tombstone remained
unchanged. Original repair and enforcing SELinux remained intact. Temporary test
files were removed after archiving metadata.

This verifies idle registration/timeout/teardown for this attempt, NOT active
policy callbacks/reconnect stability. Do not narrow the cause to patch transport
on this result. Repeat needs actual source events while the controller is alive;
a30-minute event-loop limit will give the user more time.

## New diagnostic mode

`--policy-only --timeout SECONDS` (1…1800) registers the same UID-isolated source
and unused-UID dummy policies, connects their outputs and observes source callbacks.
It stops BEFORE controller patch creation, port lookup or microphone registration.
The immutable Bridge guard blocks transport even if SIGUSR1 is received; main also
ignores arming in this mode. A timeout is mandatory; malformed or overflowing
integer arguments are rejected. Boot startup does not use it. The deadline starts
before policy registration, but synchronous Binder operations and cleanup can
block beyond it: this is an event-loop limit, NOT a guaranteed process-lifetime
bound. Manual executable-identity-verified termination remains necessary if stuck.

Normal playback routing created by Android can still exist; "no patch" here means
no controller-created device-to-device PatchRecord/PatchTrack bridge. Incoming
receiver playback may become silent because its private loopback has no reader.
The upper mic remains the microphone. This is NOT a remote-mic or Bluetooth test.

Build and20 host tests passed. Those tests check source guards/build artifacts,
not Android stability. Only a temporary test binary was executed; the installed
module binary was not changed. Rc1 stays withdrawn and native autostart remains
disabled.

## Coordinated repeat (awaiting user readiness)

1. Save work. Keep mido's Apps server and Bluetooth off; disconnect its receiver.
   A policy-only test could still crash Android. Do not restart apps/services
   automatically or run the installed boot service.sh.
2. Recheck UID, supported hashes, absent controller/private policies and repair.
   Push only a temporary current binary, using the installed module's relay.lock
   to prevent duplicate controllers. Run policy-only with a30-minute event-loop
   timeout, then ask the user to reconnect promptly. Do not confuse this with a
   hard deadline on synchronous Binder calls.
3. Ask the user to reconnect the working-phone microphone and disconnect/reconnect
   several times. Verify timestamped source START/STOP events, no PATCH creation
   and no virtual-mic advertisement. Do not arm or change the mode in place.
4. Stop via executable-identity-verified SIGTERM. Archive metadata and verify complete
   policy/device cleanup, original repair, service PIDs and tombstones. Remove only
   owned temporary test files. Do not re-enable autostart.

If an ACTIVE policy-only trial crashes, native patch transport is unnecessary for
that failure; investigate registration/routing/callback paths. If source START/STOP
is verified while alive and it does not crash, the patch becomes a narrower suspect
but is not proven causal. Idle-only or post-timeout cycles cannot establish this. Any further transport trial requires a separate
bounded plan and user coordination, not an automatic next step. Bluetooth/call
switching remains deferred until crash behavior is understood and fixed.
