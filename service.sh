#!/system/bin/sh
# SPDX-License-Identifier: Apache-2.0
MODDIR=${0%/*}
. "$MODDIR/common.sh"
module_ready && our_mount_active || exit 0

refresh_hal() {
    [ "$(/system/bin/getprop init.svc.vendor.audio-hal-2-0)" = running ] || return 0
    # Preserve the original boot-only refresh, never during an active call.
    phone_state=$(/system/bin/dumpsys -t 2 media.audio_policy 2>/dev/null |
        grep 'Phone state:') || return 0
    case "$phone_state" in
        *AUDIO_MODE_NORMAL*)
            /system/bin/setprop ctl.restart vendor.audio-hal-2-0 ||
                report_error "Could not refresh the audio HAL; reboot with the module enabled."
            ;;
    esac
}
refresh_hal

# Development safety gate: do not activate the unvalidated native path at boot.
# No daemon or ongoing shell loop is started when this is disabled.
RELAY_ENABLED=0
[ -f "$MODDIR/relay.conf" ] && . "$MODDIR/relay.conf"
[ "$RELAY_ENABLED" = 1 ] || exit 0

# Bounded, boot-only wait for PackageManager. Native runtime is event driven.
tries=0
while [ "$(/system/bin/getprop sys.boot_completed)" != 1 ]; do
    tries=$((tries + 1))
    [ "$tries" -lt 60 ] || exit 0
    sleep 2
done
relay_uid=$(/system/bin/cmd package list packages -U com.azefsw.audioconnect |
    awk '$1 == "package:com.azefsw.audioconnect" && $2 ~ /^uid:[0-9]+$/ {sub(/^uid:/, "", $2); print $2}')
case "$relay_uid" in ""|*[!0-9]*) exit 0 ;; esac

# exec replaces this shell. No busy supervisor, dumpsys loop, or restart loop.
printf '%s\n' "$$" > "$MODDIR/relay.pid"
exec "$MODDIR/bin/arm64-v8a/mido-relay-mic" --uid "$relay_uid" \
    --lock "$MODDIR/relay.lock" > "$MODDIR/relay.log" 2>&1
