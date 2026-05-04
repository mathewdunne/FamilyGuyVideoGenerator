from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from .models import DialogueTurn, ExplainerScript, WordTiming


WHISPERX_SAMPLE_RATE = 16000


class SubtitleAligner(Protocol):
    def align_script(
        self,
        script: ExplainerScript,
        status: Callable[[str], None] | None = None,
    ) -> None:
        ...


@dataclass
class WhisperXSubtitleAligner:
    model_name: str = "base"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str = "en"
    batch_size: int = 16

    def __post_init__(self) -> None:
        self._whisperx = None
        self._align_model = None
        self._align_metadata = None

    def align_script(
        self,
        script: ExplainerScript,
        status: Callable[[str], None] | None = None,
    ) -> None:
        self._load_models()
        total_turns = len(script.turns)
        for index, turn in enumerate(script.turns, start=1):
            if status is not None:
                status(f"Aligning subtitles {index}/{total_turns} for {turn.speaker.title()}")
            turn.word_timings = self.align_turn(turn)

    def align_turn(self, turn: DialogueTurn) -> list[WordTiming]:
        if turn.audio_path is None:
            raise ValueError(f"Cannot align subtitles without audio for {turn.speaker}: {turn.text!r}")
        if not Path(turn.audio_path).exists():
            raise FileNotFoundError(f"Cannot align subtitles because audio is missing: {turn.audio_path}")

        assert self._whisperx is not None
        assert self._align_model is not None
        assert self._align_metadata is not None

        audio = self._whisperx.load_audio(str(turn.audio_path))
        transcript = [
            {
                "text": turn.text,
                "start": 0.0,
                "end": _audio_duration_seconds(audio),
            }
        ]
        aligned = self._whisperx.align(
            transcript,
            self._align_model,
            self._align_metadata,
            audio,
            self.device,
            return_char_alignments=False,
        )
        timings = word_timings_from_aligned_result(turn.text, aligned)
        if not timings:
            raise RuntimeError(f"WhisperX did not return word timings for {turn.audio_path}")
        return timings

    def _load_models(self) -> None:
        if self._align_model is not None:
            return

        try:
            import whisperx
        except ImportError as exc:
            raise RuntimeError(
                "WhisperX subtitle alignment requires the 'whisperx' package. "
                "Install dependencies with: python -m pip install -r requirements.txt"
            ) from exc

        self._whisperx = whisperx
        align_model_name = None if self.model_name in ("", "base", "default") else self.model_name
        self._align_model, self._align_metadata = whisperx.load_align_model(
            language_code=self.language,
            device=self.device,
            model_name=align_model_name,
        )


def script_needs_subtitle_alignment(script: ExplainerScript) -> bool:
    return any(not turn.word_timings for turn in script.turns)


def validate_subtitle_timings(script: ExplainerScript) -> None:
    missing = [
        f"{index}:{turn.speaker}"
        for index, turn in enumerate(script.turns, start=1)
        if not turn.word_timings
    ]
    if missing:
        raise ValueError(
            "Cannot render because subtitle word timings are missing for turns: "
            + ", ".join(missing)
        )


def word_timings_from_aligned_result(script_text: str, aligned_result: dict) -> list[WordTiming]:
    aligned_words = _collect_aligned_words(aligned_result)
    if not aligned_words:
        return []

    script_words = [word for word in script_text.split() if word]
    if not script_words:
        return []

    timings: list[WordTiming] = []
    if len(aligned_words) != len(script_words):
        raise RuntimeError(
            "WhisperX word alignment returned "
            f"{len(aligned_words)} words for {len(script_words)} script words."
        )

    for script_word, aligned_word in zip(script_words, aligned_words):
        timings.append(
            WordTiming(
                word=script_word,
                start=float(aligned_word["start"]),
                end=float(aligned_word["end"]),
            )
        )

    return timings


def _collect_aligned_words(aligned_result: dict) -> list[dict]:
    words: list[dict] = []
    for segment in aligned_result.get("segments", []):
        for word in segment.get("words", []):
            if not isinstance(word, dict):
                continue
            if "start" not in word or "end" not in word:
                continue
            text = str(word.get("word", "")).strip()
            if not text:
                continue
            words.append({"word": text, "start": word["start"], "end": word["end"]})
    return words


def _audio_duration_seconds(audio) -> float:
    if hasattr(audio, "shape") and len(audio.shape) > 0:
        return max(float(audio.shape[-1]) / WHISPERX_SAMPLE_RATE, 0.001)
    return max(float(len(audio)) / WHISPERX_SAMPLE_RATE, 0.001)
