import tempfile
import unittest
from pathlib import Path

from stewie_explainer.models import DialogueTurn, ExplainerScript
from stewie_explainer.pipeline import resolve_resume_audio_path, run_generation, run_render_only
from stewie_explainer.renderer import VideoRenderer
from stewie_explainer.transcript import TranscriptGenerator
from stewie_explainer.tts import TTSProvider


def make_script() -> ExplainerScript:
    return ExplainerScript(
        title="Command-Based Commands",
        slug="command_based_commands",
        target_duration_seconds=45,
        turns=[
            DialogueTurn("peter", "Commands are little robot jobs."),
            DialogueTurn("stewie", "Tiny job descriptions with wheels, lovely."),
            DialogueTurn("peter", "Subsystems own motors and sensors."),
            DialogueTurn("stewie", "So commands politely borrow the hardware."),
            DialogueTurn("peter", "The scheduler runs commands when buttons fire."),
            DialogueTurn("stewie", "And interrupts the chaos before it becomes modern art."),
            DialogueTurn("peter", "Keep each command focused and testable."),
            DialogueTurn("stewie", "That is how your robot avoids interpretive dance."),
        ],
    )


class FakeTranscriptGenerator(TranscriptGenerator):
    def generate(self, prompt, article=None):
        return make_script()


class FakeTTSProvider(TTSProvider):
    def synthesize_turn(self, turn, output_path):
        output_path.write_bytes(b"audio")
        return output_path


class FakeRenderer(VideoRenderer):
    def render(self, script, background_path, output_path):
        output_path.write_bytes(b"video")
        return output_path


class PipelineTests(unittest.TestCase):
    def test_run_generation_writes_expected_artifacts_with_fake_services(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            background = tmp_path / "background.mp4"
            background.write_bytes(b"background")

            result = run_generation(
                prompt="Explain command-based programming.",
                url=None,
                background_path=background,
                out_dir=tmp_path / "outputs",
                transcript_generator=FakeTranscriptGenerator(),
                tts_provider=FakeTTSProvider(),
                renderer=FakeRenderer(),
            )

            self.assertEqual(result.slug, "command_based_commands")
            self.assertTrue((result.run_dir / "command_based_commands_prompt.md").exists())
            self.assertTrue((result.run_dir / "command_based_commands_script.json").exists())
            self.assertTrue((result.run_dir / "command_based_commands_script.md").exists())
            self.assertTrue((result.run_dir / "command_based_commands_manifest.json").exists())
            self.assertEqual(result.video_path.read_bytes(), b"video")
            self.assertEqual(len(list((result.run_dir / "audio").glob("*.mp3"))), 8)

    def test_run_render_only_reuses_saved_script_and_audio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            background = tmp_path / "background.mp4"
            background.write_bytes(b"background")

            initial = run_generation(
                prompt="Explain command-based programming.",
                url=None,
                background_path=background,
                out_dir=tmp_path / "outputs",
                transcript_generator=FakeTranscriptGenerator(),
                tts_provider=FakeTTSProvider(),
                renderer=FakeRenderer(),
            )
            initial.video_path.unlink()

            result = run_render_only(
                run_dir=initial.run_dir,
                background_path=background,
                renderer=FakeRenderer(),
            )

            self.assertEqual(result.video_path, initial.video_path)
            self.assertEqual(result.video_path.read_bytes(), b"video")

    def test_resolve_resume_audio_path_handles_repo_relative_saved_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "outputs" / "pid_swerve_steering"
            audio_dir = run_dir / "audio"
            audio_dir.mkdir(parents=True)
            expected = audio_dir / "01_peter.mp3"
            expected.write_bytes(b"audio")
            saved_path = Path("outputs") / "pid_swerve_steering" / "audio" / "01_peter.mp3"

            resolved = resolve_resume_audio_path(run_dir, saved_path, 1, "peter")

            self.assertEqual(resolved, expected)


if __name__ == "__main__":
    unittest.main()
