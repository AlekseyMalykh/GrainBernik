"""Install a PC's public SSH key in the offline image's writable partition."""
import argparse
from pathlib import Path
import struct
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('public_key', type=Path)
    parser.add_argument('work', type=Path)
    args = parser.parse_args()
    key = args.public_key.read_text().strip()
    assert key.startswith('ssh-ed25519 ') and len(key.split()) >= 2
    with args.image.open('rb') as image:
        mbr = image.read(512)
        assert mbr[510:] == b'\x55\xaa' and mbr[466] == 0x83
        start, sectors = struct.unpack_from('<II', mbr, 470)
        assert (start, sectors) == (4227072, 65536)
        image.seek(start * 512)
        part = args.work / 'STORAGE-with-ssh.img'
        assert not part.exists()
        part.write_bytes(image.read(sectors * 512))
    config = args.work / 'test-sshd.conf'
    config.write_text('SSH_ARGS="-o PasswordAuthentication=no -o KbdInteractiveAuthentication=no"\n')
    commands = ['mkdir /.ssh', 'set_inode_field /.ssh mode 040700',
                'mkdir /.cache', 'mkdir /.cache/services',
                'write ' + str(args.public_key.resolve()) + ' /.ssh/authorized_keys',
                'set_inode_field /.ssh/authorized_keys mode 0100600',
                'write ' + str(config.resolve()) + ' /.cache/services/sshd.conf']
    for command in commands:
        subprocess.run(['debugfs', '-w', '-R', command, str(part)], check=True)
    check = subprocess.run(['debugfs', '-R', 'cat /.ssh/authorized_keys', str(part)],
                           check=True, stdout=subprocess.PIPE, text=True)
    assert check.stdout.strip() == key
    subprocess.run(['e2fsck', '-fn', str(part)], check=True)
    with args.image.open('r+b') as image:
        image.seek(start * 512)
        assert image.write(part.read_bytes()) == sectors * 512
        image.flush()
    print('Installed public key and key-only SSH settings. Private key was not copied.')


if __name__ == '__main__':
    main()
