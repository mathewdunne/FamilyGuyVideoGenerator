import json
import unittest
from unittest.mock import patch

from stewie_explainer.article import ArticleSource
from stewie_explainer.transcript import (
    DEFAULT_OPENROUTER_MODEL,
    ClaudeCliTranscriptGenerator,
    OpenRouterTranscriptGenerator,
    build_user_prompt,
    parse_claude_output,
)


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def valid_script_payload() -> dict:
    return {
        "title": "Swerve Drive PID",
        "slug": "Swerve Drive PID!!!",
        "target_duration_seconds": 45,
        "turns": [
            {"speaker": "peter", "text": "PID keeps the robot aimed at a target."},
            {"speaker": "stewie", "text": "So it is robot self-improvement, with math."},
            {"speaker": "peter", "text": "P reacts to current error."},
            {"speaker": "stewie", "text": "I remembers old error, tragically."},
            {"speaker": "peter", "text": "D predicts where the error is heading."},
            {"speaker": "stewie", "text": "Three tiny coaches yelling at the drivetrain."},
            {"speaker": "peter", "text": "Tune one value at a time."},
            {"speaker": "stewie", "text": "And log results before touching everything."},
        ],
    }


class TranscriptTests(unittest.TestCase):
    def test_parse_valid_script_and_normalize_slug(self) -> None:
        script = parse_claude_output(json.dumps(valid_script_payload()))

        self.assertEqual(script.slug, "swerve_drive_pid")
        self.assertEqual(len(script.turns), 8)
        self.assertEqual(script.turns[0].speaker, "peter")

    def test_parse_wrapped_claude_result(self) -> None:
        wrapped = json.dumps({"result": json.dumps(valid_script_payload())})

        script = parse_claude_output(wrapped)

        self.assertEqual(script.title, "Swerve Drive PID")

    def test_parse_wrapped_claude_result_with_fenced_json(self) -> None:
        wrapped = json.dumps({"result": f"Here is the script:\n```json\n{json.dumps(valid_script_payload())}\n```"})

        script = parse_claude_output(wrapped)

        self.assertEqual(script.slug, "swerve_drive_pid")

    def test_parse_wrapped_claude_result_with_surrounding_text(self) -> None:
        wrapped = json.dumps({"result": f"Sure.\n{json.dumps(valid_script_payload())}\nDone."})

        script = parse_claude_output(wrapped)

        self.assertEqual(script.title, "Swerve Drive PID")

    def test_rejects_unknown_speaker(self) -> None:
        payload = valid_script_payload()
        payload["turns"][0]["speaker"] = "brian"

        with self.assertRaises(ValueError):
            parse_claude_output(json.dumps(payload))

    def test_rejects_too_few_turns(self) -> None:
        payload = valid_script_payload()
        payload["turns"] = payload["turns"][:2]

        with self.assertRaises(ValueError):
            parse_claude_output(json.dumps(payload))

    def test_user_prompt_includes_article_context(self) -> None:
        article = ArticleSource("https://example.com", "FRC Encoders", "Encoders measure rotation.")

        prompt = build_user_prompt("Explain encoders.", article)

        self.assertIn("Explain encoders.", prompt)
        self.assertIn("FRC Encoders", prompt)
        self.assertIn("Encoders measure rotation.", prompt)
        self.assertIn("Return exactly one JSON object", prompt)
        self.assertIn("JSON schema:", prompt)

    def test_user_prompt_guides_stewie_question_and_plain_peter_answer(self) -> None:
        prompt = build_user_prompt("Explain PID control.", None)

        self.assertIn('The first turn must have speaker "stewie".', prompt)
        self.assertIn('The first line must start with "Peter, " and end with "?".', prompt)
        self.assertIn("Peter should answer without technical jargon", prompt)
        self.assertIn("FRC student could reasonably ask", prompt)

    def test_openrouter_generator_posts_chat_request_and_parses_message_content(self) -> None:
        response_payload = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(valid_script_payload()),
                    }
                }
            ]
        }
        generator = OpenRouterTranscriptGenerator(api_key="test-key")

        with patch(
            "stewie_explainer.transcript.urlopen",
            return_value=FakeResponse(response_payload),
        ) as mocked_urlopen:
            script = generator.generate("Explain PID.")

        request = mocked_urlopen.call_args.args[0]
        body = json.loads(request.data.decode("utf-8"))

        self.assertEqual(script.title, "Swerve Drive PID")
        self.assertEqual(request.full_url, "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        self.assertEqual(body["model"], DEFAULT_OPENROUTER_MODEL)
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertEqual(body["messages"][0]["role"], "system")
        self.assertEqual(body["messages"][1]["role"], "user")

    def test_claude_command_uses_bare_text_json_only_mode(self) -> None:
        generator = ClaudeCliTranscriptGenerator()
        command = generator.build_command("Explain PID.")

        self.assertNotIn("--bare", command)
        self.assertIn("--no-session-persistence", command)
        self.assertIn("--disable-slash-commands", command)
        self.assertIn("--tools", command)
        self.assertIn("--output-format", command)
        self.assertEqual(command[command.index("--output-format") + 1], "text")
        self.assertEqual(command[command.index("--tools") + 1], "")


if __name__ == "__main__":
    unittest.main()
