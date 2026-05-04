import random
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from stewie_explainer.backgrounds import (
    choose_random_background,
    download_youtube_background,
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

    def test_download_youtube_background_prefers_video_only_formats(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            downloaded = Path(tmp) / "downloaded.mp4"
            captured_options = {}

            class FakeYoutubeDL:
                def __init__(self, options: dict) -> None:
                    captured_options.update(options)

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, traceback) -> None:
                    return None

                def extract_info(self, url: str, download: bool) -> dict:
                    downloaded.write_bytes(b"video")
                    for hook in captured_options["progress_hooks"]:
                        hook({"status": "finished", "filename": str(downloaded)})
                    return {"id": "abc123", "ext": "mp4"}

                def prepare_filename(self, info: dict) -> str:
                    return str(downloaded)

            fake_yt_dlp = types.SimpleNamespace(YoutubeDL=FakeYoutubeDL)
            with patch.dict(sys.modules, {"yt_dlp": fake_yt_dlp}):
                result = download_youtube_background(
                    "https://www.youtube.com/watch?v=abc123",
                    Path(tmp),
                )

            self.assertEqual(result, downloaded)
            self.assertEqual(
                captured_options["format"],
                "bestvideo[ext=mp4]/bestvideo/best[ext=mp4]/best",
            )


if __name__ == "__main__":
    unittest.main()
