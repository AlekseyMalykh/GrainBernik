"""Real WAV headers from interrupted USB capture, without allocating large PCM."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'rg40xx-h-patch/grainbrick-beta'))
from gb_recording import finalize_wav


class RecordingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'recording.wav'
        self.pcm = struct.pack('<hh', 1234, -2345) * 4800
        with wave.open(str(self.path), 'wb') as writer:
            writer.setparams((2, 2, 48000, 0, 'NONE', ''))
            writer.writeframes(self.pcm)

    def patch_lengths(self, length):
        with self.path.open('r+b') as stream:
            stream.seek(4)
            stream.write(struct.pack('<I', (length + 36) & 0xffffffff))
            stream.seek(40)
            stream.write(struct.pack('<I', length))

    def test_arecord_placeholder_becomes_actual_frame_count_and_pcm_is_preserved(self):
        self.patch_lengths(0x80000000)
        self.assertEqual(finalize_wav(self.path), (4800, True))
        with wave.open(str(self.path)) as reader:
            self.assertEqual(reader.getnframes(), 4800)
            self.assertEqual(reader.readframes(reader.getnframes()), self.pcm)

    def test_zero_and_uint32_max_placeholders(self):
        for length in (0, 0xffffffff):
            with self.subTest(length=length):
                self.patch_lengths(length)
                self.assertEqual(finalize_wav(self.path), (4800, True))

    def test_valid_wav_is_unchanged(self):
        original = self.path.read_bytes()
        self.assertEqual(finalize_wav(self.path), (4800, False))
        self.assertEqual(self.path.read_bytes(), original)

    def test_trailing_metadata_is_not_audio(self):
        with self.path.open('ab') as stream:
            stream.write(b'LIST\x04\x00\x00\x00INFO')
        self.assertEqual(finalize_wav(self.path), (4800, True))
        with wave.open(str(self.path)) as reader:
            self.assertEqual(reader.readframes(9999), self.pcm)

    def test_empty_recording_is_rejected_without_modification(self):
        self.path.write_bytes(self.path.read_bytes()[:44])
        self.patch_lengths(0x80000000)
        original = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'no complete audio frames'):
            finalize_wav(self.path)
        self.assertEqual(self.path.read_bytes(), original)

    def test_invalid_file_is_rejected_without_modification(self):
        self.path.write_bytes(b'not a WAV file')
        with self.assertRaises(ValueError):
            finalize_wav(self.path)
        self.assertEqual(self.path.read_bytes(), b'not a WAV file')


if __name__ == '__main__':
    unittest.main()
