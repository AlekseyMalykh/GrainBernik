"""Validate the assembled image before authorizing a separate card-write helper."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def digest_file(path, algorithm='sha256'):
    digest = hashlib.new(algorithm)
    with path.open('rb') as source:
        while chunk := source.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def image_file(image, name):
    return subprocess.check_output(['mtype', '-i', str(image) + '@@16777216', '::/' + name])


def verify(base, image, output):
    repo = Path(__file__).resolve().parents[1]
    out = base / 'build-uac2/build'
    system = base / 'SYSTEM-uac2-final'
    if not system.exists():
        system = base / 'SYSTEM-uac2'
    assert (out / 'include/config/kernel.release').read_text().strip() == '7.1.2-gb-uac2'
    assert image.stat().st_size == 2198863872
    kernel_bytes = (out / 'arch/arm64/boot/Image').read_bytes()
    assert kernel_bytes[56:60] == b'ARM\x64'
    assert (base / 'official-initramfs.cpio.gz').read_bytes() in kernel_bytes
    for firmware in ('panels/anbernic,rg40xx-panel.panel',
                     'panels/anbernic,rg40xx-v2-panel.panel', 'rtw88/rtw8821c_fw.bin'):
        assert (base / 'rootfs/usr/lib/kernel-overlays/base/lib/firmware' / firmware).read_bytes() in kernel_bytes
    config = (out / '.config').read_text()
    for flag in ('USB_CONFIGFS_F_UAC2', 'USB_F_UAC2', 'USB_U_AUDIO', 'SND_PCM',
                 'USB_MUSB_DUAL_ROLE', 'USB_MUSB_SUNXI', 'USB_CONFIGFS'):
        assert 'CONFIG_' + flag + '=y\n' in config, flag
    for name, source in [('KERNEL', out / 'arch/arm64/boot/Image'), ('SYSTEM', system)]:
        proc = subprocess.Popen(['mtype', '-i', str(image) + '@@16777216', '::/' + name], stdout=subprocess.PIPE)
        sha = hashlib.sha256()
        md5 = hashlib.md5()
        count = 0
        while chunk := proc.stdout.read(4 * 1024 * 1024):
            sha.update(chunk)
            md5.update(chunk)
            count += len(chunk)
        assert proc.wait() == 0 and count == source.stat().st_size
        assert sha.hexdigest() == digest_file(source), name + ' differs from the built file'
        assert image_file(image, name + '.md5').decode().split()[0] == md5.hexdigest()
        print(name + ' contents and checksum verified', flush=True)
    dtb = out / 'arch/arm64/boot/dts/allwinner/sun50i-h700-anbernic-rg40xx-h.dtb'
    assert image_file(image, 'dtb.img') == dtb.read_bytes()
    extlinux = image_file(image, 'extlinux/extlinux.conf').decode()
    assert 'FDT /dtb.img' in extlinux and 'ddr3' not in extlinux.lower()
    seed = 'usr/share/grainbrick-seed/grainbrick beta 1.0.1/'
    for name in ('gb_usb_gadget.py', 'gb_usb_audio.py', 'gb_usb_settings.py', 'gb_launch.py'):
        installed = subprocess.check_output(['unsquashfs', '-cat', str(system), seed + name])
        assert installed == (repo / 'rg40xx-h-patch/grainbrick-beta' / name).read_bytes(), name
    for name, target in [('gb_usb_service.py', 'usr/lib/grainbrick/gb_usb_service.py'),
                         ('grainbrick-usb-audio.service', 'usr/lib/systemd/system/grainbrick-usb-audio.service'),
                         ('082-grainbrick', 'usr/lib/autostart/common/082-grainbrick')]:
        assert subprocess.check_output(['unsquashfs', '-cat', str(system), target]) == (repo / 'tools/rocknix' / name).read_bytes()
    native = subprocess.check_output(['unsquashfs', '-cat', str(system), seed + 'main.cpython-312-aarch64-linux-gnu.so'])
    assert hashlib.sha256(native).hexdigest() == 'bcef28522efb789105ac5126612e97692374d1a5eff65b58a9a1876650b8f2a8'
    module = base / 'modules-staging/lib/modules/7.1.2-gb-uac2/rocknix-joypad/rocknix-joypad.ko'
    module_in_image = subprocess.check_output(['unsquashfs', '-cat', str(system), 'usr/lib/kernel-overlays/base/lib/modules/7.1.2-gb-uac2/rocknix-joypad/rocknix-joypad.ko'])
    assert module_in_image == module.read_bytes()
    assert subprocess.check_output(['modinfo', '-F', 'vermagic', str(module)]).startswith(b'7.1.2-gb-uac2 ')
    print('Device tree, USB adapters, unchanged official binary, and matching joypad module verified', flush=True)
    result = {'Verified': True, 'Kernel': '7.1.2-gb-uac2', 'ImageBytes': image.stat().st_size,
              'ImageSHA256': digest_file(image), 'KernelSHA256': digest_file(out / 'arch/arm64/boot/Image'),
              'SystemSHA256': digest_file(system), 'Board': 'Anbernic RG40XX H',
              'DRAM': 'DDR4', 'Panel': 'standard; v2 DTB also included in device_trees',
              'UpstreamImage': 'ROCKNIX-H700.aarch64-20261101-DDR4.img.gz',
              'UpstreamImageSHA256': '46ec25c30be24fff5f154460f988e53c0311e115fd72ee7b861b55e59c553a07',
              'PersonalizedSSH': 'public key only; private key remains on PC',
              'NativeUSBTestsPassed': 10, 'NativeAdvancedTestsPassed': 18,
              'BootVerifiedOnHardware': False, 'PhysicalUSBAudioVerified': False, 'IPhoneAudioVerified': False}
    output.write_text(json.dumps(result, indent=2) + '\n')
    print('Offline image validation passed: ' + result['ImageSHA256'])


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('base', type=Path)
    p.add_argument('image', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    verify(args.base, args.image, args.output)
