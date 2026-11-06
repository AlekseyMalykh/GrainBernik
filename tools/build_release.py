#!/usr/bin/env python3
"""Build GrainBernik release assets (no proprietary GrainBrick files).

    python3 tools/build_release.py v0.2.0-beta.1 [output_dir]

Creates <output_dir>/ (default: release/<version>/) with
  GrainBernik-<version>-RG40XXH-patch.zip   fresh installation (repo payload)
  GrainBernik-<version>-RG40XXH-update.zip  existing installation
  SHA256SUMS.txt, verification.json
Run from a clean, committed tree: verification.json records HEAD.
"""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

REPO = Path(__file__).resolve().parents[1]
STAMP = (2026, 1, 1, 0, 0, 0)  # deterministic archive timestamps
SKIP = re.compile(r'(__pycache__|\.pyc$|\.bak$|\.tmp$)')

UPDATE_MD = """# GrainBernik {v} — update / обновление

ROCKNIX:
1. Copy `grainbrick-beta/*` into `/storage/roms/ports/grainbrick beta 1.0.1/`
   (replace files).
2. Copy `rocknix/GrainBrick beta 1.0.1.sh` into `/storage/roms/ports/`.
Both steps are required. Settings, samples, projects and recordings are kept.

KNULLI: copy only `grainbrick-beta/*`; keep your KNULLI launcher.

---

ROCKNIX:
1. Скопируйте `grainbrick-beta/*` в `/storage/roms/ports/grainbrick beta 1.0.1/`
   (с заменой).
2. Скопируйте `rocknix/GrainBrick beta 1.0.1.sh` в `/storage/roms/ports/`.
Нужны оба шага. Настройки, сэмплы, проекты и записи сохраняются.

KNULLI: копируйте только `grainbrick-beta/*`, свой запускатель KNULLI оставьте.
"""


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def files(*roots):
    for root in roots:
        path = REPO / root
        items = [path] if path.is_file() else sorted(p for p in path.rglob('*') if p.is_file())
        for item in items:
            rel = item.relative_to(REPO).as_posix()
            if not SKIP.search(rel):
                yield item, rel


def write_zip(target, entries):
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for arcname, data in entries:
            info = zipfile.ZipInfo(arcname, STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if arcname.endswith('.sh') else 0o644) << 16
            archive.writestr(info, data)


def tests():
    result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests'],
                            cwd=REPO, capture_output=True, text=True)
    text = result.stderr + result.stdout
    ran = re.search(r'Ran (\d+) tests', text)
    skipped = re.search(r'skipped=(\d+)', text)
    return dict(ok=result.returncode == 0, ran=int(ran[1]) if ran else 0,
                skipped=int(skipped[1]) if skipped else 0)


def main(version, out=None):
    out = Path(out) if out else REPO / 'release' / version
    out.mkdir(parents=True, exist_ok=True)
    notes = 'docs/releases/%s.md' % version
    if not (REPO / notes).is_file():
        raise SystemExit('missing release notes: ' + notes)
    patch_files = list(files('README.md', 'README_RU.md', 'docs/ADVANCED_SETTINGS.md',
                             'docs/SHUTDOWN_FIX.md', notes, 'rg40xx-h-patch', 'rocknix'))
    patch = out / ('GrainBernik-%s-RG40XXH-patch.zip' % version)
    write_zip(patch, [(rel, p.read_bytes()) for p, rel in patch_files])
    update_entries = [('UPDATE.md', UPDATE_MD.format(v=version).encode())]
    update_entries += [(rel.replace('rg40xx-h-patch/', '', 1), p.read_bytes())
                       for p, rel in files('rg40xx-h-patch/grainbrick-beta')]
    update_entries += [('rocknix/GrainBrick beta 1.0.1.sh',
                        (REPO / 'rocknix/GrainBrick beta 1.0.1.sh').read_bytes())]
    update = out / ('GrainBernik-%s-RG40XXH-update.zip' % version)
    write_zip(update, update_entries)
    (out / 'SHA256SUMS.txt').write_text(''.join('%s  %s\n' % (sha256(z), z.name)
                                                for z in (patch, update)))
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=REPO, capture_output=True,
                            text=True).stdout.strip()
    dirty = bool(subprocess.run(['git', 'status', '--porcelain'], cwd=REPO, capture_output=True,
                                text=True).stdout.strip())
    test_result = tests()
    verification = {
        'version': version,
        'built_on': datetime.date.today().isoformat(),
        'source_commit': commit,
        'working_tree_clean': not dirty,
        'proprietary_application_included': False,
        'device': 'Anbernik RG40XX H',
        'os': 'official ROCKNIX 20261101 (DDR4 image); KNULLI supported without iPhone mode',
        'unit_tests': test_result,
        'assets_sha256': {z.name: sha256(z) for z in (patch, update)},
        'payload_sha256': {rel: sha256(p) for p, rel in patch_files},
    }
    (out / 'verification.json').write_text(json.dumps(verification, indent=2, ensure_ascii=False) + '\n')
    print('Release assets in', out)
    print('tests:', test_result, '| commit:', commit[:12], '| clean:', not dirty)
    if not test_result['ok']:
        raise SystemExit('tests failed')


if __name__ == '__main__':
    if len(sys.argv) not in (2, 3):
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
