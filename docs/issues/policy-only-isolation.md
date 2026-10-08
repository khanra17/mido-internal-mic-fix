# Policy-only isolation: prepared, not yet run

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
not Android stability. No binary has been installed or executed on the phone.
Rc1 stays withdrawn and native autostart remains disabled.

## Coordinated procedure (awaiting user readiness)

1. Save work. Keep mido's Apps server and Bluetooth off; disconnect its receiver.
   A policy-only test could still crash Android. Do not restart apps/services
   automatically or run the installed boot service.sh.
2. Recheck UID, supported hashes, absent controller/private policies and repair.
   Push only a temporary current binary, using the installed module's relay.lock
   to prevent duplicate controllers. Run policy-only with a15-minute timeout.
3. Ask the user to reconnect the working-phone microphone and disconnect/reconnect
   several times. Verify timestamped source START/STOP events, no PATCH creation
   and no virtual-mic advertisement. Do not arm or change the mode in place.
4. Stop via executable-identity-verified SIGTERM. Archive metadata and verify complete
   policy/device cleanup, original repair, service PIDs and tombstones. Remove only
   owned temporary test files. Do not re-enable autostart.

If this crashes, native patch transport is unnecessary for that failure; investigate
registration/routing/callback paths. If it does not, the patch becomes a narrower
suspect but is not proven causal. Any further transport trial requires a separate
bounded plan and user coordination, not an automatic next step. Bluetooth/call
switching remains deferred until crash behavior is understood and fixed.
