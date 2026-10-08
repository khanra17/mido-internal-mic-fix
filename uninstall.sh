#!/system/bin/sh
# SPDX-License-Identifier: Apache-2.0
MODDIR=${0%/*}
[ -f "$MODDIR/relay.pid" ] || exit 0
read -r pid < "$MODDIR/relay.pid"
case "$pid" in ""|*[!0-9]*) exit 0 ;; esac
# Do not signal a recycled PID or an unrelated process.
[ "$(readlink "/proc/$pid/exe")" = "$MODDIR/bin/arm64-v8a/mido-relay-mic" ] || exit 0
kill -TERM "$pid"
