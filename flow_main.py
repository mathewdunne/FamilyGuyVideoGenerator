from __future__ import annotations

import argparse
import sys
from pathlib import Path

from stewie_explainer.backgrounds import DEFAULT_BACKGROUNDS_DIR, resolve_background
from stewie_explainer.pipeline import run_generation, run_render_only
from stewie_explainer.renderer import MoviePyReelRenderer
from stewie_explainer.transcript import ClaudeCliTranscriptGenerator
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
        "--claude-model",
        default="haiku",
        help="Claude CLI model alias/name for script generation.",
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
        if args.render_only is not None:
            result = run_render_only(
                run_dir=args.render_only,
                background_path=background_path,
                renderer=renderer,
                status=status,
            )
            print(f"Created video: {result.video_path}")
            print(f"Run folder: {result.run_dir}")
            print(f"Manifest: {result.manifest_path}")
            return 0

        status(f"Using output directory: {args.out}")
        transcript_generator = ClaudeCliTranscriptGenerator(model=args.claude_model)
        status(f"Using Claude model: {args.claude_model}")

        status(f"Configuring TTS provider: {args.tts}")
        tts_provider = create_tts_provider(args.tts)

        result = run_generation(
            prompt=args.prompt,
            url=args.url,
            background_path=background_path,
            out_dir=args.out,
            transcript_generator=transcript_generator,
            tts_provider=tts_provider,
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
