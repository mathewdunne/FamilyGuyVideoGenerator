from __future__ import annotations

import random
from pathlib import Path


DEFAULT_BACKGROUNDS_DIR = Path("video_assets/backgrounds")
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}


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


def resolve_background(
    explicit_background: Path | None,
    backgrounds_dir: Path = DEFAULT_BACKGROUNDS_DIR,
) -> Path:
    if explicit_background is not None:
        return explicit_background
    return choose_random_background(backgrounds_dir)
