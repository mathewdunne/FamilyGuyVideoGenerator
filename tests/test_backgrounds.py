import random
import tempfile
import unittest
from pathlib import Path

from stewie_explainer.backgrounds import (
    choose_random_background,
    is_youtube_url,
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

    def test_detects_youtube_urls(self) -> None:
        self.assertTrue(is_youtube_url("https://www.youtube.com/watch?v=abc123"))
        self.assertTrue(is_youtube_url("https://youtu.be/abc123"))
        self.assertFalse(is_youtube_url("https://example.com/video.mp4"))
        self.assertFalse(is_youtube_url("video_assets/backgrounds/demo.mp4"))

    def test_resolve_background_downloads_youtube_url_to_backgrounds_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            backgrounds_dir = Path(tmp)
            downloaded = backgrounds_dir / "downloaded.mp4"
            calls = []

            def fake_downloader(url: str, target_dir: Path) -> Path:
                calls.append((url, target_dir))
                return downloaded

            result = resolve_background(
                "https://www.youtube.com/watch?v=abc123",
                backgrounds_dir,
                youtube_downloader=fake_downloader,
            )

            self.assertEqual(result, downloaded)
            self.assertEqual(
                calls,
                [("https://www.youtube.com/watch?v=abc123", backgrounds_dir)],
            )

    def test_resolve_background_keeps_local_path_string(self) -> None:
        self.assertEqual(
            resolve_background("video_assets/backgrounds/demo.mp4", Path("missing")),
            Path("video_assets/backgrounds/demo.mp4"),
        )


if __name__ == "__main__":
    unittest.main()
