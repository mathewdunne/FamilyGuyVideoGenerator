from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import DialogueTurn
from .models import ExplainerScript


class VideoRenderer:
    def render(self, script: ExplainerScript, background_path: Path, output_path: Path) -> Path:
        raise NotImplementedError


@dataclass
class MoviePyReelRenderer(VideoRenderer):
    assets_dir: Path = Path("image_assests")
    fps: int = 24

    def render(self, script: ExplainerScript, background_path: Path, output_path: Path) -> Path:
        from moviepy import (
            AudioFileClip,
            CompositeAudioClip,
            CompositeVideoClip,
            ImageClip,
            VideoFileClip,
            vfx,
        )

        if not background_path.exists():
            raise FileNotFoundError(f"Background video not found: {background_path}")

        background_source = VideoFileClip(str(background_path))
        background = None
        final_audio = None
        final_video = None
        audio_clips = []
        visual_clips = []
        subtitle_clips = []

        try:
            audio_clips, total_duration = _audio_timeline(script, AudioFileClip)
            background = _prepare_background(background_source, total_duration, vfx)

            for timed_turn in audio_clips:
                character_clip = _character_clip(
                    timed_turn.turn,
                    timed_turn.start,
                    timed_turn.duration,
                    self.assets_dir,
                    background.w,
                    background.h,
                    ImageClip,
                )
                if character_clip is not None:
                    visual_clips.append(character_clip)

                subtitle_clips.extend(
                    _word_by_word_subtitles(
                        timed_turn.turn.text,
                        timed_turn.start,
                        timed_turn.duration,
                        background.w,
                        background.h,
                    )
                )

            final_audio = CompositeAudioClip([timed.audio for timed in audio_clips])
            final_video = (
                CompositeVideoClip(
                    [background] + visual_clips + subtitle_clips,
                    size=(background.w, background.h),
                )
                .with_duration(total_duration)
                .with_audio(final_audio)
            )

            output_path.parent.mkdir(parents=True, exist_ok=True)
            final_video.write_videofile(
                str(output_path),
                codec="libx264",
                audio_codec="aac",
                fps=self.fps,
            )
            return output_path
        finally:
            _close_clip(final_video)
            _close_clip(final_audio)
            for clip in subtitle_clips:
                _close_clip(clip)
            for clip in visual_clips:
                _close_clip(clip)
            for timed in audio_clips:
                _close_clip(timed.audio)
            _close_clip(background)
            if background is not background_source:
                _close_clip(background_source)


@dataclass
class TimedAudio:
    turn: DialogueTurn
    audio: object
    start: float
    duration: float


def _audio_timeline(script: ExplainerScript, audio_clip_factory) -> tuple[list[TimedAudio], float]:
    audio_clips: list[TimedAudio] = []
    current_start = 0.0

    for turn in script.turns:
        if turn.audio_path is None:
            raise ValueError(f"Missing audio for turn: {turn.speaker} {turn.text!r}")

        audio = audio_clip_factory(str(turn.audio_path)).with_start(current_start)
        audio_clips.append(
            TimedAudio(
                turn=turn,
                audio=audio,
                start=current_start,
                duration=float(audio.duration),
            )
        )
        current_start += float(audio.duration) + 0.35

    return audio_clips, max(current_start, 0.1)


def _prepare_background(background, duration: float, vfx):
    if background.duration < duration:
        return background.with_effects([vfx.Loop(duration=duration)])
    return background.subclipped(0, duration)


def _character_clip(
    turn: DialogueTurn,
    start_time: float,
    duration: float,
    assets_dir: Path,
    frame_width: int,
    frame_height: int,
    image_clip_factory,
):
    image_path = assets_dir / turn.character_image
    if not image_path.exists():
        return None

    target_height = _character_height(frame_height)
    character = (
        image_clip_factory(str(image_path))
        .with_start(start_time)
        .with_duration(duration)
        .resized(height=target_height)
    )

    # Keep speakers anchored to opposite sides while leaving room for centered subtitles.
    margin = max(36, int(frame_width * 0.04))
    x = margin if turn.speaker == "peter" else max(margin, frame_width - character.w - margin)
    y = max(0, frame_height - character.h - max(18, int(frame_height * 0.04)))
    return character.with_position((x, y))


def _character_height(frame_height: int) -> int:
    return min(540, max(280, int(frame_height * 0.55)))


def _word_by_word_subtitles(
    text: str,
    start_time: float,
    duration: float,
    frame_width: int,
    frame_height: int,
) -> list:
    words = [word for word in text.split() if word]
    if not words:
        return []

    from moviepy import ImageClip, vfx

    word_duration = max(duration / len(words), 0.08)
    clips = []
    current = start_time
    for word in words:
        image = _subtitle_image(
            word.upper(),
            _subtitle_font_size(frame_width, frame_height, word),
        )
        clips.append(
            ImageClip(image)
            .with_start(current)
            .with_duration(word_duration)
            .with_position(("center", int(frame_height * 0.44)))
            .with_effects([vfx.FadeIn(0.05), vfx.FadeOut(0.05)])
        )
        current += word_duration
    return clips


def _subtitle_font_size(frame_width: int, frame_height: int, word: str) -> int:
    base_size = min(104, max(54, int(frame_height * 0.11)))
    max_word_width = frame_width * 0.82
    estimated_width = max(len(word), 1) * base_size * 0.68
    if estimated_width <= max_word_width:
        return base_size
    return max(42, int(base_size * (max_word_width / estimated_width)))


def _subtitle_image(word: str, font_size: int):
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np

    font = ImageFont.load_default(size=font_size)
    stroke_width = max(5, int(font_size * 0.06))
    padding_x = max(28, int(font_size * 0.28))
    padding_y = max(22, int(font_size * 0.32))

    probe = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    draw = ImageDraw.Draw(probe)
    bbox = draw.textbbox((0, 0), word, font=font, stroke_width=stroke_width)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    image = Image.new(
        "RGBA",
        (text_width + padding_x * 2, text_height + padding_y * 2),
        (0, 0, 0, 0),
    )
    draw = ImageDraw.Draw(image)

    # Pillow's text boxes can sit above/below zero; offset by the bbox so stroke never clips.
    draw.text(
        (padding_x - bbox[0], padding_y - bbox[1]),
        word,
        font=font,
        fill="#ffd84d",
        stroke_fill="black",
        stroke_width=stroke_width,
    )
    return np.array(image)


def _close_clip(clip) -> None:
    if clip is not None and hasattr(clip, "close"):
        clip.close()
