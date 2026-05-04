import unittest
import tempfile
from pathlib import Path

from stewie_explainer.models import DialogueTurn
from stewie_explainer.subtitles import WhisperXSubtitleAligner, word_timings_from_aligned_result


class FakeWhisperX:
    def __init__(self) -> None:
        self.transcript = None

    def load_audio(self, path):
        return [0.0] * 16000

    def align(self, transcript, align_model, align_metadata, audio, device, return_char_alignments=False):
        self.transcript = transcript
        return {
            "segments": [
                {
                    "words": [
                        {"word": "Known", "start": 0.1, "end": 0.3},
                        {"word": "script", "start": 0.35, "end": 0.8},
                    ]
                }
            ]
        }


class SubtitleAlignmentTests(unittest.TestCase):
    def test_whisperx_aligner_uses_script_text_as_transcript(self) -> None:
        fake_whisperx = FakeWhisperX()
        aligner = WhisperXSubtitleAligner()
        aligner._whisperx = fake_whisperx
        aligner._align_model = object()
        aligner._align_metadata = object()

        with tempfile.TemporaryDirectory() as tmp:
            audio_path = Path(tmp) / "line.mp3"
            audio_path.write_bytes(b"audio")

            timings = aligner.align_turn(DialogueTurn("peter", "Known script", audio_path=audio_path))

        self.assertEqual(fake_whisperx.transcript, [{"text": "Known script", "start": 0.0, "end": 1.0}])
        self.assertEqual([timing.word for timing in timings], ["Known", "script"])

    def test_word_timings_use_script_words_with_aligned_timestamps(self) -> None:
        aligned = {
            "segments": [
                {
                    "words": [
                        {"word": "hello", "start": 0.1, "end": 0.3},
                        {"word": "world", "start": 0.35, "end": 0.7},
                    ]
                }
            ]
        }

        timings = word_timings_from_aligned_result("Hello, world!", aligned)

        self.assertEqual([timing.word for timing in timings], ["Hello,", "world!"])
        self.assertEqual([(timing.start, timing.end) for timing in timings], [(0.1, 0.3), (0.35, 0.7)])

    def test_word_count_mismatch_raises_instead_of_guessing(self) -> None:
        aligned = {
            "segments": [
                {
                    "words": [
                        {"word": "different", "start": 0.1, "end": 0.3},
                    ]
                }
            ]
        }

        with self.assertRaisesRegex(RuntimeError, "returned 1 words for 2 script words"):
            word_timings_from_aligned_result("Hello there", aligned)


if __name__ == "__main__":
    unittest.main()
