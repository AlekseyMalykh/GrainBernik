#!/usr/bin/env bash
# Build-check the ROCKNIX H700 kernel and RG40XX H device trees with UAC2.
# Takes an unpacked ROCKNIX 20261101 tree and the original Linux archive.
set -euo pipefail
export LC_ALL=C
shopt -s nullglob

if [[ $# != 3 ]]; then
    echo "Usage: $0 ROCKNIX_20261101_TREE linux-7.1.2.tar.xz NEW_BUILD_DIRECTORY" >&2
    exit 2
fi

rocknix=$(realpath "$1")
archive=$(realpath "$2")
work=$(realpath -m "$3")
kernel=$work/linux-7.1.2
out=$work/build
device=$rocknix/projects/ROCKNIX/devices/H700
config=$device/linux/linux.aarch64.conf
grep -qx '# CONFIG_USB_CONFIGFS_F_UAC2 is not set' "$config"
printf '%s  %s\n' '37198c93727be247c9fb5309bb86cd5e496c61e5322cd8c4eca9476bb0b5883f' "$archive" | sha256sum -c -

# Each build has a fresh source tree so applying the distro patches is repeatable.
mkdir "$work"
mkdir "$out"
tar -xf "$archive" -C "$work"
for patch_file in "$rocknix"/packages/linux/patches/default/*.patch "$device"/patches/linux/*.patch; do
    printf 'Applying %s\n' "${patch_file##*/}"
    sed -e 's/@TARGET_CPU@/cortex-a53/g' -e 's/@DEVICE@/H700/g' "$patch_file" |
        patch --directory="$kernel" --batch --forward -p1
done
cp "$device"/linux/dts/allwinner/*.dts "$kernel/arch/arm64/boot/dts/allwinner/"
cp "$config" "$out/.config"

# No distro initramfs is available in this isolated cross-build. These are
# kernel build outputs, not a ROCKNIX boot image or a KNULLI replacement.
"$kernel/scripts/config" --file "$out/.config" --enable USB_CONFIGFS_F_UAC2 \
    --set-str INITRAMFS_SOURCE '' --disable DEBUG_INFO_BTF --disable WERROR
make_kernel=(make -C "$kernel" O="$out" ARCH=arm64 CROSS_COMPILE="${CROSS_COMPILE:-aarch64-linux-gnu-}" DTC_FLAGS=-@)
"${make_kernel[@]}" olddefconfig
for option in USB_MUSB_DUAL_ROLE USB_MUSB_SUNXI USB_CONFIGFS USB_CONFIGFS_F_UAC2 USB_F_UAC2 USB_U_AUDIO SND_PCM; do
    grep -qx "CONFIG_$option=y" "$out/.config"
done

"${make_kernel[@]}" -j"${JOBS:-8}" \
    drivers/usb/musb/sunxi.o drivers/usb/musb/musb_gadget.o \
    drivers/usb/gadget/function/f_uac2.o drivers/usb/gadget/function/u_audio.o \
    allwinner/sun50i-h700-anbernic-rg40xx-h.dtb \
    allwinner/sun50i-h700-anbernic-rg40xx-h-v2-panel.dtb

for board in rg40xx-h rg40xx-h-v2-panel; do
    dtb="$out/arch/arm64/boot/dts/allwinner/sun50i-h700-anbernic-$board.dtb"
    # Locate the node by its MMIO address as the full DT path can change.
    soc=$(fdtget -l "$dtb" / | awk '/^soc(@[0-9a-f]+)?$/ { print; exit }')
    usb_node="/$soc/usb@5100000"
    status=$(fdtget "$dtb" "$usb_node" status)
    role=$(fdtget "$dtb" "$usb_node" dr_mode)
    [[ $status == okay && ( $role == otg || $role == peripheral ) ]]
    printf '%s: USB controller %s, role %s\n' "$board" "$status" "$role"
done

if [[ ${BUILD_IMAGE:-0} == 1 ]]; then
    "${make_kernel[@]}" -j"${JOBS:-8}" Image
    printf 'Kernel image: %s\n' "$out/arch/arm64/boot/Image"
fi
