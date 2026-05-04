import unittest

from stewie_explainer.renderer import ensure_pillow_moviepy_compatibility

try:
    from PIL import Image
except ModuleNotFoundError:
    Image = None


class RendererCompatTests(unittest.TestCase):
    @unittest.skipIf(Image is None, "Pillow is not installed in this environment")
    def test_pillow_antialias_alias_exists_for_moviepy(self) -> None:
        ensure_pillow_moviepy_compatibility()

        self.assertTrue(hasattr(Image, "ANTIALIAS"))


if __name__ == "__main__":
    unittest.main()
