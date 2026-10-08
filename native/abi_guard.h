// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <sys/wait.h>
#include <unistd.h>

// The ROM has custom AIDL ordinals; API level/device alone are insufficient.
// Reject any unverified framework/library ABI BEFORE making Binder calls.
// One sha256sum child at startup; no ongoing shell processes or file polling.
inline bool verifiedAudioAbi() {
    static const char* const expected[] = {
        "110e15591fe5cf338da64a00e0fcd1a08d3c9a42bda99dc9fd6c1c0793119d5a  /system/framework/framework.jar",
        "41e15eda6629dcecaed755ecbdb53f011a65b4e6859d40dc3a457c1deee4c919  /system/lib64/libaudioclient.so",
        "d935de4e1bbb2b78e4110107f6ffdf7331ba39c6ef9bdf67c328534105c96973  /system/lib64/libbinder.so",
        "f62297af2a356a6d5e14ad7b9b78f064b564dc348d2c19644dc9b51040b846c8  /system/lib64/libutils.so",
    };
    int pipeFds[2];
    if (pipe(pipeFds) != 0) return false;
    const pid_t child = fork();
    if (child == 0) {
        close(pipeFds[0]);
        if (dup2(pipeFds[1], STDOUT_FILENO) < 0) _exit(126);
        close(pipeFds[1]);
        execl("/system/bin/sha256sum", "sha256sum", "/system/framework/framework.jar",
              "/system/lib64/libaudioclient.so", "/system/lib64/libbinder.so",
              "/system/lib64/libutils.so", static_cast<char*>(nullptr));
        _exit(127);
    }
    close(pipeFds[1]);
    if (child < 0) { close(pipeFds[0]); return false; }
    char result[1024]{};
    size_t length = 0;
    while (length < sizeof(result) - 1) {
        const ssize_t count = read(pipeFds[0], result + length, sizeof(result) - 1 - length);
        if (count > 0) length += count;
        else if (count == 0) break;
        else if (errno != EINTR) break;
    }
    close(pipeFds[0]);
    int status = 0;
    pid_t waited;
    do { waited = waitpid(child, &status, 0); } while (waited < 0 && errno == EINTR);
    if (waited != child || !WIFEXITED(status) || WEXITSTATUS(status) != 0) return false;
    const char* cursor = result;
    for (const char* line : expected) {
        const size_t size = strlen(line);
        if (strncmp(cursor, line, size) != 0 || cursor[size] != '\n') return false;
        cursor += size + 1;
    }
    return *cursor == '\0';
}
