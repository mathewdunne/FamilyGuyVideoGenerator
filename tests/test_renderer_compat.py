import sys
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from stewie_explainer.models import DialogueTurn, ExplainerScript, WordTiming
from stewie_explainer import renderer


def make_script_with_missing_audio() -> ExplainerScript:
    return ExplainerScript(
        title="Renderer Compatibility",
        slug="renderer_compatibility",
        target_duration_seconds=45,
        turns=[
            DialogueTurn("peter", "One"),
            DialogueTurn("stewie", "Two"),
            DialogueTurn("peter", "Three"),
            DialogueTurn("stewie", "Four"),
            DialogueTurn("peter", "Five"),
            DialogueTurn("stewie", "Six"),
            DialogueTurn("peter", "Seven"),
            DialogueTurn("stewie", "Eight"),
        ],
    )


class RendererCompatTests(unittest.TestCase):
    def test_pillow_antialias_shim_was_removed(self) -> None:
        self.assertFalse(hasattr(renderer, "ensure_pillow_moviepy_compatibility"))

    def test_missing_subtitle_timings_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "word timings"):
            renderer._word_by_word_subtitles([], 0.0, 1080, 1920)

    def test_subtitles_use_explicit_word_timings(self) -> None:
        class FakeImageClip:
            def __init__(self, image):
                self.image = image

            def with_start(self, start):
                self.start = start
                return self

            def with_duration(self, duration):
                self.duration = duration
                return self

            def with_position(self, position):
                self.position = position
                return self

            def with_effects(self, effects):
                self.effects = effects
                return self

            def close(self):
                pass

        fake_moviepy = types.SimpleNamespace(
            ImageClip=FakeImageClip,
            vfx=types.SimpleNamespace(
                FadeIn=lambda duration: ("fadein", duration),
                FadeOut=lambda duration: ("fadeout", duration),
            ),
        )
        with patch.dict(sys.modules, {"moviepy": fake_moviepy}), patch(
            "stewie_explainer.renderer._subtitle_image",
            return_value=object(),
        ):
            clips = renderer._word_by_word_subtitles(
                [WordTiming("Hello", 0.2, 0.5), WordTiming("there", 0.55, 0.9)],
                1.0,
                1080,
                1920,
            )

        try:
            self.assertEqual(len(clips), 2)
            self.assertAlmostEqual(clips[0].start, 1.2)
            self.assertAlmostEqual(clips[0].duration, 0.3)
            self.assertAlmostEqual(clips[1].start, 1.55)
            self.assertAlmostEqual(clips[1].duration, 0.35)
        finally:
            for clip in clips:
                clip.close()

    def test_subtitle_font_size_shrinks_for_long_words(self) -> None:
        normal = renderer._subtitle_font_size(1080, 1920, "robot")
        long_word = renderer._subtitle_font_size(
            1080,
            1920,
            "supercalifragilisticexpialidocious",
        )

        self.assertLess(long_word, normal)

    def test_subtitle_image_keeps_transparent_padding(self) -> None:
        image = renderer._subtitle_image("HAVE", 104)

        self.assertEqual(image.shape[2], 4)
        self.assertTrue((image[0, :, 3] == 0).all())
        self.assertTrue((image[-1, :, 3] == 0).all())

    def test_audio_timeline_rejects_missing_audio(self) -> None:
        with self.assertRaisesRegex(ValueError, "Missing audio"):
            renderer._audio_timeline(make_script_with_missing_audio(), object)

    def test_character_positions_put_stewie_left_and_peter_right(self) -> None:
        class FakeCharacterClip:
            def __init__(self, image_path):
                self.image_path = str(image_path)
                self.base_w, self.base_h = (414, 602) if "peter" in self.image_path else (781, 987)

            def with_start(self, start):
                self.start = start
                return self

            def with_duration(self, duration):
                self.duration = duration
                return self

            def resized(self, height):
                self.h = height
                self.w = int(self.base_w * (height / self.base_h))
                return self

            def with_position(self, position):
                self.position = position
                return self

        with TemporaryDirectory() as tmp:
            assets_dir = Path(tmp)
            (assets_dir / "peter.png").touch()
            (assets_dir / "stewie.png").touch()

            peter = renderer._character_clip(
                DialogueTurn("peter", "Answer"),
                0,
                1,
                assets_dir,
                1080,
                1920,
                FakeCharacterClip,
            )
            stewie = renderer._character_clip(
                DialogueTurn("stewie", "Question"),
                0,
                1,
                assets_dir,
                1080,
                1920,
                FakeCharacterClip,
            )

        self.assertEqual(stewie.position[0], 43)
        self.assertGreater(peter.position[0], 1080 // 2)
        self.assertLess(stewie.h, peter.h)


if __name__ == "__main__":
    unittest.main()
