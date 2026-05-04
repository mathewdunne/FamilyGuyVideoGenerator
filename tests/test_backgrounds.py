import random
import tempfile
import unittest
from pathlib import Path

from stewie_explainer.backgrounds import (
    choose_random_background,
    list_background_videos,
    resolve_background,
)


class BackgroundTests(unittest.TestCase):
    def test_lists_supported_background_video_formats(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.mp4").write_bytes(b"")
            (root / "b.webm").write_bytes(b"")
            (root / "c.txt").write_text("nope", encoding="utf-8")

            videos = list_background_videos(root)

            self.assertEqual([path.name for path in videos], ["a.mp4", "b.webm"])

    def test_choose_random_background_uses_supplied_rng(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.mp4").write_bytes(b"")
            (root / "b.mp4").write_bytes(b"")

            choice = choose_random_background(root, rng=random.Random(0))

            self.assertEqual(choice.name, "b.mp4")

    def test_choose_random_background_errors_when_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(FileNotFoundError, "No background videos found"):
                choose_random_background(Path(tmp))

    def test_resolve_background_prefers_explicit_path(self) -> None:
        explicit = Path("custom.mp4")

        self.assertEqual(resolve_background(explicit, Path("missing")), explicit)


if __name__ == "__main__":
    unittest.main()
