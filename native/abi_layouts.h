// SPDX-License-Identifier: Apache-2.0
#pragma once
#include "audio_system_api29.h"
#include <binder/Binder.h>
#include <binder/Parcel.h>
#include <utils/String16.h>
#include <utils/String8.h>
#include <cstddef>

// Verified compiler layouts plus matching ROM constructor/marshalling evidence.
// Hashes establish library identity, not layout compatibility by themselves.
namespace android {
static_assert(sizeof(Parcel) == 120 && alignof(Parcel) == 8, "Parcel ABI mismatch");
static_assert(sizeof(RefBase) == 16 && alignof(RefBase) == 8, "RefBase ABI mismatch");
static_assert(sizeof(IBinder) == 24 && alignof(IBinder) == 8, "IBinder ABI mismatch");
static_assert(sizeof(BBinder) == 40 && alignof(BBinder) == 8, "BBinder ABI mismatch");
static_assert(sizeof(IBinder::DeathRecipient) == 24, "DeathRecipient ABI mismatch");
static_assert(sizeof(String8) == 8 && sizeof(String16) == 8, "String ABI mismatch");
}
static_assert(sizeof(audio_port_config) == 216 && alignof(audio_port_config) == 4, "port config ABI mismatch");
static_assert(sizeof(audio_port) == 1308 && alignof(audio_port) == 4, "audio port ABI mismatch");
static_assert(sizeof(audio_patch) == 6924 && alignof(audio_patch) == 4, "audio patch ABI mismatch");
static_assert(offsetof(audio_port, active_config) == 1052, "active config offset mismatch");
static_assert(offsetof(audio_port, ext.device) == 1268, "port device offset mismatch");
static_assert(offsetof(audio_port_config, ext.device.address) == 184, "device address offset mismatch");
static_assert(sizeof(audio_port_config{}.ext.device.address) == 32, "address extent mismatch");
static_assert(offsetof(audio_patch, sources) == 8 && offsetof(audio_patch, num_sinks) == 3464 &&
              offsetof(audio_patch, sinks) == 3468, "patch array offset mismatch");
