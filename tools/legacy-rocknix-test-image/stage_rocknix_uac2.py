"""Stage the test-image additions without touching the card or its backup."""
import argparse
import hashlib
from pathlib import Path
import shutil


def copy_tree(source, target, ignore=None):
    """Merge a staging tree, preserving existing identical symlinks."""
    target.mkdir(parents=True, exist_ok=True)
    names = [p.name for p in source.iterdir()]
    skipped = set(ignore(str(source), names) if ignore else ())
    for name in names:
        if name in skipped:
            continue
        src, dst = source / name, target / name
        if src.is_symlink():
            if dst.is_symlink() and dst.readlink() == src.readlink():
                continue
            if dst.exists() or dst.is_symlink():
                raise RuntimeError('Conflicting staging symlink: ' + str(dst))
            dst.symlink_to(src.readlink(), target_is_directory=src.is_dir())
        elif src.is_dir():
            copy_tree(src, dst, ignore)
        else:
            shutil.copy2(src, dst)
    shutil.copystat(source, target)


def stage(base, runtime, saved_app):
    root = base / 'rootfs'
    assert (root / 'usr/bin/python3.14').is_file()
    assert (base / 'build-uac2/build/include/config/kernel.release').read_text().strip() == '7.1.2-gb-uac2'
    repo = Path(__file__).resolve().parents[1]
    target = root / 'usr/lib/grainbrick-python'
    copy_tree(runtime / 'root/usr', target)
    for package in ('pygame', 'pygame.libs', 'pygame-2.6.1.dist-info'):
        copy_tree(runtime / 'site' / package, target / 'site' / package)
    seed = root / 'usr/share/grainbrick-seed'
    seed.mkdir(parents=True, exist_ok=True)
    app = seed / saved_app.name
    copy_tree(saved_app, app, ignore=shutil.ignore_patterns('__pycache__', '*.bak', '*.log'))
    native = app / 'main.cpython-312-aarch64-linux-gnu.so'
    assert hashlib.sha256(native.read_bytes()).hexdigest() == 'bcef28522efb789105ac5126612e97692374d1a5eff65b58a9a1876650b8f2a8'
    for name in ('gb_usb_audio.py', 'gb_usb_gadget.py', 'gb_usb_settings.py', 'gb_launch.py'):
        shutil.copy2(repo / 'rg40xx-h-patch/grainbrick-beta' / name, app / name)
    for path in seed.rglob('*'):
        if not path.is_symlink():
            path.chmod(0o755 if path.is_dir() else 0o644)
    for name in ('GrainBrick beta 1.0.1.sh', 'GrainBernik USB Audio Diagnostics.sh'):
        shutil.copy2(repo / 'tools/rocknix' / name, seed / name)
        (seed / name).chmod(0o755)
    service_root = root / 'usr/lib/grainbrick'
    service_root.mkdir(exist_ok=True)
    shutil.copy2(repo / 'tools/rocknix/gb_usb_service.py', service_root)
    (service_root / 'gb_usb_service.py').chmod(0o644)
    shutil.copy2(repo / 'tools/rocknix/grainbrick-usb-audio.service', root / 'usr/lib/systemd/system')
    (root / 'usr/lib/systemd/system/grainbrick-usb-audio.service').chmod(0o644)
    hook = root / 'usr/lib/autostart/common/082-grainbrick'
    shutil.copy2(repo / 'tools/rocknix/082-grainbrick', hook)
    hook.chmod(0o755)
    userdata = root / 'userdata'
    if not userdata.is_symlink():
        assert not userdata.exists()
        userdata.symlink_to('/storage', target_is_directory=True)
    modules = base / 'modules-staging/lib/modules/7.1.2-gb-uac2'
    copy_tree(modules, root / 'usr/lib/kernel-overlays/base/lib/modules/7.1.2-gb-uac2',
              ignore=shutil.ignore_patterns('build', 'source'))
    print('Staged matching kernel modules, portable Python, saved GrainBrick data, and USB mode service.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base', type=Path)
    parser.add_argument('runtime', type=Path)
    parser.add_argument('saved_app', type=Path)
    args = parser.parse_args()
    stage(args.base, args.runtime, args.saved_app)
