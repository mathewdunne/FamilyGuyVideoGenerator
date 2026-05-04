import shutil
import unittest


class RendererAvailabilityTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg is required for real render smoke tests")
    def test_ffmpeg_available_for_render_smoke_tests(self) -> None:
        self.assertIsNotNone(shutil.which("ffmpeg"))


if __name__ == "__main__":
    unittest.main()

