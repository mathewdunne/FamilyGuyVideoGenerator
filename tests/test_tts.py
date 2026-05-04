import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from io import BytesIO

from stewie_explainer.models import DialogueTurn, ExplainerScript
from stewie_explainer.tts import FishAudioProvider


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def read(self) -> bytes:
        return b"fake mp3"


class TTSTests(unittest.TestCase):
    def test_from_env_reports_missing_fish_audio_settings(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "FISH_AUDIO_API_KEY"):
                FishAudioProvider.from_env()

    @patch("stewie_explainer.tts.urlopen", return_value=FakeResponse())
    def test_fish_audio_request_uses_speaker_voice_and_writes_audio(self, fake_urlopen) -> None:
        provider = FishAudioProvider(
            api_key="key",
            peter_voice_id="peter_voice",
            stewie_voice_id="stewie_voice",
            model="s2-pro",
        )
        script = ExplainerScript(
            title="PID",
            slug="pid",
            target_duration_seconds=40,
            turns=[
                DialogueTurn("peter", "Line one."),
                DialogueTurn("stewie", "Line two."),
                DialogueTurn("peter", "Line three."),
                DialogueTurn("stewie", "Line four."),
                DialogueTurn("peter", "Line five."),
                DialogueTurn("stewie", "Line six."),
                DialogueTurn("peter", "Line seven."),
                DialogueTurn("stewie", "Line eight."),
            ],
        )

        with tempfile.TemporaryDirectory() as tmp:
            paths = provider.synthesize_script(script, Path(tmp))

            self.assertEqual(len(paths), 8)
            self.assertEqual(paths[0].read_bytes(), b"fake mp3")
            self.assertEqual(script.turns[1].audio_path, paths[1])

        first_request = fake_urlopen.call_args_list[0].args[0]
        second_request = fake_urlopen.call_args_list[1].args[0]
        first_payload = json.loads(first_request.data.decode("utf-8"))
        second_payload = json.loads(second_request.data.decode("utf-8"))

        self.assertEqual(first_payload["reference_id"], "peter_voice")
        self.assertEqual(second_payload["reference_id"], "stewie_voice")
        self.assertEqual(first_request.get_header("Authorization"), "Bearer key")
        self.assertEqual(first_request.get_header("Model"), "s2-pro")

    @patch("stewie_explainer.tts.urlopen")
    def test_fish_audio_402_explains_api_billing_boundary(self, fake_urlopen) -> None:
        fake_urlopen.side_effect = HTTPError(
            url="https://api.fish.audio/v1/tts",
            code=402,
            msg="Payment Required",
            hdrs=None,
            fp=BytesIO(b'{"message":"insufficient balance"}'),
        )
        provider = FishAudioProvider(
            api_key="key",
            peter_voice_id="peter_voice",
            stewie_voice_id="stewie_voice",
        )

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "API billing"):
                provider.synthesize_turn(DialogueTurn("peter", "Line one."), Path(tmp) / "line.mp3")


if __name__ == "__main__":
    unittest.main()
