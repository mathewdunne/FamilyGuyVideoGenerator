import unittest

from stewie_explainer.models import DialogueTurn, ExplainerScript, WordTiming, script_from_dict


class ModelTests(unittest.TestCase):
    def test_script_serializes_and_loads_word_timings(self) -> None:
        script = ExplainerScript(
            title="Word Timing",
            slug="word_timing",
            target_duration_seconds=45,
            turns=[
                DialogueTurn("peter", "One", word_timings=[WordTiming("One", 0.0, 0.2)]),
                DialogueTurn("stewie", "Two", word_timings=[WordTiming("Two", 0.1, 0.4)]),
                DialogueTurn("peter", "Three", word_timings=[WordTiming("Three", 0.0, 0.3)]),
                DialogueTurn("stewie", "Four", word_timings=[WordTiming("Four", 0.0, 0.3)]),
                DialogueTurn("peter", "Five", word_timings=[WordTiming("Five", 0.0, 0.3)]),
                DialogueTurn("stewie", "Six", word_timings=[WordTiming("Six", 0.0, 0.3)]),
                DialogueTurn("peter", "Seven", word_timings=[WordTiming("Seven", 0.0, 0.3)]),
                DialogueTurn("stewie", "Eight", word_timings=[WordTiming("Eight", 0.0, 0.3)]),
            ],
        )

        loaded = script_from_dict(script.to_dict(include_audio=True))

        self.assertEqual(loaded.turns[0].word_timings[0].word, "One")
        self.assertEqual(loaded.turns[0].word_timings[0].start, 0.0)
        self.assertEqual(loaded.turns[0].word_timings[0].end, 0.2)


if __name__ == "__main__":
    unittest.main()
