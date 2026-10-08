#!/system/bin/sh
# SPDX-License-Identifier: Apache-2.0
MODDIR=${0%/*}
[ -f "$MODDIR/relay.pid" ] || exit 0
read -r pid < "$MODDIR/relay.pid"
case "$pid" in ""|*[!0-9]*) exit 0 ;; esac
# Do not signal a recycled PID or an unrelated process.
[ "$(readlink "/proc/$pid/exe")" = "$MODDIR/bin/arm64-v8a/mido-relay-mic" ] || exit 0
kill -TERM "$pid" || exit 1
# Bounded uninstall-only wait; never a runtime polling supervisor.
tries=0
while [ "$(readlink "/proc/$pid/exe")" = "$MODDIR/bin/arm64-v8a/mido-relay-mic" ]; do
    tries=$((tries + 1))
    if [ "$tries" -ge 10 ]; then
        /system/bin/log -p e -t mido-internal-mic-fix "Controller did not finish teardown; reboot required."
        exit 1
    fi
    sleep 1
done
rm -f "$MODDIR/relay.pid"
