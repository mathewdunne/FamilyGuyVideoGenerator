from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .article import ArticleSource, fetch_article
from .artifacts import (
    create_run_directory,
    write_manifest,
    write_prompt_file,
    write_script_files,
)
from .models import ExplainerScript, script_from_dict
from .renderer import VideoRenderer
from .transcript import TranscriptGenerator
from .tts import TTSProvider


@dataclass
class PipelineResult:
    slug: str
    run_dir: Path
    video_path: Path
    manifest_path: Path


def run_generation(
    prompt: str,
    url: str | None,
    background_path: Path,
    out_dir: Path,
    transcript_generator: TranscriptGenerator,
    tts_provider: TTSProvider,
    renderer: VideoRenderer,
    status: Callable[[str], None] | None = None,
) -> PipelineResult:
    def report(message: str) -> None:
        if status is not None:
            status(message)

    if not prompt.strip() and not url:
        raise ValueError("Provide --prompt, --url, or both")

    report("Fetching article source" if url else "No article URL supplied")
    article: ArticleSource | None = fetch_article(url) if url else None
    if article is not None:
        report(f"Extracted {len(article.text)} characters from article")

    report("Generating Peter/Stewie script with Claude")
    script = transcript_generator.generate(prompt=prompt, article=article)
    report(f"Script generated: {script.title} ({len(script.turns)} turns)")

    slug, run_dir = create_run_directory(out_dir, script.slug or script.title)
    script.slug = slug
    report(f"Created run folder: {run_dir}")

    report("Writing original prompt artifact")
    prompt_path = write_prompt_file(run_dir, slug, prompt, article)
    report("Generating voice audio")
    audio_paths = tts_provider.synthesize_script(script, run_dir / "audio", status=report)
    report("Writing script artifacts")
    script_json_path, script_md_path = write_script_files(run_dir, slug, script)

    video_path = run_dir / f"{slug}.mp4"
    report(f"Rendering video with background: {background_path}")
    renderer.render(script, background_path, video_path)
    report(f"Rendered video: {video_path}")

    report("Writing manifest")
    manifest_path = write_manifest(
        run_dir,
        slug,
        {
            "slug": slug,
            "title": script.title,
            "prompt_file": str(prompt_path),
            "script_json_file": str(script_json_path),
            "script_markdown_file": str(script_md_path),
            "video_file": str(video_path),
            "audio_files": [str(path) for path in audio_paths],
            "background_file": str(background_path),
            "tts_provider": tts_provider.__class__.__name__,
            "renderer": renderer.__class__.__name__,
            "source_article": None
            if article is None
            else {
                "url": article.url,
                "title": article.title,
                "extracted_chars": len(article.text),
            },
        },
    )

    return PipelineResult(slug=slug, run_dir=run_dir, video_path=video_path, manifest_path=manifest_path)


def run_render_only(
    run_dir: Path,
    background_path: Path,
    renderer: VideoRenderer,
    status: Callable[[str], None] | None = None,
) -> PipelineResult:
    def report(message: str) -> None:
        if status is not None:
            status(message)

    if not run_dir.exists():
        raise FileNotFoundError(f"Run folder not found: {run_dir}")
    if not run_dir.is_dir():
        raise ValueError(f"Render-only path must be a folder: {run_dir}")

    report(f"Loading existing run folder: {run_dir}")
    script_path = find_single_run_file(run_dir, "_script.json")
    script = load_script_for_resume(script_path)
    slug = script.slug

    report(f"Loaded script: {script.title} ({len(script.turns)} turns)")
    validate_audio_files(script)

    video_path = run_dir / f"{slug}.mp4"
    report(f"Rendering video with background: {background_path}")
    renderer.render(script, background_path, video_path)
    report(f"Rendered video: {video_path}")

    report("Writing manifest")
    manifest_path = write_manifest(
        run_dir,
        slug,
        {
            "slug": slug,
            "title": script.title,
            "script_json_file": str(script_path),
            "script_markdown_file": str(run_dir / f"{slug}_script.md"),
            "video_file": str(video_path),
            "audio_files": [str(turn.audio_path) for turn in script.turns if turn.audio_path],
            "background_file": str(background_path),
            "renderer": renderer.__class__.__name__,
            "resume_mode": "render_only",
        },
    )
    return PipelineResult(slug=slug, run_dir=run_dir, video_path=video_path, manifest_path=manifest_path)


def find_single_run_file(run_dir: Path, suffix: str) -> Path:
    matches = sorted(run_dir.glob(f"*{suffix}"))
    if not matches:
        raise FileNotFoundError(f"No {suffix} file found in {run_dir}")
    if len(matches) > 1:
        raise ValueError(f"Expected one {suffix} file in {run_dir}, found {len(matches)}")
    return matches[0]


def load_script_for_resume(script_path: Path) -> ExplainerScript:
    data = json.loads(script_path.read_text(encoding="utf-8"))
    script = script_from_dict(data)
    for index, turn in enumerate(script.turns, start=1):
        turn.audio_path = resolve_resume_audio_path(script_path.parent, turn.audio_path, index, turn.speaker)
    return script


def resolve_resume_audio_path(
    run_dir: Path,
    saved_path: Path | None,
    turn_index: int,
    speaker: str,
) -> Path:
    candidates: list[Path] = []
    if saved_path is not None:
        if saved_path.is_absolute():
            candidates.append(saved_path)
        else:
            candidates.append(_resolve_repo_relative_audio_path(run_dir, saved_path))
            candidates.append(Path.cwd() / saved_path)
            candidates.append(run_dir / saved_path)
            candidates.append(run_dir / saved_path.name)
            if saved_path.parent.name == "audio":
                candidates.append(run_dir / "audio" / saved_path.name)

    candidates.append(run_dir / "audio" / f"{turn_index:02d}_{speaker}.mp3")

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _resolve_repo_relative_audio_path(run_dir: Path, saved_path: Path) -> Path:
    parts = saved_path.parts
    run_name = run_dir.name
    if run_name in parts:
        index = parts.index(run_name)
        tail = Path(*parts[index + 1 :])
        return run_dir / tail
    return Path.cwd() / saved_path


def validate_audio_files(script: ExplainerScript) -> None:
    missing = [
        f"{index}:{turn.speaker}"
        for index, turn in enumerate(script.turns, start=1)
        if turn.audio_path is None or not turn.audio_path.exists()
    ]
    if missing:
        raise FileNotFoundError(
            "Cannot render-only because audio files are missing for turns: "
            + ", ".join(missing)
        )
