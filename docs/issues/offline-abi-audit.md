# Offline crash audit, 2026-10-08

This audit found no verified crash fix. Native autostart remains disabled; rc1
remains withdrawn. Bluetooth and ongoing-call switching are still deferred.

## Controller and matching ROM

The following checks use the actual pinned ROM libraries/framework.jar, not only
AOSP headers. Framework SHA256 is the value required by native/abi_guard.h.

| Boundary | Result |
| --- | --- |
| Parcel construction/destruction | 120-byte object including mOpenAshmemSize at0x70; ROM store atlibbinder0x60ee0 is in bounds. Previous112-byte claim was false. |
| BBinder derived-class dispatch | ROM transact calls vtable+0x80, matching PolicyCallback.onTransact. Virtual RefBase displacement is obtained from the object's vtable. |
| AudioSystem methods | Inspected exports/signatures agree; audio_patch6924 bytes, audio_port1308 bytes. |
| ROM policy config serialization | classes2.dex writeToParcel code_off0x1fb2b8 and Parcel constructor0x1faf0c match the controller's fields. |
| Register/unregister decoding | Stub.onTransact code_off0x1b5df8 confirms register72, async-unregister73, sync-unregister74 and four boolean integers. |
| Criteria/boolean representation | Rule/value integer pairs for usage1,preset2,UID4; writeBoolean uses writeInt. |

The config order is mix count, route flags, callback flags, device type/address,
sample rate, encoding, channel mask, privileged-capture boolean, rule count,
rule/value pairs. Register wraps it in a presence integer, then callback Binder,
four false boolean integers and null MediaProjection Binder. Reply shape agrees.
No complete-object/vtable/signature/wire-order mismatch was found at these
boundaries. This does not prove server-side PatchPanel, HAL or kernel behavior.

Parcel write return values are not currently all checked. This is a robustness
gap under allocation failure, not an observed malformed request or confirmed
cause. Do not present an allocation-check change as the crash fix.

## Network-statistics failure

Matching libnetdbpf disassembly shows a40-byte allocated std::function target.
At0x4d04/0x4d08, its map-reference capture at+0x18 and unknown-byte-total reference
at+0x20 are loaded. At the crash they contain ASCII "Get next" and " key of ",
respectively. The invalid map reference reaches libbpf_android0x5328, which faults
on ldr w8,[x0] BEFORE the lookup syscall. The corruption precedes the reported
faulting operation.

The terminal next-key ENOENT error is formatted before processing the last current
key. That is normal Android10 BpfMap.iterate ordering, not by itself an iterator
bug. The final stack includes plausible long-string words with a data pointer
0x707dafd768, equal to the callable address0x707dafd750 plus0x18. However, that
pointer ends in8, unlike ordinary16-byte-aligned ARM64 malloc/new returns.
Residual stack contents do NOT prove two valid allocations overlapped or identify
the first invalid write. The damaged capture fields are the reliable finding.

Matching helper implementations agree with their callers:

- libbase StringPrintf0xf4c8 takes its24-byte string result through x8 and zeroes
  all24 bytes before calling StringAppendV. The30-character error uses its normal
  1024-byte local formatting buffer and string.append.
- libnetdutils statusFromErrno0xe82c reads the normal24-byte string layout, returns
  through x8 and writes the expected32-byte Status (code at0, string at8).
- Matching libc++ string append preserves the allocation pointer unmodified.
- No alternate-string-layout or hidden-result mismatch was demonstrated. Relevant
  resolved libnetdbpf GOT targets point to expected libraries. The final tombstone
  does not include all helper-internal runtime PLT targets or preceding heap state.

Read-only fdinfo metadata found iface-compatible map dimensions: key4/value16
and key4/value32 (1000entries). Those descriptors are not definitively bound to
pin names by this output; it is not a complete map-validation result. No map
values, UID counters or traffic contents were collected.

## Next distinguishing check

The earlier no-crash baseline exercised AudioRelay's Apps SERVER without native
routing. The user subsequently rebooted and performed the missing RECEIVER-only
comparison, including multiple disconnects/reconnects, without a crash. Read-only
inspection confirmed native control stayed disabled and no new system_server
tombstone appeared. The reboot changed process state, so this is not an otherwise
identical comparison. See [policy-only isolation](policy-only-isolation.md) for
results and the next prepared diagnostic.

The negative baseline does not establish controller causation. Policy registration
and patch transport now need separate bounded, coordinated tests. Do not add a
restart supervisor or change assistant roles/privacy/SELinux/system libraries
in place of identifying the producer.

At16:49IST read-only library collection: system_server17753/audioserver17530
unchanged, RELAY_ENABLED=0. No new native routing was launched or binary installed.
