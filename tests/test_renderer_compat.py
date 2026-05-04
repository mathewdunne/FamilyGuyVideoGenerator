import unittest

from stewie_explainer.models import DialogueTurn, ExplainerScript
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

    def test_empty_subtitles_do_not_create_clips(self) -> None:
        self.assertEqual(
            renderer._word_by_word_subtitles("", 0.0, 1.0, 1080, 1920),
            [],
        )

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


if __name__ == "__main__":
    unittest.main()
