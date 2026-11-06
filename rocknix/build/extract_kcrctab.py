#!/usr/bin/env python3
"""Extract exported-symbol CRCs (Module.symvers format) from an arm64 Image.

ROCKNIX is built with GCC 16; a local GCC 13 build computes different
genksyms CRCs for the same Linux 7.2 source, so modules are rejected with
"disagrees about version of symbol". This reads the official kernel's own
table instead: Linux 7.x keeps one sorted __ksymtab (12-byte PREL32 entries:
value, name, namespace), followed by __kcrctab (u32 per symbol) and a
per-symbol flags byte (bit 0 = GPL-only).

Usage: python3 extract_kcrctab.py /flash/KERNEL official.symvers
(copy /flash/KERNEL from the console first).
"""
import re
import struct
import sys

IDENT = re.compile(rb'[A-Za-z_][A-Za-z0-9_.$]*')
NAMESPACE = re.compile(rb'[A-Za-z0-9_:.-]+')


def main(image_path, out_path):
    data = open(image_path, 'rb').read()
    size = len(data)

    def string_at(offset):
        if not 0 < offset < size:
            return None
        end = data.find(b'\0', offset)
        return data[offset:end] if 0 <= end - offset <= 200 else None

    def entry(position):
        name_off, ns_off = struct.unpack_from('<ii', data, position + 4)
        name = string_at(position + 4 + name_off)
        namespace = string_at(position + 8 + ns_off)
        if name is None or namespace is None or not IDENT.fullmatch(name):
            return None
        if namespace and not NAMESPACE.fullmatch(namespace):
            return None
        return name.decode(), namespace.decode()

    found = {}
    for position in range(0, size - 12, 4):
        value = entry(position)
        if value:
            found[position] = value
    best = []
    for position in sorted(found):
        if position - 12 in found:
            continue
        chain = [position]
        while chain[-1] + 12 in found:
            chain.append(chain[-1] + 12)
        if len(chain) > len(best):
            best = chain
    names = [found[p][0] for p in best]
    if len(best) < 1000 or names != sorted(names):
        raise SystemExit('ksymtab not found (largest sorted run: %d entries)' % len(best))
    count, end = len(best), best[-1] + 12
    crcs = struct.unpack_from('<%dI' % count, data, end)
    flags = data[end + 4 * count:end + 5 * count]
    with open(out_path, 'w', encoding='utf-8') as out:
        for i, position in enumerate(best):
            name, namespace = found[position]
            kind = 'EXPORT_SYMBOL_GPL' if flags[i] & 1 else 'EXPORT_SYMBOL'
            out.write('0x%08x\t%s\tvmlinux\t%s\t%s\n' % (crcs[i], name, kind, namespace))
    print('%d symbols written to %s' % (count, out_path))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
