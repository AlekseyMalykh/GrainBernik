#!/usr/bin/env bash
# Produce an offline RG40XX H test image; never opens a physical drive.
set -euo pipefail
export LC_ALL=C
base=$(realpath "${1:?build directory}")
archive=$(realpath "${2:?official DDR4 gzip image}")
image=$(realpath -m "${3:?new test image path}")
test ! -e "$image"
printf '%s  %s\n' 46ec25c30be24fff5f154460f988e53c0311e115fd72ee7b861b55e59c553a07 "$archive" | sha256sum -c -
out=$base/build-uac2/build
test "$(cat "$out/include/config/kernel.release")" = 7.1.2-gb-uac2
test -s "$out/arch/arm64/boot/Image"
test -s "$base/rootfs/usr/lib/grainbrick-python/bin/python3.12"
system=$base/SYSTEM-uac2
test ! -e "$system"
# All files in the official image belong to root. Staging is unprivileged.
mksquashfs "$base/rootfs" "$system" -noappend -all-root -comp zstd -b 1048576 -processors 4 -no-progress
unsquashfs -s "$system"
gzip -dc "$archive" > "$image"
fat="$image@@16777216"
mdir -i "$fat" ::/
mcopy -o -i "$fat" "$out/arch/arm64/boot/Image" ::/KERNEL
mcopy -o -i "$fat" "$system" ::/SYSTEM
dtbs=$out/arch/arm64/boot/dts/allwinner
mcopy -o -i "$fat" "$dtbs/sun50i-h700-anbernic-rg40xx-h.dtb" ::/dtb.img
for board in rg40xx-h rg40xx-h-v2-panel; do
    mcopy -o -i "$fat" "$dtbs/sun50i-h700-anbernic-$board.dtb" ::/device_trees/
done
printf '%s  target/KERNEL\n' "$(md5sum "$out/arch/arm64/boot/Image" | cut -d' ' -f1)" > "$base/KERNEL.md5"
printf '%s  target/SYSTEM\n' "$(md5sum "$system" | cut -d' ' -f1)" > "$base/SYSTEM.md5"
mcopy -o -i "$fat" "$base/KERNEL.md5" ::/KERNEL.md5
mcopy -o -i "$fat" "$base/SYSTEM.md5" ::/SYSTEM.md5
fdtget "$dtbs/sun50i-h700-anbernic-rg40xx-h.dtb" / model
mtype -i "$fat" ::/extlinux/extlinux.conf
sha256sum "$image"
