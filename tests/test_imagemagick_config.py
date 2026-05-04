import os
import unittest
from unittest.mock import patch

from stewie_explainer.renderer import _safe_convert_binary, configure_imagemagick_for_moviepy


class ImageMagickConfigTests(unittest.TestCase):
    @patch.dict(os.environ, {"IMAGEMAGICK_BINARY": "C:\\ImageMagick\\magick.exe"})
    @patch("stewie_explainer.renderer._apply_moviepy_settings")
    def test_env_binary_wins(self, apply_settings) -> None:
        binary = configure_imagemagick_for_moviepy()

        self.assertEqual(binary, "C:\\ImageMagick\\magick.exe")
        apply_settings.assert_called_once_with({"IMAGEMAGICK_BINARY": "C:\\ImageMagick\\magick.exe"})

    @patch.dict(os.environ, {}, clear=True)
    @patch("stewie_explainer.renderer.shutil.which")
    @patch("stewie_explainer.renderer._apply_moviepy_settings")
    def test_finds_magick_on_path(self, apply_settings, which) -> None:
        which.side_effect = lambda name: "C:\\Tools\\magick.exe" if name == "magick" else None

        binary = configure_imagemagick_for_moviepy()

        self.assertEqual(binary, "C:\\Tools\\magick.exe")
        apply_settings.assert_called_once_with({"IMAGEMAGICK_BINARY": "C:\\Tools\\magick.exe"})

    @patch("stewie_explainer.renderer.shutil.which", return_value="C:\\Windows\\System32\\convert.exe")
    def test_safe_convert_ignores_windows_system_convert(self, _which) -> None:
        self.assertIsNone(_safe_convert_binary())


if __name__ == "__main__":
    unittest.main()
