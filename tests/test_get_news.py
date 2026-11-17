import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

# Creating the Google GenAI client at import time requires a key, but these
# tests never make a live model call.
os.environ.setdefault("GEMINI_API_KEY", "test-key")

import synapse.components.get_news as get_news


ARTICLE_URL = (
    "https://www.theguardian.com/commentisfree/2026/nov/06/"
    "the-guardian-view-on-the-ai-backlash-american-voters-want-a-say-in-their-future"
)
API_PAYLOAD = {
    "response": {
        "pages": 1,
        "results": [
            {
                "webTitle": "The Guardian view on the AI backlash: American voters want a say in their future",
                "webUrl": ARTICLE_URL,
                "sectionName": "Opinion",
                "webPublicationDate": "2026-11-06T18:25:00Z",
            }
        ],
    }
}


class FakeResponse:
    def __init__(self, payload=None, text="", status_code=200):
        self._payload = payload
        self.text = text
        self.status_code = status_code

    def json(self):
        return self._payload


def fake_llm_response():
    return SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(parts=[SimpleNamespace(text="A summary.")])
            )
        ]
    )


class NewsScraperAuthorTests(unittest.TestCase):
    def extract_with_html(self, article_html):
        def fake_get(url, *args, **kwargs):
            if "content.guardianapis.com" in url:
                return FakeResponse(payload=API_PAYLOAD)
            return FakeResponse(text=article_html)

        with patch.object(get_news.requests, "get", side_effect=fake_get), patch.object(
            get_news, "generate_content", return_value=fake_llm_response()
        ):
            return get_news.NewsScraper().extract("2026-11-06")

    def test_editorial_byline_without_address_wrapper_is_scraped(self):
        # Editorial pages link the byline with rel="author" but do not wrap it
        # in an <address> element, which is what the scraper originally assumed.
        html = """
        <html><body>
        <a rel="author" href="https://www.theguardian.com/profile/editorial">Editorial</a>
        <div class="article-body-viewer-selector">
          <p>First paragraph of the editorial.</p>
          <p>Second paragraph of the editorial.</p>
        </div>
        </body></html>
        """

        result = self.extract_with_html(html)

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["author"], "Editorial")
        self.assertEqual(result[0]["summary"], "A summary.")

    def test_article_without_a_byline_is_scraped(self):
        html = """
        <html><body>
        <div class="article-body-viewer-selector">
          <p>A byline-less article body.</p>
        </div>
        </body></html>
        """

        result = self.extract_with_html(html)

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["author"], "")


if __name__ == "__main__":
    unittest.main()
