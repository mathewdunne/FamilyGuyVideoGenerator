from __future__ import annotations

import os
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .models import DialogueTurn, ExplainerScript


class TTSProvider:
    def synthesize_script(
        self,
        script: ExplainerScript,
        audio_dir: Path,
        status: Callable[[str], None] | None = None,
    ) -> list[Path]:
        audio_dir.mkdir(parents=True, exist_ok=True)
        paths = []
        for index, turn in enumerate(script.turns, start=1):
            output_path = audio_dir / f"{index:02d}_{turn.speaker}.mp3"
            if status is not None:
                status(f"Generating audio {index}/{len(script.turns)} for {turn.speaker.title()}")
            self.synthesize_turn(turn, output_path)
            turn.audio_path = output_path
            paths.append(output_path)
        return paths

    def synthesize_turn(self, turn: DialogueTurn, output_path: Path) -> Path:
        raise NotImplementedError


@dataclass
class FishAudioProvider(TTSProvider):
    api_key: str
    peter_voice_id: str
    stewie_voice_id: str
    model: str = "s2-pro"
    endpoint: str = "https://api.fish.audio/v1/tts"
    timeout_seconds: int = 90

    @classmethod
    def from_env(cls) -> "FishAudioProvider":
        api_key = os.getenv("FISH_AUDIO_API_KEY") or os.getenv("FISH_API_KEY")
        peter_voice_id = os.getenv("FISH_AUDIO_PETER_VOICE_ID")
        stewie_voice_id = os.getenv("FISH_AUDIO_STEWIE_VOICE_ID")
        missing = [
            name
            for name, value in {
                "FISH_AUDIO_API_KEY": api_key,
                "FISH_AUDIO_PETER_VOICE_ID": peter_voice_id,
                "FISH_AUDIO_STEWIE_VOICE_ID": stewie_voice_id,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"Missing Fish Audio environment variables: {', '.join(missing)}")
        return cls(
            api_key=api_key,
            peter_voice_id=peter_voice_id,
            stewie_voice_id=stewie_voice_id,
            model=os.getenv("FISH_AUDIO_MODEL", "s2-pro"),
        )

    def synthesize_turn(self, turn: DialogueTurn, output_path: Path) -> Path:
        reference_id = self.peter_voice_id if turn.speaker == "peter" else self.stewie_voice_id
        request = Request(
            self.endpoint,
            data=json.dumps(
                {
                    "text": turn.text,
                    "reference_id": reference_id,
                    "format": "mp3",
                }
            ).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "model": self.model,
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                output_path.write_bytes(response.read())
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace").strip()
            message = _extract_error_message(body)
            if exc.code == 402:
                raise RuntimeError(
                    "Fish Audio returned 402 Payment Required. "
                    "This usually means API billing or API wallet access is not enabled/funded, "
                    "even if the web app still shows free monthly generation credits. "
                    f"Fish message: {message}"
                ) from exc
            raise RuntimeError(f"Fish Audio request failed with HTTP {exc.code}: {message}") from exc
        return output_path


def create_tts_provider(name: str) -> TTSProvider:
    normalized = name.strip().lower()
    if normalized == "fish_audio":
        return FishAudioProvider.from_env()
    raise ValueError(f"Unsupported TTS provider: {name}")


def _extract_error_message(body: str) -> str:
    if not body:
        return "(empty response body)"
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return body[:500]
    if isinstance(data, dict):
        return str(data.get("message") or data.get("detail") or data)
    return str(data)
