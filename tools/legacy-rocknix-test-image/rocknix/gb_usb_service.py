"""Own the USB audio gadget on the dedicated ROCKNIX test image only."""
import json
from pathlib import Path
import signal
import sys
import time

APP = Path('/storage/roms/ports/grainbrick beta 1.0.1')
sys.path.insert(0, str(APP))
from gb_usb_audio import Settings, MODES
from gb_usb_gadget import Activation, GadgetError, System, read


def scaffold(system):
    # This service must never activate the defective stock KNULLI controller.
    if system.release != '7.1.2-gb-uac2':
        raise GadgetError('This service requires the dedicated 7.1.2-gb-uac2 image')
    base = system.path('/sys/kernel/config/usb_gadget')
    for gadget in base.iterdir():
        if gadget.name != 'grainbernik' and read(gadget / 'UDC'):
            raise GadgetError('USB controller belongs to ' + gadget.name)
    gadget = base / 'grainbernik'
    product = 'GrainBernik USB Audio'
    if gadget.exists():
        if read(gadget / 'strings/0x409/product') != product:
            raise GadgetError('Existing grainbernik gadget has another owner')
    else:
        gadget.mkdir()
        for name, value in {'idVendor': '0x1d6b', 'idProduct': '0x0104',
                            'bcdUSB': '0x0200', 'bcdDevice': '0x0101',
                            'bDeviceClass': '0xef', 'bDeviceSubClass': '2',
                            'bDeviceProtocol': '1'}.items():
            (gadget / name).write_text(value + '\n')
        strings = gadget / 'strings/0x409'
        strings.mkdir()
        for name, value in {'manufacturer': 'GrainBernik', 'product': product,
                            'serialnumber': 'GB-RG40XXH-UAC2-TEST'}.items():
            (strings / name).write_text(value + '\n')
        config = gadget / 'configs/c.1'
        config.mkdir()
        (config / 'bmAttributes').write_text('0xc0\n')
        (config / 'MaxPower').write_text('100\n')
        (config / 'strings/0x409').mkdir()
        (config / 'strings/0x409/configuration').write_text('Stereo USB Audio\n')
    return gadget / 'configs/c.1'


class Service:
    def __init__(self, system=None, settings=None, activation=None):
        self.system = system or System()
        self.settings = settings or Settings(APP / 'gb_usb_audio.json')
        self.activation = activation or Activation(self.system, '/run/grainbrick-usb-audio.json')

    def tick(self):
        data = self.settings.load()
        if data['mode'] != MODES[2]:
            if self.activation.journal.exists():
                self.activation.restore()
                print('USB audio disabled; original USB binding restored', flush=True)
            return
        if self.activation.journal.exists():
            plan = json.loads(self.activation.journal.read_text())
            if read(Path(plan['gadget']) / 'UDC') != plan['udc']:
                raise GadgetError('USB binding changed outside GrainBernik; disable the mode to restore')
            return
        config = scaffold(self.system)
        self.activation.activate(config, allow_disconnect=True, rate=48000)
        print('Stereo UAC2 enabled at 48000 Hz, 16 bit, capture and playback', flush=True)


def main():
    running = True

    def stop(_number, _frame):
        nonlocal running
        running = False

    for number in (signal.SIGTERM, signal.SIGINT):
        signal.signal(number, stop)
    service = Service()
    last_error = None
    try:
        while running:
            try:
                service.tick()
                last_error = None
            except (OSError, ValueError, GadgetError) as exc:
                if str(exc) != last_error:
                    print('USB audio: ' + str(exc), flush=True)
                    last_error = str(exc)
            time.sleep(1)
    finally:
        if service.activation.journal.exists():
            service.activation.restore()


if __name__ == '__main__':
    main()
