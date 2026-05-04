from __future__ import annotations

import re
from pathlib import Path


def slugify(value: str, fallback: str = "explainer_video") -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or fallback


def unique_run_dir(out_dir: Path, base_slug: str) -> tuple[str, Path]:
    slug = slugify(base_slug)
    candidate = out_dir / slug
    if not candidate.exists():
        return slug, candidate

    suffix = 2
    while True:
        next_slug = f"{slug}_{suffix}"
        candidate = out_dir / next_slug
        if not candidate.exists():
            return next_slug, candidate
        suffix += 1

