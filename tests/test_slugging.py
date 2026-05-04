import tempfile
import unittest
from pathlib import Path

from stewie_explainer.slugging import slugify, unique_run_dir


class SluggingTests(unittest.TestCase):
    def test_slugify_sanitizes_to_snake_case(self) -> None:
        self.assertEqual(slugify("Swerve Drive PID!!!"), "swerve_drive_pid")
        self.assertEqual(slugify("  FRC: Command-Based Java  "), "frc_command_based_java")

    def test_slugify_uses_fallback_for_empty_slug(self) -> None:
        self.assertEqual(slugify("!!!"), "explainer_video")

    def test_unique_run_dir_adds_collision_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            (out_dir / "swerve_drive_pid").mkdir()
            (out_dir / "swerve_drive_pid_2").mkdir()

            slug, run_dir = unique_run_dir(out_dir, "Swerve Drive PID")

            self.assertEqual(slug, "swerve_drive_pid_3")
            self.assertEqual(run_dir, out_dir / "swerve_drive_pid_3")


if __name__ == "__main__":
    unittest.main()

