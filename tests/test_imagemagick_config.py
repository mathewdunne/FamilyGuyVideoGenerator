import importlib.util
import unittest

from stewie_explainer import renderer


class MoviePy2ConfigTests(unittest.TestCase):
    def test_moviepy_editor_import_path_is_not_used(self) -> None:
        self.assertIsNone(importlib.util.find_spec("moviepy.editor"))

    def test_imagemagick_configuration_was_removed(self) -> None:
        self.assertFalse(hasattr(renderer, "configure_imagemagick_for_moviepy"))


if __name__ == "__main__":
    unittest.main()
