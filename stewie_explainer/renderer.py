from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from .models import ExplainerScript


class VideoRenderer:
    def render(self, script: ExplainerScript, background_path: Path, output_path: Path) -> Path:
        raise NotImplementedError


@dataclass
class MoviePyReelRenderer(VideoRenderer):
    assets_dir: Path = Path("image_assests")
    fps: int = 24

    def render(self, script: ExplainerScript, background_path: Path, output_path: Path) -> Path:
        ensure_pillow_moviepy_compatibility()
        configure_imagemagick_for_moviepy()

        from moviepy.editor import (
            AudioFileClip,
            CompositeAudioClip,
            CompositeVideoClip,
            ImageClip,
            VideoFileClip,
        )

        if not background_path.exists():
            raise FileNotFoundError(f"Background video not found: {background_path}")

        background = VideoFileClip(str(background_path))
        target_duration = _script_duration_upper_bound(script)
        if background.duration > target_duration + 10:
            background = background.subclip(0, target_duration + 10)

        audio_clips = []
        visual_clips = []
        subtitle_clips = []
        current_start = 0.0

        for turn in script.turns:
            if turn.audio_path is None:
                raise ValueError(f"Missing audio for turn: {turn.speaker} {turn.text!r}")
            audio = AudioFileClip(str(turn.audio_path)).set_start(current_start)
            audio_clips.append(audio)

            image_path = self.assets_dir / turn.character_image
            if image_path.exists():
                character = (
                    ImageClip(str(image_path))
                    .set_start(current_start)
                    .set_duration(audio.duration)
                    .resize(height=500)
                )
                x = 50 if turn.speaker == "peter" else max(0, background.w - character.w - 50)
                y = max(0, background.h - 550)
                visual_clips.append(character.set_position((x, y)))

            subtitle_clips.extend(
                _word_by_word_subtitles(turn.text, current_start, audio.duration)
            )
            current_start += audio.duration + 0.35

        final_audio = CompositeAudioClip(audio_clips)
        final_video = CompositeVideoClip([background] + visual_clips + subtitle_clips)
        final_video = final_video.set_duration(current_start).set_audio(final_audio)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final_video.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            fps=self.fps,
        )
        final_video.close()
        background.close()
        for clip in audio_clips:
            clip.close()
        return output_path


def _script_duration_upper_bound(script: ExplainerScript) -> int:
    return max(script.target_duration_seconds, 60)


def ensure_pillow_moviepy_compatibility() -> None:
    """MoviePy 1.x expects constants removed in Pillow 10."""
    from PIL import Image

    if not hasattr(Image, "ANTIALIAS"):
        Image.ANTIALIAS = Image.Resampling.LANCZOS


def configure_imagemagick_for_moviepy() -> str:
    """Point MoviePy 1.x at ImageMagick 7's magick binary when available."""
    binary = (
        os.getenv("IMAGEMAGICK_BINARY")
        or shutil.which("magick")
        or _safe_convert_binary()
    )
    if not binary:
        raise RuntimeError(
            "ImageMagick was not found. Install ImageMagick and make sure `magick` is on PATH, "
            "or set IMAGEMAGICK_BINARY in .env to the full path to magick.exe."
        )

    _apply_moviepy_settings({"IMAGEMAGICK_BINARY": binary})
    return binary


def _apply_moviepy_settings(settings: dict[str, str]) -> None:
    from moviepy.config import change_settings

    change_settings(settings)


def _safe_convert_binary() -> str | None:
    convert = shutil.which("convert")
    if convert and "system32" not in convert.lower():
        return convert
    return None


def _word_by_word_subtitles(text: str, start_time: float, duration: float) -> list:
    from moviepy.editor import TextClip

    words = [word for word in text.split() if word]
    if not words:
        return []
    word_duration = max(duration / len(words), 0.08)
    clips = []
    current = start_time
    for word in words:
        clips.append(
            TextClip(
                word,
                fontsize=95,
                color="yellow",
                font="DejaVu-Sans-Bold",
                stroke_color="black",
                stroke_width=1,
            )
            .set_start(current)
            .set_duration(word_duration)
            .set_position(("center", "center"))
            .fadein(0.05)
            .fadeout(0.05)
        )
        current += word_duration
    return clips
