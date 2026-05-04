import unittest
from unittest.mock import patch

from stewie_explainer.article import fetch_article


class FakeResponse:
    html = """
    <html>
      <head><title>Command-Based Robots</title><style>.x{}</style></head>
      <body>
        <h1>Command-Based Robots</h1>
        <p>Commands describe robot actions.</p>
        <p>Subsystems own hardware resources.</p>
        <script>ignore me</script>
      </body>
    </html>
    """.encode("utf-8")

    class Headers:
        def get_content_charset(self):
            return "utf-8"

    headers = Headers()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def read(self) -> bytes:
        return self.html


class ArticleTests(unittest.TestCase):
    @patch("stewie_explainer.article.urlopen", return_value=FakeResponse())
    def test_fetch_article_extracts_title_and_readable_text(self, fake_urlopen) -> None:
        article = fetch_article("https://example.com/frc")

        self.assertEqual(article.title, "Command-Based Robots")
        self.assertIn("Commands describe robot actions.", article.text)
        self.assertIn("Subsystems own hardware resources.", article.text)
        self.assertNotIn("ignore me", article.text)
        fake_urlopen.assert_called_once()


if __name__ == "__main__":
    unittest.main()
