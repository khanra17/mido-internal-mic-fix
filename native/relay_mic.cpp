// SPDX-License-Identifier: Apache-2.0
// Native control plane only: all PCM stays inside audioserver's PatchRecord/Track.
#include "audio_system_api29.h"
#include "abi_guard.h"
#include <binder/Binder.h>
#include <binder/IServiceManager.h>
#include <binder/Parcel.h>
#include <binder/ProcessState.h>
#include <utils/String16.h>
#include <utils/String8.h>
#include <atomic>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <poll.h>
#include <time.h>
#include <signal.h>
#include <sys/eventfd.h>
#include <sys/file.h>
#include <sys/system_properties.h>
#include <unistd.h>

using namespace android;
namespace {
// Verified from THIS qassa ROM's IAudioService.Stub fields (not generic AOSP's
// ordinal numbering). Boot script must verify framework/library SHA-256 first.
constexpr int kRegister = 72;
constexpr int kUnregister = 74;  // Synchronous; never use async teardown here.
constexpr int kNotifyMixState = 5;
constexpr int kMatchUsage = 1, kMatchPreset = 2, kMatchUid = 4;
constexpr int kLoopBackOnly = 2; // NOT LOOP_BACK_AND_RENDER (no speaker copy).
const String16 kServiceToken("android.media.IAudioService");
const String16 kCallbackToken("android.media.audiopolicy.IAudioPolicyCallback");
std::atomic<int> desiredState{0};
volatile sig_atomic_t stopping = 0, armed = 1;
int wakeFd = -1;

void wake() {
    const uint64_t value = 1;
    if (wakeFd >= 0) (void)write(wakeFd, &value, sizeof(value));
}
void signalHandler(int signal) {
    const int saved = errno;
    if (signal == SIGUSR1) armed = 1;
    else stopping = 1;
    wake();
    errno = saved;
}

void audioError(status_t error) {
    if (error == DEAD_OBJECT) { stopping = 1; wake(); }
}
int64_t monotonicMs() {
    timespec now{};
    clock_gettime(CLOCK_MONOTONIC, &now);
    return static_cast<int64_t>(now.tv_sec) * 1000 + now.tv_nsec / 1000000;
}
class ServiceDeath final : public IBinder::DeathRecipient {
    void binderDied(const wp<IBinder>&) override { stopping = 1; wake(); }
};

class PolicyCallback final : public BBinder {
public:
    explicit PolicyCallback(bool source) : source_(source) {}
    const String16& getInterfaceDescriptor() const override { return kCallbackToken; }
protected:
    status_t onTransact(uint32_t code, const Parcel& data, Parcel* reply,
                        uint32_t flags = 0) override {
        if (code != kNotifyMixState) return BBinder::onTransact(code, data, reply, flags);
        if (!data.enforceInterface(kCallbackToken)) return PERMISSION_DENIED;
        const String16 registration = data.readString16();
        int32_t state = -1;
        if (data.readInt32(&state) != NO_ERROR || (state != 0 && state != 1)) return BAD_VALUE;
        if (source_) {
            // This callback belongs to one source policy/mix only. No app/UID polling.
            fprintf(stderr, "SOURCE_ACTIVITY address=%s state=%d\n", String8(registration).c_str(), state);
            desiredState.store(state, std::memory_order_release);
            wake();
        }
        return NO_ERROR;
    }
private:
    bool source_;
};

struct Policy {
    sp<PolicyCallback> callback;
    String8 address;
    bool registered = false;
};

// Serialize exactly AudioPolicyConfig.writeToParcel() from Android 10, NOT the
// native AudioMix parcel. System_server owns the proxy and unregisters it on
// this callback Binder's death, ensuring virtual-input fallback after a crash.
status_t registerPolicy(const sp<IBinder>& service, Policy& policy, int uid, bool microphone) {
    policy.callback = new PolicyCallback(!microphone && uid != 65534);
    Parcel request, response;
    request.writeInterfaceToken(kServiceToken);
    request.writeInt32(1); // Non-null Parcelable AudioPolicyConfig.
    request.writeInt32(1); // One mix, separate source/microphone registrations.
    request.writeInt32(kLoopBackOnly);
    request.writeInt32(!microphone && uid != 65534 ? 1 : 0); // Notify activity.
    request.writeInt32(microphone ? AUDIO_DEVICE_IN_REMOTE_SUBMIX : AUDIO_DEVICE_OUT_REMOTE_SUBMIX);
    request.writeString16(String16(""));
    request.writeInt32(48000);
    request.writeInt32(2);  // Java ENCODING_PCM_16BIT.
    request.writeInt32(12); // Java CHANNEL_OUT_STEREO; AudioMix normalizes directions.
    request.writeInt32(0);  // Respect playback capture restrictions; no privileged opt-out bypass.
    if (microphone) {
        constexpr int presets[] = {1, 5, 6, 7, 9}; // Deliberately exclude REMOTE_SUBMIX (8).
        request.writeInt32(sizeof(presets) / sizeof(presets[0]));
        for (int preset : presets) { request.writeInt32(kMatchPreset); request.writeInt32(preset); }
    } else {
        request.writeInt32(uid == 65534 ? 1 : 2);
        request.writeInt32(kMatchUid); request.writeInt32(uid);
        if (uid != 65534) { request.writeInt32(kMatchUsage); request.writeInt32(1); } // MEDIA only.
    }
    request.writeStrongBinder(policy.callback);
    for (int i = 0; i != 4; ++i) request.writeInt32(0); // No focus listener/policy/volume policy.
    request.writeStrongBinder(nullptr); // No MediaProjection.
    status_t status = service->transact(kRegister, request, &response);
    if (status != NO_ERROR) return status;
    if (response.readExceptionCode() != 0) return PERMISSION_DENIED;
    const String8 registration(response.readString16());
    if (!registration.length()) return INVALID_OPERATION;
    policy.registered = true;
    char address[AUDIO_DEVICE_MAX_ADDRESS_LEN];
    const int written = snprintf(address, sizeof(address), "%smix%c:0", registration.c_str(),
                                 microphone ? 'r' : 'p');
    if (written < 0 || static_cast<size_t>(written) >= sizeof(address)) return BAD_VALUE;
    policy.address = String8(address);
    fprintf(stderr, "POLICY_REGISTERED %s\n", address);
    return NO_ERROR;
}

status_t unregisterPolicy(const sp<IBinder>& service, Policy& policy) {
    if (!policy.registered) return NO_ERROR;
    Parcel request, response;
    request.writeInterfaceToken(kServiceToken);
    request.writeStrongBinder(policy.callback);
    const status_t status = service->transact(kUnregister, request, &response);
    if (status == NO_ERROR && response.readExceptionCode() == 0) {
        policy.registered = false;
        fprintf(stderr, "POLICY_UNREGISTERED %s\n", policy.address.c_str());
        return NO_ERROR;
    }
    return status == NO_ERROR ? INVALID_OPERATION : status;
}

status_t connect(audio_devices_t type, const String8& address, bool available) {
    const status_t status = AudioSystem::setDeviceConnectionState(type,
        available ? AUDIO_POLICY_DEVICE_STATE_AVAILABLE : AUDIO_POLICY_DEVICE_STATE_UNAVAILABLE,
        address.c_str(), "mido-relay-private", AUDIO_FORMAT_DEFAULT);
    fprintf(stderr, "PRIVATE_DEVICE type=%#x address=%s available=%d status=%d\n",
             type, address.c_str(), available, status);
    return status;
}

status_t findDevice(audio_devices_t type, const String8& address, audio_port& result) {
    // A bounded retry handles concurrent policy generation changes, not a polling daemon.
    for (int attempt = 0; attempt != 3; ++attempt) {
        unsigned count = 0, before = 0, after = 0;
        status_t status = AudioSystem::listAudioPorts(AUDIO_PORT_ROLE_NONE,
            AUDIO_PORT_TYPE_DEVICE, &count, nullptr, &before);
        if (status != NO_ERROR || count > 256) return status == NO_ERROR ? BAD_VALUE : status;
        const unsigned capacity = count;
        audio_port* ports = static_cast<audio_port*>(calloc(count ? count : 1, sizeof(audio_port)));
        if (!ports) return NO_MEMORY;
        status = AudioSystem::listAudioPorts(AUDIO_PORT_ROLE_NONE,
            AUDIO_PORT_TYPE_DEVICE, &count, ports, &after);
        if (status == NO_ERROR && before == after && count <= capacity) {
            for (unsigned i = 0; i < count; ++i) {
                if (ports[i].type == AUDIO_PORT_TYPE_DEVICE && ports[i].ext.device.type == type &&
                    strcmp(ports[i].ext.device.address, address.c_str()) == 0) {
                    result = ports[i]; free(ports); return NO_ERROR;
                }
            }
            free(ports); return NAME_NOT_FOUND;
        }
        free(ports);
        if (status != NO_ERROR) return status;
    }
    return WOULD_BLOCK;
}

audio_port_config config(const audio_port& port, bool input) {
    audio_port_config result = port.active_config;
    result.id = port.id; result.role = port.role; result.type = AUDIO_PORT_TYPE_DEVICE;
    result.ext.device.hw_module = port.ext.device.hw_module;
    result.ext.device.type = port.ext.device.type;
    memcpy(result.ext.device.address, port.ext.device.address, sizeof(result.ext.device.address));
    result.config_mask = AUDIO_PORT_CONFIG_SAMPLE_RATE | AUDIO_PORT_CONFIG_CHANNEL_MASK |
                         AUDIO_PORT_CONFIG_FORMAT;
    result.sample_rate = 48000;
    result.channel_mask = input ? AUDIO_CHANNEL_IN_STEREO : AUDIO_CHANNEL_OUT_STEREO;
    result.format = AUDIO_FORMAT_PCM_16_BIT;
    return result;
}

class Bridge {
public:
    sp<IBinder> service;
    sp<ServiceDeath> serviceDeath;
    Policy source, microphone, dummy;
    audio_patch_handle_t patch = AUDIO_PATCH_HANDLE_NONE;
    bool sourceConnected = false, microphoneConnected = false, dummyConnected = false;

    status_t start(int uid, bool captureOnly) {
        service = defaultServiceManager()->checkService(String16("audio"));
        if (!service) return NAME_NOT_FOUND;
        serviceDeath = new ServiceDeath;
        (void)service->linkToDeath(serviceDeath);
        AudioSystem::setErrorCallback(audioError);
        status_t status = registerPolicy(service, source, uid, false);
        if (status != NO_ERROR) return status;
        status = connect(AUDIO_DEVICE_OUT_REMOTE_SUBMIX, source.address, true);
        if (status != NO_ERROR) return status;
        sourceConnected = true;
        if (captureOnly) {
            status = registerPolicy(service, dummy, 65534, false);
            if (status != NO_ERROR) return status;
            status = connect(AUDIO_DEVICE_OUT_REMOTE_SUBMIX, dummy.address, true);
            if (status != NO_ERROR) return status;
            dummyConnected = true;
        }
        fprintf(stderr, "READY source=%s captureOnly=%d; reconnect an already-playing client\n",
                source.address.c_str(), captureOnly);
        return NO_ERROR;
    }

    status_t route(bool remoteMicrophone) {
        if (remoteMicrophone && microphoneConnected) return NO_ERROR;
        Policy* sink = &dummy;
        status_t status = NO_ERROR;
        if (remoteMicrophone) {
            status = registerPolicy(service, microphone, 0, true);
            if (status != NO_ERROR) return status;
            sink = &microphone;
        }
        audio_port sourcePort{}, sinkPort{};
        status = findDevice(AUDIO_DEVICE_IN_REMOTE_SUBMIX, source.address, sourcePort);
        if (status != NO_ERROR) return status;
        status = findDevice(AUDIO_DEVICE_OUT_REMOTE_SUBMIX, sink->address, sinkPort);
        if (status != NO_ERROR) return status;
        audio_patch connection{};
        connection.num_sources = 1; connection.sources[0] = config(sourcePort, true);
        connection.num_sinks = 1; connection.sinks[0] = config(sinkPort, false);
        status = AudioSystem::createAudioPatch(&connection, &patch);
        fprintf(stderr, "PATCH destination=%s handle=%d status=%d\n", sink->address.c_str(), patch, status);
        if (status != NO_ERROR) return status;
        if (remoteMicrophone) {
            // Internal PatchTrack bypasses startOutput()/startSource(): explicitly
            // advertise its exact matching virtual input, AFTER patch success.
            status = connect(AUDIO_DEVICE_IN_REMOTE_SUBMIX, microphone.address, true);
            if (status != NO_ERROR) return status;
            microphoneConnected = true;
            audio_port verify{};
            status = findDevice(AUDIO_DEVICE_IN_REMOTE_SUBMIX, microphone.address, verify);
            if (status != NO_ERROR) return status;
            fprintf(stderr, "REMOTE_MIC_ENABLED %s\n", microphone.address.c_str());
        } else fprintf(stderr, "CAPTURE_CONTROL_ACTIVE\n");
        return NO_ERROR;
    }

    status_t fallback() {
        status_t result = NO_ERROR;
        // Preserve failed resource handles so final cleanup can retry. Never
        // resume routing after a teardown error or report false success.
        if (microphoneConnected) {
            const status_t status = connect(AUDIO_DEVICE_IN_REMOTE_SUBMIX, microphone.address, false);
            if (status == NO_ERROR) microphoneConnected = false;
            else result = status;
        }
        if (patch != AUDIO_PATCH_HANDLE_NONE) {
            const status_t status = AudioSystem::releaseAudioPatch(patch);
            fprintf(stderr, "PATCH_RELEASE handle=%d status=%d\n", patch, status);
            if (status == NO_ERROR) patch = AUDIO_PATCH_HANDLE_NONE;
            else if (result == NO_ERROR) result = status;
        }
        const status_t status = unregisterPolicy(service, microphone);
        if (status != NO_ERROR && result == NO_ERROR) result = status;
        if (result == NO_ERROR) fprintf(stderr, "UPPER_MIC_FALLBACK\n");
        else fprintf(stderr, "FALLBACK_ERROR status=%d\n", result);
        return result;
    }
    status_t cleanup() {
        if (!service) return NO_ERROR;
        status_t result = fallback();
        if (dummyConnected) {
            const status_t status = connect(AUDIO_DEVICE_OUT_REMOTE_SUBMIX, dummy.address, false);
            if (status == NO_ERROR) dummyConnected = false;
            else if (result == NO_ERROR) result = status;
        }
        if (sourceConnected) {
            const status_t status = connect(AUDIO_DEVICE_OUT_REMOTE_SUBMIX, source.address, false);
            if (status == NO_ERROR) sourceConnected = false;
            else if (result == NO_ERROR) result = status;
        }
        for (Policy* policy : {&dummy, &source}) {
            const status_t status = unregisterPolicy(service, *policy);
            if (status != NO_ERROR && result == NO_ERROR) result = status;
        }
        if (result == NO_ERROR) fprintf(stderr, "CLEANUP_COMPLETE\n");
        else fprintf(stderr, "CLEANUP_INCOMPLETE status=%d; Binder death will remove owned policies\n", result);
        return result;
    }
};
}

int main(int argc, char** argv) {
    setvbuf(stderr, nullptr, _IOLBF, 0);
    bool captureOnly = false;
    int uid = -1;
    int timeoutSeconds = 0;
    const char* lockPath = "/data/local/tmp/mido-relay-native.lock";
    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--capture-only") == 0) captureOnly = true;
        else if (strcmp(argv[i], "--uid") == 0 && ++i < argc) uid = atoi(argv[i]);
        else if (strcmp(argv[i], "--lock") == 0 && ++i < argc) lockPath = argv[i];
        else if (strcmp(argv[i], "--timeout") == 0 && ++i < argc) timeoutSeconds = atoi(argv[i]);
        else { fprintf(stderr, "Usage: %s --uid APP_UID [--capture-only] [--lock PATH] [--timeout SECONDS]\n", argv[0]); return 2; }
    }
    char property[PROP_VALUE_MAX]{};
    __system_property_get("ro.product.device", property);
    if (strcmp(property, "mido") != 0) return 2;
    __system_property_get("ro.build.version.sdk", property);
    if (strcmp(property, "29") != 0 || getuid() != 0 || uid < 10000) return 2;
    if (!verifiedAudioAbi()) {
        fprintf(stderr, "UNSUPPORTED_AUDIO_ABI: leave repaired upper mic selected\n");
        return 2;
    }
    const int lock = open(lockPath, O_CREAT | O_RDWR | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (lock < 0 || flock(lock, LOCK_EX | LOCK_NB) != 0) return 3;
    wakeFd = eventfd(0, EFD_CLOEXEC | EFD_NONBLOCK);
    if (wakeFd < 0) return 3;
    armed = !captureOnly;
    struct sigaction action{};
    action.sa_handler = signalHandler;
    sigemptyset(&action.sa_mask);
    for (int signal : {SIGINT, SIGTERM, SIGHUP, SIGUSR1}) sigaction(signal, &action, nullptr);
    // Binder callbacks wake poll(); no Java VM, focus manipulation, app recorder,
    // ongoing dumpsys/package queries, PCM copying, or periodic activity polling.
    ProcessState::self()->startThreadPool();
    Bridge bridge;
    status_t status = bridge.start(uid, captureOnly);
    bool active = false, remote = false;
    const int64_t deadline = timeoutSeconds > 0 ? monotonicMs() + timeoutSeconds * 1000LL : 0;
    while (status == NO_ERROR && !stopping && (!deadline || monotonicMs() < deadline)) {
        const bool desired = desiredState.load(std::memory_order_acquire) == 1;
        const bool wantRemote = armed != 0;
        if (desired && (!active || remote != wantRemote)) {
            status = bridge.route(wantRemote);
            active = status == NO_ERROR; remote = wantRemote;
        } else if (!desired && active) { status = bridge.fallback(); active = false; }
        if (status != NO_ERROR || stopping) break;
        pollfd event{wakeFd, POLLIN, 0};
        const int waitMs = deadline ? static_cast<int>(deadline - monotonicMs()) : -1;
        if (waitMs <= 0 && deadline) break;
        if (poll(&event, 1, waitMs) < 0 && errno != EINTR) { status = -errno; break; }
        uint64_t count;
        while (read(wakeFd, &count, sizeof(count)) == sizeof(count)) {}
    }
    if (status != NO_ERROR) fprintf(stderr, "ERROR status=%d; restoring upper mic\n", status);
    const status_t cleanupStatus = bridge.cleanup();
    if (status == NO_ERROR) status = cleanupStatus;
    // Do not destroy Binder globals under still-running Binder pool threads.
    // Kernel closes all descriptors/Binder refs; policies have been removed above.
    _exit(status == NO_ERROR ? 0 : 1);
}
