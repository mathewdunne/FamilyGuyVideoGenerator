from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from typing import Any

from .article import ArticleSource
from .models import ExplainerScript, script_from_dict
from .slugging import slugify


SCRIPT_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["title", "slug", "target_duration_seconds", "turns"],
    "properties": {
        "title": {"type": "string"},
        "slug": {"type": "string"},
        "target_duration_seconds": {"type": "integer", "minimum": 40, "maximum": 60},
        "turns": {
            "type": "array",
            "minItems": 8,
            "maxItems": 14,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["speaker", "text"],
                "properties": {
                    "speaker": {"type": "string", "enum": ["peter", "stewie"]},
                    "text": {"type": "string"},
                    "image_search": {"type": "string"},
                },
            },
        },
    },
}


SYSTEM_PROMPT = """You are a JSON-only script generator.
Return exactly one JSON object and nothing else.
Do not write markdown, commentary, explanations, summaries, bullet points, or code fences.
Do not say "Done".
The JSON object must have exactly these top-level keys: title, slug, target_duration_seconds, turns.
Each turn must use only speaker values "peter" or "stewie".
The script must be a classroom-safe, accurate, funny 40-60 second explainer for high school FRC/coding students.
"""


class TranscriptGenerator:
    def generate(self, prompt: str, article: ArticleSource | None = None) -> ExplainerScript:
        raise NotImplementedError


@dataclass
class ClaudeCliTranscriptGenerator(TranscriptGenerator):
    model: str = "haiku"
    timeout_seconds: int = 120

    def generate(self, prompt: str, article: ArticleSource | None = None) -> ExplainerScript:
        user_prompt = build_user_prompt(prompt, article)
        command = self.build_command(user_prompt)
        try:
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            stdout = (exc.stdout or "").strip()
            detail = stderr or stdout or f"exit code {exc.returncode}"
            raise RuntimeError(f"Claude CLI script generation failed: {detail}") from exc
        return parse_claude_output(result.stdout)

    def build_command(self, user_prompt: str) -> list[str]:
        return [
            "claude",
            "-p",
            "--model",
            self.model,
            "--system-prompt",
            SYSTEM_PROMPT,
            "--no-session-persistence",
            "--tools",
            "",
            "--disable-slash-commands",
            "--output-format",
            "text",
            user_prompt,
        ]


def build_user_prompt(prompt: str, article: ArticleSource | None = None) -> str:
    sections = [
        "Generate an FRC/coding explainer reel script.",
        "",
        "OUTPUT RULES:",
        "Return exactly one JSON object. No markdown. No prose. No preface. No explanation.",
        "The response must start with { and end with }.",
        "",
        "JSON schema:",
        json.dumps(SCRIPT_JSON_SCHEMA, indent=2),
        "",
        "User prompt:",
        prompt.strip() or "(no direct prompt supplied)",
    ]
    if article is not None and article.ok:
        sections.extend(
            [
                "",
                "Source article:",
                f"Title: {article.title or '(untitled)'}",
                f"URL: {article.url}",
                "",
                article.text,
            ]
        )
    sections.extend(
        [
            "",
            "Make the title specific and generate a snake_case slug candidate.",
            "Aim for 8-14 short turns total. Keep each line suitable for TTS.",
            "Use target_duration_seconds between 40 and 60.",
        ]
    )
    return "\n".join(sections)


def parse_claude_output(raw_output: str) -> ExplainerScript:
    raw_output = raw_output.strip()
    data = _load_jsonish(raw_output)

    if isinstance(data, dict) and isinstance(data.get("result"), str):
        data = _load_jsonish(data["result"])

    script = script_from_dict(data)
    script.slug = slugify(script.slug or script.title)
    return script


def _load_jsonish(value: str) -> Any:
    value = value.strip()
    if not value:
        raise ValueError("Claude returned an empty response")

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", value, flags=re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))

    extracted = _extract_first_json_object(value)
    if extracted is not None:
        return json.loads(extracted)

    preview = value.replace("\n", " ")[:500]
    raise ValueError(f"Claude did not return parseable script JSON. Response preview: {preview}")


def _extract_first_json_object(value: str) -> str | None:
    start = value.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(value)):
        char = value[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return value[start : index + 1]
    return None
