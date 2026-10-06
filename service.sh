#!/system/bin/sh
# SPDX-License-Identifier: Apache-2.0
MODDIR=${0%/*}
. "$MODDIR/common.sh"
module_ready && our_mount_active || exit 0
[ "$(/system/bin/getprop init.svc.vendor.audio-hal-2-0)" = running ] || exit 0

# The HAL may have read its XML before post-fs-data. Refresh it once, never
# during an active call. This hook exits immediately; there is no polling.
phone_state=$(/system/bin/dumpsys -t 2 media.audio_policy 2>/dev/null |
    grep 'Phone state:') || exit 0
case "$phone_state" in
    *AUDIO_MODE_NORMAL*)
        /system/bin/setprop ctl.restart vendor.audio-hal-2-0 ||
            report_error "Could not refresh the audio HAL; reboot with the module enabled."
        ;;
esac
