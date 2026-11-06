#!/usr/bin/env bash
# Complete the isolated H700 cross-build using firmware/initramfs from ROCKNIX.
# The matching in-tree and joypad modules must travel with this kernel.
set -euo pipefail
export LC_ALL=C
base=$(realpath "${1:?Pass the persistent H700 build directory}")
kernel=$base/build-uac2/linux-7.1.2
out=$base/build-uac2/build
firmware=$base/rootfs/usr/lib/kernel-overlays/base/lib/firmware
test -s "$base/official-initramfs.cpio.gz"
test -s "$base/official-kernel.config"
test -s "$firmware/panels/anbernic,rg40xx-panel.panel"
cp "$base/official-kernel.config" "$out/.config"
"$kernel/scripts/config" --file "$out/.config" \
    --enable USB_CONFIGFS_F_UAC2 --disable DEBUG_INFO_BTF --disable WERROR \
    --set-str LOCALVERSION '-gb-uac2' --disable LOCALVERSION_AUTO \
    --set-str INITRAMFS_SOURCE "$base/official-initramfs.cpio.gz" \
    --set-str EXTRA_FIRMWARE_DIR "$firmware"
make_kernel=(make -C "$kernel" O="$out" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- DTC_FLAGS=-@)
"${make_kernel[@]}" olddefconfig
for option in USB_MUSB_DUAL_ROLE USB_MUSB_SUNXI USB_CONFIGFS USB_CONFIGFS_F_UAC2 USB_F_UAC2 USB_U_AUDIO SND_PCM; do
    grep -qx "CONFIG_$option=y" "$out/.config"
done
"${make_kernel[@]}" -j"${JOBS:-8}" Image modules \
    allwinner/sun50i-h700-anbernic-rg40xx-h.dtb \
    allwinner/sun50i-h700-anbernic-rg40xx-h-v2-panel.dtb
version=$(cat "$out/include/config/kernel.release")
[[ $version == 7.1.2-gb-uac2 ]]
"${make_kernel[@]}" INSTALL_MOD_PATH="$base/modules-staging" INSTALL_MOD_STRIP=1 modules_install
printf '%s  %s\n' 7a9a90d9d25d48384771bf8fe7cfb53bba708b64aa4e56d44e71205a8bcc699a \
    "$base/rocknix-joypad.tar.gz" | sha256sum -c -
joypad=$base/rocknix-joypad-005033d1ddd8746c771f2c81f1174f2d892541c9
if [[ ! -d $joypad ]]; then tar -xzf "$base/rocknix-joypad.tar.gz" -C "$base"; fi
"${make_kernel[@]}" -j"${JOBS:-8}" M="$joypad" modules
mkdir -p "$base/modules-staging/lib/modules/$version/rocknix-joypad"
for module in "$joypad"/*.ko; do
    aarch64-linux-gnu-strip --strip-debug "$module"
    cp "$module" "$base/modules-staging/lib/modules/$version/rocknix-joypad/"
done
depmod -b "$base/modules-staging" "$version"
printf 'Completed %s including matching in-tree and joypad modules.\n' "$version"
sha256sum "$out/arch/arm64/boot/Image"
