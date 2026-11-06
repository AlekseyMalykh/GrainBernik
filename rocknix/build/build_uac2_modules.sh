#!/usr/bin/env bash
# GrainBernik: собрать u_audio.ko и usb_f_uac2.ko для ОФИЦИАЛЬНОГО ROCKNIX 20261101
# (H700 / RG40XX H, ядро Linux 7.2.0). Запускать в WSL (Ubuntu):
#   bash rocknix/build/build_uac2_modules.sh      (from the repository root)
# Консоль должна быть включена и доступна по SSH (пароль спросят 1 раз).
set -euo pipefail

CONSOLE="${CONSOLE:-root@192.168.0.150}"
WORK="${WORK:-$HOME/gb-uac2-7.2}"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${OUT:-$HERE/../uac2}"
LINUX_VER=7.2
LINUX_SHA=f9fef3d14c0df53819026f4be74459835c2a0b0dcbf5b5bbd9ea19f0829402b3
ROCKNIX_TAG=20261101
X=aarch64-linux-gnu-
MK=(make ARCH=arm64 CROSS_COMPILE=$X -j"$(nproc)")
SSH=(ssh -o ControlMaster=auto -o ControlPath="$WORK/ssh-%r@%h" -o ControlPersist=15m "$CONSOLE")

say() { printf '\n=== %s\n' "$*"; }
mkdir -p "$WORK" "$OUT"
cd "$WORK"

say "1/7 Проверка инструментов"
need=()
for c in ${X}gcc make flex bison bc git curl xz patch perl ssh scp; do command -v "$c" >/dev/null || need+=("$c"); done
[ -f /usr/include/openssl/opensslv.h ] || need+=(libssl-dev)
[ -f /usr/include/libelf.h ] || [ -f /usr/include/elfutils/libelf.h ] || need+=(libelf-dev)
if [ ${#need[@]} -gt 0 ]; then
  echo "Не хватает: ${need[*]} — ставлю пакеты (нужен пароль WSL для sudo)"
  sudo apt-get update
  sudo apt-get install -y gcc-aarch64-linux-gnu build-essential flex bison bc git curl xz-utils patch perl libssl-dev libelf-dev openssh-client
fi
${X}gcc --version | head -1

say "2/7 Конфигурация ядра с консоли ($CONSOLE)"
"${SSH[@]}" 'uname -r; zcat /proc/config.gz' > console.txt
KREL=$(head -1 console.txt); tail -n +2 console.txt > config-console
echo "Ядро на консоли: $KREL"
[ "$KREL" = "7.2.0" ] || { echo "ОЖИДАЛОСЬ 7.2.0 — остановка"; exit 1; }

say "3/7 Исходники Linux $LINUX_VER и ROCKNIX $ROCKNIX_TAG"
[ -f linux-$LINUX_VER.tar.xz ] || curl -fL -o linux-$LINUX_VER.tar.xz \
  https://cdn.kernel.org/pub/linux/kernel/v7.x/linux-$LINUX_VER.tar.xz
echo "$LINUX_SHA  linux-$LINUX_VER.tar.xz" | sha256sum -c -
[ -d rocknix ] || git clone -q --depth 1 --branch $ROCKNIX_TAG https://github.com/ROCKNIX/distribution rocknix

if [ ! -f linux-$LINUX_VER/.gb-patched ]; then
  rm -rf linux-$LINUX_VER
  tar xf linux-$LINUX_VER.tar.xz
  say "4/7 Патчи ROCKNIX (в том же порядке, что и официальная сборка)"
  P=rocknix/projects/ROCKNIX/packages/linux/patches
  D=rocknix/projects/ROCKNIX/devices/H700/patches/linux
  : > patch-failures.txt
  shopt -s nullglob
  for f in $P/mainline/*.patch $P/$LINUX_VER/*.patch $D/*.patch; do
    if ! patch -d linux-$LINUX_VER -p1 -N -s < "$f" > /dev/null 2>&1; then
      echo "$f" >> patch-failures.txt; echo "  не применился: ${f##*/}"
    fi
  done
  touch linux-$LINUX_VER/.gb-patched
fi
[ -s patch-failures.txt ] && echo "Внимание: часть патчей не применилась (см. $WORK/patch-failures.txt)"

cd linux-$LINUX_VER
say "5/7 Конфигурация"
cp ../config-console .config
# initramfs ROCKNIX встраивается их сборочной системой; для модулей он не нужен
scripts/config --set-str INITRAMFS_SOURCE ""
# встроенные прошивки Wi-Fi/BT тоже берутся из их сборки; на модули не влияют
scripts/config --set-str EXTRA_FIRMWARE ""
"${MK[@]}" olddefconfig > /dev/null
crit='^CONFIG_(MODVERSIONS|MODULES|BASIC_MODVERSIONS|EXTENDED_MODVERSIONS|SMP|PREEMPT|PREEMPT_RT|MODULE_UNLOAD|STACKPROTECTOR|STACKPROTECTOR_STRONG|STACKPROTECTOR_PER_TASK|ARM64_PTR_AUTH_KERNEL|ARM64_BTI_KERNEL|SHADOW_CALL_STACK|RANDSTRUCT_NONE|GCC_PLUGIN_[A-Z_]+|SND_PCM|USB_GADGET|USB_LIBCOMPOSITE|USB_CONFIGFS|DEBUG_INFO_BTF)='
diff <(grep -E "$crit" ../config-console | sort) <(grep -E "$crit" .config | sort) \
  && echo "Ключевые параметры совпадают с консолью" \
  || { echo "ОШИБКА: компилятор изменил важные параметры (см. diff выше) — остановка"; exit 1; }

say "6/7 Сборка ядра для таблицы версий символов (10–40 минут)"
"${MK[@]}" vmlinux
cp vmlinux.symvers Module.symvers
"${MK[@]}" modules_prepare
# CRC символов берём из ОФИЦИАЛЬНОГО ядра консоли (извлечены из /flash/KERNEL):
# GCC 13 даёт другие CRC, чем GCC 16.2 сборки ROCKNIX, хотя раскладка структур та же.
if [ -f "$HERE/official.symvers" ]; then
  cp "$HERE/official.symvers" Module.symvers
  echo "Используются CRC официального ядра: $(wc -l < Module.symvers) символов"
fi

say "7/7 Сборка модулей UAC2"
M="$WORK/uac2-mod"; rm -rf "$M"; mkdir -p "$M"
cp drivers/usb/gadget/function/{f_uac2.c,u_audio.c} drivers/usb/gadget/function/*.h "$M"/
printf 'obj-m := u_audio.o usb_f_uac2.o\nusb_f_uac2-y := f_uac2.o\n' > "$M/Kbuild"
"${MK[@]}" M="$M" modules
for k in u_audio usb_f_uac2; do
  vm=$(/sbin/modinfo -F vermagic "$M/$k.ko" 2>/dev/null || strings "$M/$k.ko" | grep -m1 '^vermagic=' | cut -d= -f2)
  echo "$k.ko: vermagic='$vm'"
  case "$vm" in "7.2.0 SMP preempt mod_unload modversions aarch64"*) ;; *) echo "НЕОЖИДАННЫЙ vermagic — остановка"; exit 1;; esac
done
cp "$M"/u_audio.ko "$M"/usb_f_uac2.ko "$OUT"/
echo "Готово: модули в $OUT"

read -r -p "Скопировать модули и скрипты на консоль в /storage/uac2? [y/N] " a
if [ "${a,,}" = y ]; then
  "${SSH[@]}" 'mkdir -p /storage/uac2'
  scp -o ControlPath="$WORK/ssh-%r@%h" "$OUT"/u_audio.ko "$OUT"/usb_f_uac2.ko "$OUT"/uac2-on.sh "$OUT"/uac2-off.sh "$CONSOLE":/storage/uac2/
  "${SSH[@]}" 'chmod +x /storage/uac2/*.sh; ls -l /storage/uac2'
  echo "На консоли: sh /storage/uac2/uac2-on.sh  (выключить: sh /storage/uac2/uac2-off.sh)"
fi
