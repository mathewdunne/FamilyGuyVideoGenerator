from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .article import ArticleSource
from .models import ExplainerScript
from .slugging import unique_run_dir


def create_run_directory(out_dir: Path, requested_slug: str) -> tuple[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    slug, run_dir = unique_run_dir(out_dir, requested_slug)
    run_dir.mkdir(parents=True)
    (run_dir / "audio").mkdir()
    return slug, run_dir


def write_prompt_file(
    run_dir: Path,
    slug: str,
    prompt: str,
    article: ArticleSource | None,
) -> Path:
    path = run_dir / f"{slug}_prompt.md"
    lines = ["# Original Prompt", "", prompt.strip() or "(none)", ""]
    if article is not None:
        lines.extend(["# Source Article", "", f"URL: {article.url}", ""])
        if article.title:
            lines.extend([f"Title: {article.title}", ""])
        if article.text:
            lines.extend(["## Extracted Text", "", article.text.strip(), ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_script_files(run_dir: Path, slug: str, script: ExplainerScript) -> tuple[Path, Path]:
    json_path = run_dir / f"{slug}_script.json"
    md_path = run_dir / f"{slug}_script.md"

    json_path.write_text(
        json.dumps(script.to_dict(include_audio=True), indent=2),
        encoding="utf-8",
    )

    lines = [f"# {script.title}", "", f"Target duration: {script.target_duration_seconds}s", ""]
    for turn in script.turns:
        lines.append(f"**{turn.speaker.title()}:** {turn.text}")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def write_manifest(
    run_dir: Path,
    slug: str,
    data: dict[str, Any],
) -> Path:
    manifest_path = run_dir / f"{slug}_manifest.json"
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        **data,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path

