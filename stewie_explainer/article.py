from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.request import Request, urlopen


@dataclass
class ArticleSource:
    url: str
    title: str
    text: str

    @property
    def ok(self) -> bool:
        return bool(self.text.strip())


class ReadableHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self.body_parts: list[str] = []
        self._tag_stack: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._tag_stack.append(tag)
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self._tag_stack:
            self._tag_stack.pop()
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text or self._skip_depth:
            return

        current_tag = self._tag_stack[-1] if self._tag_stack else ""
        if current_tag == "title":
            self.title_parts.append(text)
        elif current_tag in {"p", "li", "h1", "h2", "h3", "pre", "code"}:
            self.body_parts.append(text)


def fetch_article(url: str, timeout_seconds: int = 20, max_chars: int = 8000) -> ArticleSource:
    request = Request(
        url,
        headers={"User-Agent": "frc-explainer-video-generator/1.0"},
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        html = raw.decode(charset, errors="replace")

    parser = ReadableHTMLParser()
    parser.feed(html)

    title = " ".join(parser.title_parts).strip()
    body = "\n\n".join(parser.body_parts).strip()
    if len(body) > max_chars:
        body = body[:max_chars].rsplit(" ", 1)[0].strip()

    return ArticleSource(url=url, title=title, text=body)
