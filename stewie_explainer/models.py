from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .slugging import slugify


SUPPORTED_SPEAKERS = {"peter", "stewie"}


@dataclass
class DialogueTurn:
    speaker: str
    text: str
    image_search: str = ""
    audio_path: Path | None = None

    def __post_init__(self) -> None:
        self.speaker = self.speaker.strip().lower()
        self.text = self.text.strip()
        self.image_search = self.image_search.strip()

        if self.speaker not in SUPPORTED_SPEAKERS:
            raise ValueError(f"Unsupported speaker: {self.speaker!r}")
        if not self.text:
            raise ValueError("Dialogue text cannot be empty")

    @property
    def character_image(self) -> str:
        return f"{self.speaker}.png"

    def to_dict(self, include_audio: bool = True) -> dict[str, Any]:
        data: dict[str, Any] = {
            "speaker": self.speaker,
            "text": self.text,
            "image_search": self.image_search,
        }
        if include_audio and self.audio_path is not None:
            data["audio"] = str(self.audio_path)
        return data


@dataclass
class ExplainerScript:
    title: str
    slug: str
    target_duration_seconds: int
    turns: list[DialogueTurn] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.title = self.title.strip()
        if not self.title:
            raise ValueError("Script title cannot be empty")

        self.slug = slugify(self.slug or self.title)
        if not 40 <= int(self.target_duration_seconds) <= 60:
            raise ValueError("target_duration_seconds must be between 40 and 60")
        if not 8 <= len(self.turns) <= 14:
            raise ValueError("Script must contain 8 to 14 dialogue turns")

    def to_dict(self, include_audio: bool = True) -> dict[str, Any]:
        return {
            "title": self.title,
            "slug": self.slug,
            "target_duration_seconds": self.target_duration_seconds,
            "turns": [turn.to_dict(include_audio=include_audio) for turn in self.turns],
        }


def script_from_dict(data: dict[str, Any]) -> ExplainerScript:
    if not isinstance(data, dict):
        raise ValueError("Claude output must be a JSON object")

    raw_turns = data.get("turns")
    if not isinstance(raw_turns, list):
        raise ValueError("Claude output must include a turns array")

    turns = []
    for index, item in enumerate(raw_turns, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Turn {index} must be a JSON object")
        turns.append(
            DialogueTurn(
                speaker=str(item.get("speaker", "")),
                text=str(item.get("text", "")),
                image_search=str(item.get("image_search", "")),
                audio_path=Path(str(item["audio"])) if item.get("audio") else None,
            )
        )

    return ExplainerScript(
        title=str(data.get("title", "")),
        slug=str(data.get("slug", "")),
        target_duration_seconds=int(data.get("target_duration_seconds", 0)),
        turns=turns,
    )
