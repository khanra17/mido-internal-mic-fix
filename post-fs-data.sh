#!/system/bin/sh
# SPDX-License-Identifier: Apache-2.0
MODDIR=${0%/*}
. "$MODDIR/common.sh"
module_ready || exit 0
our_mount_active && exit 0

current_hash=$(file_hash "$TARGET") || exit 0
case "$current_hash" in
    "$STOCK_SHA256"|"$FIXED_SHA256") ;;
    *)
        report_error "Vendor layout changed or another module conflicts; not mounting."
        exit 0
        ;;
esac

# No setprop here: property-service calls can deadlock in post-fs-data.
mount -o bind "$MODDIR/mixer_paths_mtp.xml" "$TARGET" ||
    report_error "Could not mount the microphone configuration."
