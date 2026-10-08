// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <binder/Parcel.h>
#include "abi_layouts.h"
#include <utils/String8.h>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <new>

// Local serialization only. No service lookup, policy, patch, audio capture,
// Bluetooth, or Android audio-service restart is involved.
inline int abiSelfTest() {
    constexpr uint64_t marker = UINT64_C(0x6d69646f41424931);
    struct Frame {
        uint64_t before;
        alignas(android::Parcel) unsigned char bytes[sizeof(android::Parcel)];
        uint64_t after;
    } frame{marker, {}, marker};
    auto intact = [&]() { return frame.before == marker && frame.after == marker; };
    auto* parcel = new (frame.bytes) android::Parcel;
    if (!intact()) { fprintf(stderr, "ABI_SELF_TEST_FAILED constructor bounds\n"); return 1; }
    constexpr int32_t value = 0x12345678;
    constexpr char message[] = "mido-local-parcel-roundtrip";
    bool ok = parcel->writeInt32(value) == android::NO_ERROR &&
              parcel->writeString16(android::String16(message)) == android::NO_ERROR;
    parcel->setDataPosition(0);
    int32_t actual = 0;
    ok = ok && parcel->readInt32(&actual) == android::NO_ERROR && actual == value;
    if (ok) {
        const android::String8 decoded(parcel->readString16());
        ok = strcmp(decoded.c_str(), message) == 0;
    }
    ok = ok && intact();
    parcel->~Parcel();
    ok = ok && intact();
    fprintf(stderr, ok ? "ABI_SELF_TEST_OK parcel=120 alignment=8 roundtrip=ok guards=ok\n"
                       : "ABI_SELF_TEST_FAILED serialization/destructor bounds\n");
    return ok ? 0 : 1;
}
