#!/system/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Small shared helpers; sourced only during installation and boot.
TARGET=/vendor/etc/mixer_paths_mtp.xml
STOCK_SHA256=66d83c144b406660023654751c7a89adc823018ad3c90d69aa4df20fd5437234
FIXED_SHA256=52fded3b0bd3f615a8cc3fcd942708b3534f647d9ebd34a66f6edc1e6963fd18

file_hash() {
    hash_output=$(sha256sum "$1") || return 1
    printf '%s\n' "${hash_output%% *}"
}

supported_device() {
    [ "$(/system/bin/getprop ro.product.device)" = mido ] &&
        [ "$(/system/bin/getprop ro.build.version.sdk)" = 29 ]
}

module_ready() {
    supported_device &&
        [ ! -e "$MODDIR/disable" ] &&
        [ ! -e "$MODDIR/remove" ] &&
        [ "$(file_hash "$MODDIR/mixer_paths_mtp.xml")" = "$FIXED_SHA256" ]
}

our_mount_active() {
    source_id=$(stat -c '%d:%i' "$MODDIR/mixer_paths_mtp.xml") || return 1
    target_id=$(stat -c '%d:%i' "$TARGET") || return 1
    [ "$source_id" = "$target_id" ]
}

report_error() {
    /system/bin/log -p e -t mido-internal-mic-fix "$1"
}
