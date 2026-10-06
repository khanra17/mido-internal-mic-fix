#!/system/bin/sh
# SPDX-License-Identifier: Apache-2.0
# KernelSU sources this hook after extracting the ZIP.
[ "$KSU" = true ] || abort "Install this module using KernelSU Manager."
. "$MODPATH/common.sh"

supported_device || abort "Only the tested Redmi Note 4 (mido), Android 10 layout is supported."
[ -f "$TARGET" ] || abort "Vendor mixer configuration is missing."

current_hash=$(file_hash "$TARGET") || abort "Cannot read the vendor mixer configuration."
case "$current_hash" in
    "$STOCK_SHA256")
        ui_print "- Generating the verified speakerphone-input patch"
        awk -f "$MODPATH/patch-mixer.awk" "$TARGET" > "$MODPATH/mixer_paths_mtp.xml.tmp" ||
            abort "Cannot patch handset-mic."
        ;;
    "$FIXED_SHA256")
        ui_print "- Existing module patch detected"
        cp "$TARGET" "$MODPATH/mixer_paths_mtp.xml.tmp" ||
            abort "Cannot copy the existing patch."
        ;;
    *)
        abort "Unsupported or conflicting mixer configuration. No changes were made."
        ;;
esac

[ "$(file_hash "$MODPATH/mixer_paths_mtp.xml.tmp")" = "$FIXED_SHA256" ] ||
    abort "Generated configuration failed its integrity check."
mv "$MODPATH/mixer_paths_mtp.xml.tmp" "$MODPATH/mixer_paths_mtp.xml" ||
    abort "Cannot save the generated configuration."

set_perm_recursive "$MODPATH" 0 0 0755 0644
set_perm "$MODPATH/post-fs-data.sh" 0 0 0755
set_perm "$MODPATH/service.sh" 0 0 0755
set_perm "$MODPATH/mixer_paths_mtp.xml" 0 0 0644 u:object_r:vendor_configs_file:s0
ui_print "- Playback paths are unchanged"
ui_print "- No metamodule or background audio daemon is required"
ui_print "- Reboot to apply"
