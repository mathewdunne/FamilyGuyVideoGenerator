from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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


DEFAULT_OPENROUTER_MODEL = "anthropic/claude-haiku-4.5"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


SYSTEM_PROMPT = """You are a JSON-only script generator for short Peter and Stewie style FRC explainer reels.
Return exactly one JSON object and nothing else.
Do not write markdown, commentary, explanations, summaries, bullet points, or code fences.
Do not say "Done".
The JSON object must have exactly these top-level keys: title, slug, target_duration_seconds, turns.
Each turn must use only speaker values "peter" or "stewie".
The script must be a classroom-safe, accurate, funny 40-60 second explainer for high school FRC/coding students.
The first turn must be Stewie asking Peter a realistic student question that starts with "Peter, " and ends with "?".
Peter must answer in plain student-friendly language with simple cause-and-effect explanations and minimal jargon.
Use a few short back-and-forth follow-up questions from Stewie, then practical answers from Peter.
Keep the humor focused on the concept, not insults, edgy jokes, or copyrighted catchphrases.
"""


class TranscriptGenerator:
    def generate(self, prompt: str, article: ArticleSource | None = None) -> ExplainerScript:
        raise NotImplementedError


@dataclass
class OpenRouterTranscriptGenerator(TranscriptGenerator):
    api_key: str
    model: str = DEFAULT_OPENROUTER_MODEL
    base_url: str = DEFAULT_OPENROUTER_BASE_URL
    timeout_seconds: int = 120
    site_url: str = ""
    app_name: str = "FamilyGuyVideoGenerator"

    @classmethod
    def from_env(cls, model: str | None = None) -> "OpenRouterTranscriptGenerator":
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("Missing OpenRouter environment variable: OPENROUTER_API_KEY")
        return cls(
            api_key=api_key,
            model=model or os.getenv("OPENROUTER_MODEL") or DEFAULT_OPENROUTER_MODEL,
            base_url=os.getenv("OPENROUTER_BASE_URL") or DEFAULT_OPENROUTER_BASE_URL,
            site_url=os.getenv("OPENROUTER_SITE_URL", ""),
            app_name=os.getenv("OPENROUTER_APP_NAME", "FamilyGuyVideoGenerator"),
        )

    def generate(self, prompt: str, article: ArticleSource | None = None) -> ExplainerScript:
        user_prompt = build_user_prompt(prompt, article)
        request = self.build_request(user_prompt)
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw_output = response.read().decode("utf-8")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace").strip()
            raise RuntimeError(
                f"OpenRouter script generation failed with HTTP {exc.code}: "
                f"{_extract_error_message(body)}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(f"OpenRouter script generation failed: {exc.reason}") from exc
        return parse_openrouter_output(raw_output)

    def build_request(self, user_prompt: str) -> Request:
        url = self.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.site_url:
            headers["HTTP-Referer"] = self.site_url
        if self.app_name:
            headers["X-Title"] = self.app_name

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.4,
            "max_tokens": 1600,
        }
        return Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )


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
        "SCRIPT GOAL:",
        "Use the dialogue to teach one robotics or coding concept in a fun, useful way.",
        "Stewie is the student asking a question. Peter is the friendly explainer.",
        "",
        "OPENING TURN:",
        'The first turn must have speaker "stewie".',
        'The first line must start with "Peter, " and end with "?".',
        "Make that opening question sound like something an FRC student could reasonably ask.",
        "Good examples:",
        'Peter, what is PID control?',
        "Peter, my robot's elevator moves up slowly, but moves down very quickly, how can I fix this?",
        "",
        "DIALOGUE STYLE:",
        "Peter should answer without technical jargon when possible.",
        "Use plain language, everyday analogies, and practical cause-and-effect explanations.",
        "Stewie should ask a few short follow-up questions that a curious student would ask.",
        "Keep the humor classroom-safe and focused on the concept.",
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
            "Aim for 8-12 short turns total. Keep each line suitable for TTS.",
            "Use target_duration_seconds between 40 and 60, roughly a 40 second to 1 minute reel.",
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


def parse_openrouter_output(raw_output: str) -> ExplainerScript:
    data = _load_jsonish(raw_output)
    if not isinstance(data, dict):
        raise ValueError("OpenRouter output must be a JSON object")

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("OpenRouter response did not include choices[0].message.content") from exc
    return parse_claude_output(str(content))


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


def _extract_error_message(body: str) -> str:
    if not body:
        return "(empty response body)"
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return body[:500]
    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error)
        return str(data.get("message") or data.get("detail") or data)
    return str(data)
