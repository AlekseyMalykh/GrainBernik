"""Read a KNULLI GPT/Android boot image without mounting/writing the image.

Optional --module accepts a separately extracted UAC module for provenance.
This audits an IMAGE, never claims to describe the running handheld.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import struct

FLAGS = ('USB_GADGET', 'CONFIGFS_FS', 'USB_LIBCOMPOSITE', 'USB_CONFIGFS',
         'USB_CONFIGFS_F_UAC1', 'USB_CONFIGFS_F_UAC2', 'USB_F_UAC2',
         'USB_CONFIGFS_F_AUDIO_SRC', 'SND_USB_AUDIO', 'SND_ALOOP', 'USB_SUNXI_UDC0')


def audit(path, module=None):
    path = Path(path)
    with path.open('rb') as stream:
        stream.seek(512)
        header = stream.read(512)
        if header[:8] != b'EFI PART':
            raise ValueError('Expected GPT image with 512-byte sectors')
        lba, count, size = struct.unpack_from('<QII', header, 72)
        if not 128 <= size <= 4096 or count > 4096:
            raise ValueError('Invalid GPT entry dimensions')
        stream.seek(lba * 512)
        partitions = []
        for index in range(count):
            entry = stream.read(size)
            if any(entry[:16]):
                first, last = struct.unpack_from('<QQ', entry, 32)
                partitions.append({'name': entry[56:128].decode('utf-16le').rstrip('\0'),
                                   'first_lba': first, 'last_lba': last})
        boot = next(p for p in partitions if p['name'] == 'boot')
        length = (boot['last_lba'] - boot['first_lba'] + 1) * 512
        if not 0 < length <= 64 * 1024 * 1024:
            raise ValueError('Unexpected boot partition size')
        stream.seek(boot['first_lba'] * 512)
        data = stream.read(length)
    if data[:8] != b'ANDROID!':
        raise ValueError('Expected Android boot header')
    kernel_size = struct.unpack_from('<I', data, 8)[0]
    page_size = struct.unpack_from('<I', data, 36)[0]
    if page_size < 512 or kernel_size > len(data) - page_size:
        raise ValueError('Invalid Android kernel dimensions')
    kernel = data[page_size:page_size + kernel_size]
    start, end = kernel.find(b'IKCFG_ST'), kernel.find(b'IKCFG_ED')
    if start < 0 or end < start:
        raise ValueError('Embedded kernel config unavailable')
    config = gzip.decompress(kernel[start + 8:end])
    text = config.decode()
    flags = {}
    for flag in FLAGS:
        match = re.search(r'^CONFIG_' + flag + r'=(y|m)$', text, re.M)
        flags[flag] = match[1] if match else ('n' if '# CONFIG_' + flag + ' is not set' in text else 'unknown')
    version = re.search(rb'Linux version [^\0\n]+', kernel)
    result = {'scope': 'local firmware image only; installed device not inspected',
              'image': path.name, 'partitions': partitions,
              'kernel_version': version[0].decode(errors='replace') if version else None,
              'kernel_sha256': hashlib.sha256(kernel).hexdigest(),
              'embedded_config_sha256': hashlib.sha256(config).hexdigest(), 'flags': flags}
    if module:
        module = Path(module)
        data = module.read_bytes()
        fields = [s.decode() for s in re.findall(rb'[ -~]{4,}', data)
                  if s.startswith((b'vermagic=', b'depends=', b'alias=', b'srcversion='))]
        result['separately_shipped_module'] = {
            'name': module.name, 'sha256': hashlib.sha256(data).hexdigest(), 'modinfo': fields,
            'required_attributes_found': [a for a in ('c_chmask', 'p_chmask', 'c_srate', 'p_srate', 'c_ssize', 'p_ssize')
                                          if a.encode() + b'\0' in data],
            'loadability': 'unknown until tested on the running kernel',
            'note': 'Embedded configuration can disagree with separately shipped modules.'}
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image')
    parser.add_argument('--module')
    parser.add_argument('--output')
    args = parser.parse_args()
    result = json.dumps(audit(args.image, args.module), indent=2) + '\n'
    if args.output:
        Path(args.output).write_text(result, encoding='utf-8')
    else:
        print(result, end='')
