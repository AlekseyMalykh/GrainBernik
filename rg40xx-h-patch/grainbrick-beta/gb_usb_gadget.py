"""Read-only USB/ALSA inventory and explicit, journalled ConfigFS activation.

No import-time system changes. All paths can be redirected to fixtures.
Never changes USB roles, charging, descriptors, services or KNULLI settings.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess

FLAGS = ('USB_GADGET', 'CONFIGFS_FS', 'USB_LIBCOMPOSITE', 'USB_CONFIGFS',
         'USB_CONFIGFS_F_UAC1', 'USB_CONFIGFS_F_UAC2', 'USB_F_UAC1',
         'USB_F_UAC2', 'SND_USB_AUDIO', 'SND_ALOOP', 'USB_SUNXI_UDC0')
ATTRS = tuple(p + '_' + a for p in ('c', 'p') for a in ('chmask', 'srate', 'ssize'))
FAULTY_SUNXI_UAC2_SHA256 = '80b2832a7a9ef2298b9395b149619e5e4b2960d289b14b670eb3bffc97a05b69'


def read(path):
    try:
        return Path(path).read_text(errors='replace').strip()
    except OSError:
        return None


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    with temp.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def audio_format(attributes, prefix):
    def number(key):
        try:
            return int(attributes[prefix + '_' + key], 0)
        except (TypeError, ValueError):
            return None
    mask, size = number('chmask'), number('ssize')
    try:
        rates = [int(value.strip()) for value in attributes[prefix + '_srate'].split(',')]
    except (AttributeError, ValueError):
        rates = None
    return {'enabled': bool(mask) if mask is not None else None,
            'channels': mask.bit_count() if mask is not None else None,
            'advertised_rates': rates, 'sample_bits': size * 8 if size else None}


class System:
    def __init__(self, root='/', release=None):
        self.root = Path(root)
        self.release = release or platform.release()

    def path(self, name):
        return self.root / name.lstrip('/')

    def kernel(self):
        candidates = [self.path('/proc/config.gz'),
                      self.path('/boot/config-' + self.release),
                      self.path('/lib/modules/' + self.release + '/build/.config')]
        for path in candidates:
            try:
                text = (gzip.decompress(path.read_bytes()).decode() if path.suffix == '.gz'
                        else path.read_text())
            except (OSError, EOFError, ValueError):
                continue
            result = {}
            for flag in FLAGS:
                match = re.search(r'^CONFIG_' + flag + r'=(y|m)$', text, re.M)
                result[flag] = match[1] if match else (
                    'n' if '# CONFIG_' + flag + ' is not set' in text else 'unknown')
            return {'source': str(path), 'flags': result}
        return {'source': None, 'flags': dict.fromkeys(FLAGS, 'unknown')}

    def udcs(self):
        return [{'name': p.name, **{a: read(p / a) for a in
                 ('state', 'current_speed', 'maximum_speed', 'function')}}
                for p in sorted(self.path('/sys/class/udc').glob('*'))]

    def function_support(self, kind):
        """Config and separately shipped modules may disagree on vendor BSPs."""
        flag = self.kernel()['flags']['USB_CONFIGFS_F_' + kind.upper()]
        modules = self.path('/lib/modules/' + self.release)
        files = [str(p) for p in modules.rglob('*.ko*')
                 if re.search(r'(?:^|_)' + kind + r'\.ko(?:\.|$)', p.name)]
        builtin = read(modules / 'modules.builtin') or ''
        built_in = bool(re.search(r'(?:^|/)(?:usb_f_)?' + kind + r'\.ko$', builtin, re.M))
        loaded = bool(re.search(r'^usb_f_' + kind + r'\s',
                                read(self.path('/proc/modules')) or '', re.M))
        registered = self.path('/sys/module/usb_f_' + kind).is_dir()
        instances = [f['path'] for g in self.gadgets() for f in g['functions']
                     if f['name'].startswith(kind + '.')]
        return {'kernel_flag': flag, 'module_files': files, 'built_in_metadata': built_in,
                'loaded_module': loaded, 'sys_module': registered,
                'instances': instances,
                'state': 'present' if instances else 'candidate' if files or built_in or loaded or registered or flag in ('y', 'm')
                else 'disabled' if flag == 'n' else 'unknown'}

    def gadgets(self):
        found = []
        for g in sorted(self.path('/sys/kernel/config/usb_gadget').glob('*')):
            functions = []
            for f in sorted((g / 'functions').glob('*')):
                links = [str(c.relative_to(g)) for c in (g / 'configs').glob('*/*')
                         if c.is_symlink() and c.resolve() == f.resolve()]
                attributes = {a: read(f / a) for a in ATTRS}
                functions.append({'name': f.name, 'path': str(f), 'links': links,
                                  'attributes': attributes,
                                  'capture_usb_out': audio_format(attributes, 'c'),
                                  'playback_usb_in': audio_format(attributes, 'p')})
            found.append({'path': str(g), 'udc': read(g / 'UDC'), 'functions': functions,
                          'configurations': [str(c) for c in (g / 'configs').glob('*')
                                             if c.is_dir()]})
        return found

    def cards(self):
        found = []
        for card in sorted(self.path('/proc/asound').glob('card[0-9]*')):
            if not re.fullmatch(r'card\d+', card.name):
                continue
            number = int(card.name[4:])
            card_id = read(card / 'id')
            info = read(self.path('/proc/asound/cards')) or ''
            match = re.search(r'^\s*' + str(number) + r'\s+\[[^\]]+\]:\s*(.*)', info, re.M)
            name = match[1] if match else ''
            device = self.path('/sys/class/sound/' + card.name + '/device')
            device_path = str(device.resolve()) if device.exists() else None
            external = (card / 'usbid').exists()
            # Gadget ALSA cards are NOT USB host cards: they lack usbid.
            # Conservative kernel names or an actual ConfigFS device ancestry.
            gadget = not external and (bool(re.search(
                r'(?:UAC[12]_?Gadget|g_audio|audiosource|f_uac[12])',
                (card_id or '') + ' ' + name, re.I)) or
                bool(device_path and '/usb_gadget/' in device_path))
            pcms = []
            for pcm in sorted(card.glob('pcm*')):
                m = re.fullmatch(r'pcm(\d+)([cp])', pcm.name)
                if not m:
                    continue
                streams = []
                for sub in sorted(pcm.glob('sub*')):
                    streams.append({'path': str(sub), 'status': read(sub / 'status'),
                                    'hw_params': read(sub / 'hw_params')})
                pcms.append({'device': int(m[1]), 'direction': 'capture' if m[2] == 'c' else 'playback',
                             'substreams': streams})
            found.append({'number': number, 'id': card_id, 'name': name,
                          'device_path': device_path, 'external_usb': external,
                          'gadget': gadget, 'pcms': pcms})
        return found

    def report(self, commands=False):
        modules_dir = self.path('/lib/modules/' + self.release)
        report = {'kernel_release': self.release, 'kernel': self.kernel(),
                  'function_support': {k: self.function_support(k) for k in ('uac1', 'uac2')},
                  'udcs': self.udcs(), 'gadgets': self.gadgets(), 'cards': self.cards(),
                  'alsa_cards': read(self.path('/proc/asound/cards')),
                  'alsa_pcm': read(self.path('/proc/asound/pcm')),
                  'loaded_modules': read(self.path('/proc/modules')),
                  'built_in_modules': read(modules_dir / 'modules.builtin'),
                  'module_files': [str(p) for p in modules_dir.rglob('*.ko*')
                                   if re.search(r'uac|u_audio|g_audio|snd.*(usb|aloop)', p.name)],
                  'usb_roles': {str(p): read(p) for pattern in (
                      '/sys/class/usb_role/*/role', '/sys/devices/platform/soc/usbc0/otg_role')
                      for p in self.root.glob(pattern.lstrip('/'))}
                  }
        if commands:
            report['commands'] = {}
            for argv in (['aplay', '-l'], ['arecord', '-l'], ['lsusb'], ['dmesg']):
                try:
                    proc = subprocess.run(argv, capture_output=True, text=True, timeout=4,
                                          errors='replace')
                    output = proc.stdout + proc.stderr
                    if argv[0] == 'dmesg':
                        output = '\n'.join(line for line in output.splitlines()
                                           if re.search('usb|gadget|uac|xrun|snd', line, re.I))[-16000:]
                    report['commands'][' '.join(argv)] = {'returncode': proc.returncode,
                                                          'output': output}
                except (OSError, subprocess.TimeoutExpired) as exc:
                    report['commands'][' '.join(argv)] = {'unavailable': str(exc)}
        report['notes'] = diagnosis(report)
        return report


def diagnosis(report):
    notes = ['USB OUT -> Anbernic ALSA Capture; Anbernic ALSA Playback -> USB IN.',
             'Enumeration and PCM presence do not prove audio transfer or iPhone identity.']
    if not report['kernel']['source']:
        notes.append('Kernel config unavailable: driver support is unknown, not absent.')
    if not report['udcs']:
        notes.append('No UDC visible: check device-capable OTG port, role and controller driver.')
    for flag in ('USB_CONFIGFS_F_UAC1', 'USB_CONFIGFS_F_UAC2'):
        value = report['kernel']['flags'][flag]
        notes.append('CONFIG_%s=%s%s' % (flag, value,
                     ' (disabled in this kernel build)' if value == 'n' else ''))
        support = report['function_support'][flag[-4:].lower()]
        if support['module_files'] and value == 'n':
            notes.append('Separately shipped ' + flag[-4:].lower() +
                         ' module conflicts with embedded config: ABI/loadability must be checked on device.')
    for gadget in report['gadgets']:
        for f in gadget['functions']:
            if f['name'].startswith('audio_source'):
                notes.append('audio_source is one-way console -> host; it cannot capture iPhone audio.')
            if f['name'].startswith(('uac1.', 'uac2.')):
                if not f['links']:
                    notes.append(f['name'] + ': not linked into a USB configuration.')
                for prefix, label in (('c', 'ALSA Capture / USB OUT'), ('p', 'ALSA Playback / USB IN')):
                    mask = f['attributes'].get(prefix + '_chmask')
                    notes.append(f['name'] + ' ' + label + ': ' + (
                        'disabled' if mask == '0' else 'mask=' + str(mask) + ' (unknown if null)'))
    notes.append('Current negotiated PCM parameters are in substreams.hw_params; closed means unknown.')
    notes.append('RUNNING/owner_pid identifies possible PCM contention; no devices were opened by diagnostics.')
    return notes


class GadgetError(RuntimeError):
    pass


class Activation:
    """Only append our own function to an explicit existing configuration.

    Journal persists across crash/reboot. Never remove an existing function.
    Unbinding a buggy BSP can hang the kernel; software rollback cannot cure it.
    """
    def __init__(self, system, journal):
        self.system, self.journal = system, Path(journal)

    def plan(self, config, kind='uac2', rate=48000, channels=2, sample_bytes=2):
        base = self.system.path('/sys/kernel/config/usb_gadget').resolve()
        config = Path(config).resolve()
        if config.parent.name != 'configs' or config.parent.parent.parent != base or not config.is_dir():
            raise GadgetError('Select an existing ConfigFS gadget/configs/<configuration> directory')
        if kind not in ('uac1', 'uac2') or rate not in (44100, 48000, 96000) or channels not in (1, 2) or sample_bytes not in (2, 3, 4):
            raise GadgetError('Unsupported requested audio format')
        gadget = config.parent.parent
        if any(f.name.startswith(('uac1.', 'uac2.', 'uac1_legacy.', 'audio_source.'))
               for f in (gadget / 'functions').iterdir()):
            raise GadgetError('Existing audio function: use it or restore its owner; refusing to replace it')
        support = self.system.function_support(kind)
        if support['state'] == 'disabled':
            raise GadgetError('Driver Not Available: CONFIG_USB_CONFIGFS_F_' + kind.upper() + '=n')
        udc = read(gadget / 'UDC')
        udcs = self.system.udcs()
        if not udc:
            if len(udcs) != 1:
                raise GadgetError('Need one unambiguous UDC or an already bound gadget')
            udc = udcs[0]['name']
        if udc not in [u['name'] for u in udcs]:
            raise GadgetError('Selected UDC unavailable')
        if read(gadget / 'UDC') is None:
            raise GadgetError('UDC binding unreadable; refusing activation')
        if any(g['udc'] == udc and Path(g['path']).resolve() != gadget
               for g in self.system.gadgets()):
            raise GadgetError('UDC owned by another gadget')
        function = gadget / 'functions' / (kind + '.grainbernik')
        if function.exists() or (config / function.name).is_symlink():
            raise GadgetError('Owned resource name already exists; restore previous journal first')
        blocked_reason = None
        if kind == 'uac2' and self.system.release == '4.9.170' and udc == '5100000.udc-controller':
            for filename in support['module_files']:
                try:
                    digest = hashlib.sha256(Path(filename).read_bytes()).hexdigest()
                except OSError:
                    continue
                if digest == FAULTY_SUNXI_UAC2_SHA256:
                    blocked_reason = 'UAC2 bind crashed on this KNULLI/Sunxi driver combination (missing USB IN endpoint)'
                    break
        return {'version': 1, 'config': str(config), 'gadget': str(gadget), 'function': str(function),
                'link': str(config / function.name), 'original_udc': read(gadget / 'UDC'),
                'udc': udc, 'udc_state': next(u['state'] for u in udcs if u['name'] == udc),
                'support': support, 'blocked_reason': blocked_reason,
                'links': self._links(gadget), 'function_created': False,
                'attributes': {prefix + '_' + a: str(v)
                               for prefix in ('c', 'p') for a, v in
                               (('chmask', (1 << channels) - 1), ('srate', rate), ('ssize', sample_bytes))}}

    @staticmethod
    def _links(gadget):
        return {str(p): str(p.resolve()) for p in (gadget / 'configs').glob('*/*') if p.is_symlink()}

    def activate(self, config, allow_disconnect=False, **options):
        if not allow_disconnect:
            raise GadgetError('Explicit --allow-disconnect required; USB/ADB will disconnect and BSP may hang')
        plan = self.plan(config, **options)
        if plan['blocked_reason']:
            raise GadgetError(plan['blocked_reason'])
        if plan['original_udc'] and plan['udc_state'] not in ('configured', 'addressed'):
            raise GadgetError('USB host must be connected before unbinding this BSP gadget')
        self.journal.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation also prevents two activation attempts sharing a journal.
        with self.journal.open('x', encoding='utf-8') as stream:
            json.dump(plan, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        gadget, function, link = (Path(plan[k]) for k in ('gadget', 'function', 'link'))
        try:
            if plan['original_udc']:
                (gadget / 'UDC').write_text('\n')
            function.mkdir()  # ConfigFS loads driver here; missing module alone is NOT proof.
            plan['function_created'] = True
            atomic_json(self.journal, plan)
            if any(not (function / a).is_file() for a in ATTRS):
                raise GadgetError('Unsupported Configuration: driver lacks duplex PCM attributes (legacy UAC1?)')
            for a, value in plan['attributes'].items():
                (function / a).write_text(value + '\n')
                if read(function / a) != value:
                    raise GadgetError('Driver rejected ' + a)
            link.symlink_to(function)
            (gadget / 'UDC').write_text(plan['udc'] + '\n')
        except BaseException as exc:
            try:
                self.restore()
            except Exception as rollback:
                raise GadgetError('Activation failed; restore journal retained: ' + str(rollback)) from exc
            raise
        return plan

    def restore(self):
        plan = json.loads(self.journal.read_text(encoding='utf-8'))
        gadget, config, function, link = (Path(plan[k]) for k in ('gadget', 'config', 'function', 'link'))
        base = self.system.path('/sys/kernel/config/usb_gadget').resolve()
        # Validate journal before any write/removal; never follow an arbitrary path.
        if (gadget.resolve().parent != base or config.resolve().parent != gadget / 'configs'
                or function.parent != gadget / 'functions'
                or function.name not in ('uac1.grainbernik', 'uac2.grainbernik')
                or link != config / function.name or function.is_symlink()
                or plan['original_udc'] not in ('', plan['udc'])
                or plan['udc'] not in [u['name'] for u in self.system.udcs()]):
            raise GadgetError('Invalid journal paths/UDC; refusing restoration')
        current = self._links(gadget)
        current.pop(str(link), None)
        if current != plan['links'] or read(gadget / 'UDC') not in ('', plan['udc']):
            raise GadgetError('Gadget changed by another owner; journal retained for manual recovery')
        if link.is_symlink() and link.resolve() != function:
            raise GadgetError('Function link ownership changed')
        if function.exists() and not plan.get('function_created'):
            raise GadgetError('Function ownership not recorded; refusing removal; journal retained')
        if read(gadget / 'UDC'):
            (gadget / 'UDC').write_text('\n')
        if link.is_symlink():
            link.unlink()
        if function.exists():
            function.rmdir()  # ConfigFS attributes are virtual; never recursive delete.
        if plan['original_udc']:
            (gadget / 'UDC').write_text(plan['original_udc'] + '\n')
        self.journal.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='/')
    parser.add_argument('--commands', action='store_true', help='also run bounded read-only ALSA/dmesg commands')
    parser.add_argument('--activate', metavar='CONFIG_DIRECTORY')
    parser.add_argument('--class', dest='kind', choices=['uac1', 'uac2'], default='uac2')
    parser.add_argument('--rate', type=int, default=48000)
    parser.add_argument('--channels', type=int, default=2)
    parser.add_argument('--sample-bytes', type=int, default=2)
    parser.add_argument('--journal', default=str(Path(__file__).with_name('gb_usb_gadget_state.json')))
    parser.add_argument('--restore', action='store_true')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--allow-disconnect', action='store_true')
    args = parser.parse_args()
    system = System(args.root)
    activation = Activation(system, args.journal)
    try:
        if args.restore:
            if not args.apply:
                parser.error('--restore requires --apply')
            activation.restore()
            result = {'restored': True}
        elif args.activate:
            options = dict(kind=args.kind, rate=args.rate, channels=args.channels, sample_bytes=args.sample_bytes)
            result = (activation.activate(args.activate, args.allow_disconnect, **options) if args.apply
                      else activation.plan(args.activate, **options))
        else:
            result = system.report(commands=args.commands)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (GadgetError, OSError, ValueError) as exc:
        parser.exit(1, str(exc) + '\n')


if __name__ == '__main__':
    main()
