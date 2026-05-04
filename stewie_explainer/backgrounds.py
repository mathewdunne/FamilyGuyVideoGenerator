from __future__ import annotations

import random
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse


DEFAULT_BACKGROUNDS_DIR = Path("video_assets/backgrounds")
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}

Downloader = Callable[[str, Path], Path]


def list_background_videos(backgrounds_dir: Path) -> list[Path]:
    if not backgrounds_dir.exists():
        return []
    return sorted(
        path
        for path in backgrounds_dir.iterdir()
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    )


def choose_random_background(
    backgrounds_dir: Path = DEFAULT_BACKGROUNDS_DIR,
    rng: random.Random | None = None,
) -> Path:
    videos = list_background_videos(backgrounds_dir)
    if not videos:
        supported = ", ".join(sorted(VIDEO_EXTENSIONS))
        raise FileNotFoundError(
            f"No background videos found in {backgrounds_dir}. "
            f"Add one of these formats: {supported}, or pass --background explicitly."
        )
    chooser = rng.choice if rng is not None else random.choice
    return chooser(videos)


def is_youtube_url(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        return False
    return parsed.netloc.lower() in YOUTUBE_HOSTS


def download_youtube_background(url: str, backgrounds_dir: Path = DEFAULT_BACKGROUNDS_DIR) -> Path:
    try:
        from pytube import YouTube
    except ImportError as exc:
        raise RuntimeError(
            "Downloading YouTube backgrounds requires pytube. "
            "Install dependencies with: python -m pip install -r requirements.txt"
        ) from exc

    backgrounds_dir.mkdir(parents=True, exist_ok=True)
    youtube = YouTube(url)
    stream = (
        youtube.streams.filter(progressive=True, file_extension="mp4")
        .order_by("resolution")
        .desc()
        .first()
    )
    if stream is None:
        raise ValueError(f"No progressive MP4 stream found for YouTube URL: {url}")

    downloaded_path = Path(stream.download(output_path=str(backgrounds_dir)))
    if downloaded_path.suffix.lower() not in VIDEO_EXTENSIONS:
        raise ValueError(f"Downloaded background is not a supported video file: {downloaded_path}")
    return downloaded_path


def resolve_background(
    explicit_background: str | Path | None,
    backgrounds_dir: Path = DEFAULT_BACKGROUNDS_DIR,
    youtube_downloader: Downloader = download_youtube_background,
) -> Path:
    if explicit_background is not None:
        background_value = str(explicit_background)
        if is_youtube_url(background_value):
            return youtube_downloader(background_value, backgrounds_dir)
        return Path(explicit_background)
    return choose_random_background(backgrounds_dir)
