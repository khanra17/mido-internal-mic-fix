# Rc1 post-install report (2026-10-08)

## Confirmed by the user after install/reboot

- With AudioRelay disconnected, Gboard heard mido's upper mic.
- With the working phone's microphone streamed into mido, Gboard heard that remote mic.
- Starting mido's AudioRelay Apps server while receiving the remote mic, then
  connecting the working phone as its client, returned the same microphone audio
  to the working phone. **This full-duplex configuration is currently unsupported.**
- Stopping that server coincided with black-screen/UI recovery. Later reconnects
  no longer replaced the physical mic.

## Collected evidence

`relay.log` shows two successful REMOTE_MIC_ENABLED transitions (private ap1/ap3),
with status=0 for patches/input activation. Between them one normal source-idle
fallback disconnected the mic input, released patch 42 and unregistered its policy
successfully. Later teardown had DEAD_OBJECT (-32); the controller exited.
No controller process/private policy remained when inspected. Installed mixer
hash/mount intact and SELinux enforcing.

At 13:11:25 IST, tombstone_09 shows system_server SIGABRT, UBSAN divrem-overflow:
VectorImpl::_shrink -> BpBinder::unlinkToDeath -> PowerManagerService wake-lock
release. This is a DIFFERENT trace from the earlier 11:12 ART/JIT GC SIGSEGV.
It proves a framework crash, not why its vector arithmetic was invalid or that
our daemon caused it. Native code does not make PowerManager/wake-lock calls.

The daemon intentionally does not auto-restart after service death. Thus subsequent
AudioRelay client reconnection cannot reactivate policies after it exits. A controlled
controller restart/new receiver track is needed before further microphone tests;
no HAL/audio-service/app restart or library patch has been performed.

## Echo finding

Android 10 AudioPolicyMixCollection::getOutputForAttr separately selects a primary
LOOP_BACK route and secondary LOOP_BACK|RENDER playback-capture routes. Diverting the
AudioRelay incoming track from the speaker does NOT prevent another Apps capture
mix from receiving a secondary copy. Incoming UID isolation protects the mic from
other playback; it does not itself exclude incoming audio from outgoing capture.
An outgoing capture UID exclusion is needed for reliable full duplex.

Do NOT add a broad output-as-microphone fallback, privacy bypass, UID impersonation,
or edit system libraries to address this. AOSP setAllowedCapturePolicy requires the
calling UID to equal the affected UID; a root daemon cannot simply set another app's
policy through that API. Leave mido's Apps server off for isolated mic/call testing.

## Pending

- Safest offline crash diagnostic: disassemble matching libutils BuildId to identify
  the divisor/guard at _shrink's UBSAN failure; do not assume corruption versus ROM bug.
- Isolated controller recovery, then Telegram test without mido's Apps server.
- Robust crash/recovery handling after root cause review; outgoing UID exclusion.
- No updated binary/release or installed-module config was changed during inspection.
