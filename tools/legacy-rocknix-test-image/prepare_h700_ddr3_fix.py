"""Build a DDR3 boot-only variant and a guarded sector patch from the DDR4 test image."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def prepare(base, directory):
    original = directory / 'GrainBernik-RG40XXH-UAC2-test-DDR4.img'
    variant = directory / 'GrainBernik-RG40XXH-UAC2-test-DDR3.img'
    assert sha(original) == 'd8b307f389b5145748cd9633c86da6b215a0e0010b557550358eb7fb4140f7fb'
    assert not variant.exists()
    dtbs = base / 'build-uac2/build/arch/arm64/boot/dts/allwinner'
    overlay = base / 'ddr3.dtbo'
    for board in ('rg40xx-h', 'rg40xx-h-v2-panel'):
        dtb = dtbs / ('sun50i-h700-anbernic-' + board + '.dtb')
        combined = base / (board + '-ddr3-validated.dtb')
        subprocess.run(['fdtoverlay', '-i', str(dtb), '-o', str(combined), str(overlay)], check=True)
        regulator = subprocess.check_output(['fdtget', str(combined), '/__symbols__', 'reg_dcdc3'], text=True).strip()
        for field in ('regulator-min-microvolt', 'regulator-max-microvolt'):
            assert subprocess.check_output(['fdtget', '-t', 'u', str(combined), regulator, field], text=True).strip() == '1200000'
    shutil.copyfile(original, variant)
    loader = base / 'rootfs/usr/share/bootloader/H700_DDR3_u-boot-sunxi-with-spl.bin'
    assert sha(loader) == '4fa9d47914c82674d88d70140e62d0d9af559ace0b12c9884efc547d8d89ab1c'
    with variant.open('r+b') as f:
        f.seek(8192)
        f.write(loader.read_bytes())
    fat = str(variant) + '@@16777216'
    config = base / 'extlinux-ddr3.conf'
    config.write_bytes(subprocess.check_output(['mtype', '-i', str(directory / 'ROCKNIX-H700.aarch64-20261101-DDR3.img') + '@@16777216', '::/extlinux/extlinux.conf']))
    subprocess.run(['mcopy', '-o', '-i', fat, str(config), '::/extlinux/extlinux.conf'], check=True)
    subprocess.run(['mcopy', '-o', '-i', fat, str(dtbs / 'sun50i-h700-anbernic-rg40xx-h.dtb'), '::/dtb.img'], check=True)
    for board in ('rg40xx-h', 'rg40xx-h-v2-panel'):
        subprocess.run(['mcopy', '-o', '-i', fat, str(dtbs / ('sun50i-h700-anbernic-' + board + '.dtb')), '::/device_trees/'], check=True)
    # Compare only changed chunks at sector granularity; full kernel/SYSTEM
    # remain in place. Patch ranges stay aligned and no larger than 64 KiB.
    ranges = []
    old_path = directory / 'ddr3-boot-patch-old.bin'
    new_path = directory / 'ddr3-boot-patch-new.bin'
    with original.open('rb') as old, variant.open('rb') as new, old_path.open('xb') as old_data, new_path.open('xb') as new_data:
        offset = 0
        while a := old.read(65536):
            b = new.read(len(a))
            if a != b:
                first = None
                for i in range(0, len(a) + 512, 512):
                    differs = i < len(a) and a[i:i + 512] != b[i:i + 512]
                    if differs and first is None:
                        first = i
                    if not differs and first is not None:
                        data_offset = old_data.tell()
                        old_data.write(a[first:i])
                        new_data.write(b[first:i])
                        ranges.append({'Offset': offset + first, 'Length': i - first, 'DataOffset': data_offset})
                        first = None
            offset += len(a)
    # Storage starts at this fixed offset in the original image. It must not
    # be modified by a boot fix, including on an already-expanded card.
    assert all(r['Offset'] + r['Length'] <= 2164260864 for r in ranges)
    result = {'Version': 1, 'Verified': True, 'DiskBytes': 62239277056,
              'Reason': 'Stock boot0 has LPDDR3 type 7 and matching DDR3 electrical parameters',
              'OriginalImageSHA256': sha(original), 'VariantImageSHA256': sha(variant),
              'OldPatchSHA256': sha(old_path), 'NewPatchSHA256': sha(new_path),
              'Ranges': ranges, 'PatchBytes': old_path.stat().st_size,
              'BootloaderSHA256': sha(loader), 'DDR3VoltageMicrovolts': 1200000,
              'DTBOverlayValidated': True, 'HardwareBootVerified': False}
    (directory / 'ddr3-boot-patch.json').write_text(json.dumps(result, indent=2) + '\n')
    print('DDR3 boot fix ready:', len(ranges), 'ranges,', result['PatchBytes'], 'bytes; storage untouched.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    prepare(args.base, args.directory)
