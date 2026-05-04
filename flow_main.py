from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stewie_explainer.backgrounds import DEFAULT_BACKGROUNDS_DIR, resolve_background
from stewie_explainer.pipeline import run_generation, run_render_only
from stewie_explainer.renderer import MoviePyReelRenderer
from stewie_explainer.subtitles import WhisperXSubtitleAligner
from stewie_explainer.transcript import (
    DEFAULT_OPENROUTER_MODEL,
    ClaudeCliTranscriptGenerator,
    OpenRouterTranscriptGenerator,
    TranscriptGenerator,
)
from stewie_explainer.tts import create_tts_provider


def load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a funny Peter/Stewie FRC or coding explainer reel."
    )
    parser.add_argument("--prompt", default="", help="Topic or instructions for the explainer.")
    parser.add_argument("--url", default=None, help="Optional article URL to use as source context.")
    parser.add_argument(
        "--render-only",
        type=Path,
        default=None,
        help="Resume an existing run folder and rerun only the video render step.",
    )
    parser.add_argument(
        "--background",
        type=Path,
        default=None,
        help=(
            "Background gameplay/reel video to render behind the characters. "
            "Defaults to a random video from video_assets/backgrounds/."
        ),
    )
    parser.add_argument(
        "--backgrounds-dir",
        default=DEFAULT_BACKGROUNDS_DIR,
        type=Path,
        help="Directory to search for a random background when --background is not set.",
    )
    parser.add_argument(
        "--out",
        default=Path("outputs"),
        type=Path,
        help="Directory where the run folder and artifacts should be written.",
    )
    parser.add_argument(
        "--tts",
        default="fish_audio",
        help="TTS provider to use. Currently supported: fish_audio.",
    )
    parser.add_argument(
        "--script-provider",
        default="openrouter",
        choices=["openrouter", "claude_cli"],
        help="Script generator to use. Default: openrouter.",
    )
    parser.add_argument(
        "--openrouter-model",
        default=None,
        help=(
            "OpenRouter model for script generation. "
            f"Defaults to OPENROUTER_MODEL or {DEFAULT_OPENROUTER_MODEL}."
        ),
    )
    parser.add_argument(
        "--claude-model",
        default="haiku",
        help="Claude CLI model alias/name for script generation when --script-provider claude_cli.",
    )
    parser.add_argument(
        "--whisperx-model",
        default="base",
        help=(
            "Optional WhisperX alignment model override. "
            "The default uses WhisperX's language-specific align model."
        ),
    )
    parser.add_argument(
        "--whisperx-device",
        default="cpu",
        help="Device for WhisperX subtitle alignment, such as cpu or cuda.",
    )
    parser.add_argument(
        "--whisperx-compute-type",
        default="int8",
        help="Reserved for future WhisperX transcription use.",
    )
    parser.add_argument(
        "--language",
        default="en",
        help="Language code for WhisperX subtitle alignment.",
    )
    parser.add_argument(
        "--assets-dir",
        default=Path("image_assests"),
        type=Path,
        help="Directory containing peter.png and stewie.png.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show full Python tracebacks instead of concise errors.",
    )
    return parser


def create_transcript_generator(args: argparse.Namespace) -> TranscriptGenerator:
    if args.script_provider == "openrouter":
        return OpenRouterTranscriptGenerator.from_env(model=args.openrouter_model)
    if args.script_provider == "claude_cli":
        return ClaudeCliTranscriptGenerator(model=args.claude_model)
    raise ValueError(f"Unsupported script provider: {args.script_provider}")


def main() -> int:
    load_dotenv_if_available()
    args = build_parser().parse_args()

    def status(message: str) -> None:
        print(f"[status] {message}", flush=True)

    try:
        status("Resolving background video")
        background_path = resolve_background(args.background, args.backgrounds_dir)
        status(f"Using background: {background_path}")

        renderer = MoviePyReelRenderer(assets_dir=args.assets_dir)
        subtitle_aligner = WhisperXSubtitleAligner(
            model_name=args.whisperx_model,
            device=args.whisperx_device,
            compute_type=args.whisperx_compute_type,
            language=args.language,
        )
        status(
            "Using WhisperX subtitle alignment: "
            f"language={args.language}, device={args.whisperx_device}"
        )
        if args.render_only is not None:
            result = run_render_only(
                run_dir=args.render_only,
                background_path=background_path,
                subtitle_aligner=subtitle_aligner,
                renderer=renderer,
                status=status,
            )
            print(f"Created video: {result.video_path}")
            print(f"Run folder: {result.run_dir}")
            print(f"Manifest: {result.manifest_path}")
            return 0

        status(f"Using output directory: {args.out}")
        transcript_generator = create_transcript_generator(args)
        if isinstance(transcript_generator, OpenRouterTranscriptGenerator):
            status(f"Using OpenRouter model: {transcript_generator.model}")
        else:
            status(f"Using Claude CLI model: {args.claude_model}")

        status(f"Configuring TTS provider: {args.tts}")
        tts_provider = create_tts_provider(args.tts)

        result = run_generation(
            prompt=args.prompt,
            url=args.url,
            background_path=background_path,
            out_dir=args.out,
            transcript_generator=transcript_generator,
            tts_provider=tts_provider,
            subtitle_aligner=subtitle_aligner,
            renderer=renderer,
            status=status,
        )
    except Exception as exc:
        if args.debug:
            raise
        print(f"[error] {exc}", file=sys.stderr, flush=True)
        return 1

    print(f"Created video: {result.video_path}")
    print(f"Run folder: {result.run_dir}")
    print(f"Manifest: {result.manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
