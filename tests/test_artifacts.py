import json
import tempfile
import unittest
from pathlib import Path

from stewie_explainer.article import ArticleSource
from stewie_explainer.artifacts import (
    create_run_directory,
    write_manifest,
    write_prompt_file,
    write_script_files,
)
from stewie_explainer.models import DialogueTurn, ExplainerScript


def make_script(slug: str = "swerve_drive_pid") -> ExplainerScript:
    turns = [
        DialogueTurn("peter", "PID is like steering toward the target."),
        DialogueTurn("stewie", "So the robot stops wobbling like bad shopping cart?"),
        DialogueTurn("peter", "Exactly, proportional reacts to current error."),
        DialogueTurn("stewie", "And integral remembers old mistakes, deeply relatable."),
        DialogueTurn("peter", "Derivative watches how fast the error changes."),
        DialogueTurn("stewie", "So P, I, and D are a tiny robot coaching staff."),
        DialogueTurn("peter", "Tune gently, test safely, and log what changes."),
        DialogueTurn("stewie", "Aha, fewer mystery spins, more banners."),
    ]
    return ExplainerScript("Swerve Drive PID", slug, 45, turns)


class ArtifactTests(unittest.TestCase):
    def test_writes_coherent_run_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            slug, run_dir = create_run_directory(out_dir, "Swerve Drive PID")
            script = make_script(slug)
            article = ArticleSource(
                url="https://example.com/pid",
                title="PID Control",
                text="PID helps robots correct error over time.",
            )

            prompt_path = write_prompt_file(run_dir, slug, "Explain PID for FRC.", article)
            json_path, md_path = write_script_files(run_dir, slug, script)
            manifest_path = write_manifest(run_dir, slug, {"video_file": str(run_dir / f"{slug}.mp4")})

            self.assertTrue((run_dir / "audio").is_dir())
            self.assertEqual(prompt_path.name, "swerve_drive_pid_prompt.md")
            self.assertEqual(json_path.name, "swerve_drive_pid_script.json")
            self.assertEqual(md_path.name, "swerve_drive_pid_script.md")
            self.assertEqual(manifest_path.name, "swerve_drive_pid_manifest.json")
            self.assertIn("Explain PID for FRC.", prompt_path.read_text(encoding="utf-8"))
            self.assertIn("**Peter:**", md_path.read_text(encoding="utf-8"))
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["slug"], slug)


if __name__ == "__main__":
    unittest.main()

