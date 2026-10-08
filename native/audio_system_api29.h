// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <system/audio.h>
#include <system/audio_policy.h>
#include <utils/Errors.h>

// ABI-only declarations of static methods from Android 10 AudioSystem.h.
// No instances/layouts of AudioSystem are reproduced. These non-public APIs are
// deliberately restricted to the verified mido/API-29 ROM, not general Android.
namespace android {
class AudioSystem {
public:
    static void setErrorCallback(void (*callback)(status_t));
    static status_t setDeviceConnectionState(audio_devices_t, audio_policy_dev_state_t,
                                              const char*, const char*, audio_format_t);
    static status_t listAudioPorts(audio_port_role_t, audio_port_type_t,
                                   unsigned int*, audio_port*, unsigned int*);
    static status_t createAudioPatch(const audio_patch*, audio_patch_handle_t*);
    static status_t releaseAudioPatch(audio_patch_handle_t);
};
}
