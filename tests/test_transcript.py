import json
import unittest

from stewie_explainer.article import ArticleSource
from stewie_explainer.transcript import ClaudeCliTranscriptGenerator, build_user_prompt, parse_claude_output


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
