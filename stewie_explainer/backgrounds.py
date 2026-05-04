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
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError(
            "Downloading YouTube backgrounds requires yt-dlp. "
            "Install dependencies with: python -m pip install -r requirements.txt"
        ) from exc

    backgrounds_dir.mkdir(parents=True, exist_ok=True)
    downloaded_paths: list[Path] = []

    def remember_download(download: dict) -> None:
        if download.get("status") == "finished" and download.get("filename"):
            downloaded_paths.append(Path(download["filename"]))

    options = {
        "format": "bestvideo[ext=mp4]/bestvideo/best[ext=mp4]/best",
        "noplaylist": True,
        "outtmpl": str(backgrounds_dir / "%(title).200B [%(id)s].%(ext)s"),
        "progress_hooks": [remember_download],
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(options) as downloader:
        info = downloader.extract_info(url, download=True)
        prepared_path = Path(downloader.prepare_filename(info))

    if downloaded_paths:
        downloaded_path = downloaded_paths[-1]
    else:
        downloaded_path = prepared_path

    if downloaded_path.suffix.lower() not in VIDEO_EXTENSIONS:
        raise ValueError(f"Downloaded background is not a supported video file: {downloaded_path}")
    if not downloaded_path.exists():
        raise FileNotFoundError(f"Downloaded background file was not created: {downloaded_path}")
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
