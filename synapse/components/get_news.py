import os
import requests
from bs4 import BeautifulSoup
from synapse.utils.logger import get_logger
from synapse.utils.llm_utils import generate_content

logger = get_logger(__name__)

class NewsScraper:
    def __init__(self):
        self.base_url = f"https://content.guardianapis.com/search?section=technology&tag=technology/artificialintelligenceai&api-key={os.getenv('GUARDIAN_API_KEY')}"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }

    def extract(self, date):
        def get_main_content(response):
            if not response or not getattr(response, "candidates", None):
                return ""
            candidate = response.candidates[0]
            if not candidate or not getattr(candidate, "content", None):
                return ""
            parts = getattr(candidate.content, "parts", None)
            if not parts:
                return ""

            return "".join(part.text for part in parts if hasattr(part, "text"))

        main_data = []
        self.base_url = self.base_url + f"&from-date={date}&to-date={date}"
        try:
            response = requests.get(self.base_url)
            if response.status_code == 200:
                data = response.json()
                total_pages = data["response"]["pages"]
                for page in range(1, total_pages + 1):
                    response = requests.get(self.base_url + f"&page={page}")
                    data = response.json()
                    for article in data["response"]["results"]:
                        title = article["webTitle"]
                        url = article["webUrl"]
                        section = article["sectionName"]
                        date = article["webPublicationDate"]
                        content_response = requests.get(url, headers = self.headers)
                        soup = BeautifulSoup(content_response.text, 'html.parser')
                        author_el = soup.select_one('address a[rel="author"]') or soup.select_one('a[rel="author"]')
                        author = author_el.get_text(strip=True) if author_el else ""
                        content = "\n".join(p.get_text(strip=True)
                        for p in soup.select('div.article-body-viewer-selector p'))
                        news_summary = generate_content(prompt_name = "summary_prompt", article = content)
                        main_data.append({
                            "title": title,
                            "url": url,
                            "section": section,
                            "date": article["webPublicationDate"],
                            "author": author,
                            "content": content,
                            "summary": get_main_content(news_summary)
                        })
                return main_data
        except Exception as e:
            logger.error(f"Failed to extract news for {date}: {str(e)}")
            return None