"""Real pipe backpressure and process cleanup; run on Linux (including ROCKNIX)."""
import multiprocessing
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'rg40xx-h-patch/grainbrick-beta'))
import gb_shutdown


def blocked_audio(aplay, ready, stop_event):
    # Like SDL's inherited signal handling, TERM cannot end this worker.
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    player = subprocess.Popen([aplay, '-c', 'import time; time.sleep(60)'], stdin=subprocess.PIPE, bufsize=0)
    ready.send(player.pid)
    try:
        os.write(player.stdin.fileno(), b'\0' * 65536)
        while not stop_event.is_set():
            os.write(player.stdin.fileno(), b'\0' * 65536)
    except BrokenPipeError:
        pass
    finally:
        player.stdin.close()
        player.wait()


@unittest.skipUnless(sys.platform == 'linux' and hasattr(os, 'pidfd_open'), 'Linux pidfds required')
class ShutdownTests(unittest.TestCase):
    def test_stalled_playback_and_term_resistant_worker_are_reaped(self):
        ctx = multiprocessing.get_context('fork')
        with tempfile.TemporaryDirectory() as directory:
            aplay = Path(directory) / 'aplay'
            aplay.symlink_to(sys.executable)
            reader, writer = ctx.Pipe(duplex=False)
            event = ctx.Event()
            process = ctx.Process(target=blocked_audio, args=(str(aplay), writer, event))
            process.start()
            self.assertTrue(reader.poll(3))
            player_pid = reader.recv()
            worker = SimpleNamespace(process=process, stop_event=event)

            def native_stop(worker):
                worker.stop_event.set()
                worker.process.join(timeout=0.05)
                worker.process.terminate()
                worker.process.join(timeout=0.05)
                return 'native result'

            try:
                self.assertEqual(gb_shutdown._stop_worker(worker, native_stop), 'native result')
                self.assertFalse(process.is_alive())
                deadline = time.monotonic() + 2
                while Path('/proc/%d' % player_pid).exists() and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertFalse(Path('/proc/%d' % player_pid).exists())
            finally:
                if process.is_alive():
                    os.kill(player_pid, signal.SIGKILL)
                    process.kill()
                    process.join(2)
                reader.close()
                writer.close()
                process.close()

    def test_worker_without_loaded_sample(self):
        self.assertEqual(gb_shutdown._stop_worker(SimpleNamespace(process=None), lambda w: 42), 42)

    def test_healthy_stop_retains_native_behavior(self):
        ctx = multiprocessing.get_context('fork')
        process = ctx.Process(target=lambda: None)
        process.start()
        try:
            worker = SimpleNamespace(process=process)
            gb_shutdown._stop_worker(worker, lambda w: w.process.join(timeout=2))
            self.assertEqual(process.exitcode, 0)
        finally:
            process.close()


if __name__ == '__main__':
    unittest.main()
