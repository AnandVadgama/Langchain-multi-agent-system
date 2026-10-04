from langchain.tools import tool
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests
from tavily import TavilyClient
from readability import Document
import trafilatura
import re


load_dotenv()

tavily = TavilyClient()

@tool
def web_search(query: str) -> str:
    """
    Search the web for recent and reliable information on a topic . Returns Titles , URLs and snippets.
    :param query: str
    """
    results = tavily.search(query = query, max_results = 3)

    out = []

    for r in results['results']:
        out.append(
            f"Title : {r['title']}\nURL : {r['url']}\nSnippet : {r['content'][:300]}\n"
            )

    return "\n----\n".join(out)

@tool
def scrape_url(url: str) -> str:
    """
    Scrape and extract clean readable content from a URL.
    Uses multiple extraction strategies for better reliability.
    :param url: str
    """

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
        }

    try:
        response = requests.get(
            url = url,
            headers = headers,
            timeout = 15
            )

        response.raise_for_status()

        html = response.text

        # Strategy 1 → trafilatura (BEST for articles/blogs)
        extracted = trafilatura.extract(
            html,
            include_comments = False,
            include_tables = False
            )

        if extracted and len(extracted.strip()) > 200:
            cleaned = re.sub(r"\s+", " ", extracted)
            return cleaned[:1500]

        # Strategy 2 → readability

        doc = Document(html)
        clean_html = doc.summary()

        soup = BeautifulSoup(clean_html, "html.parser")

        for tag in soup(
                [
                    "script",
                    "style",
                    "nav",
                    "footer",
                    "header",
                    "aside",
                    "form"
                    ]
                ):
            tag.decompose()

        text = soup.get_text(separator = " ", strip = True)

        if text and len(text.strip()) > 200:
            cleaned = re.sub(r'\s+', ' ', text)
            return cleaned[:1500]

        # Strategy 3 → fallback full page extraction

        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(
                [
                    "script",
                    "style",
                    "nav",
                    "footer",
                    "header",
                    "aside",
                    "form"
                    ]
                ):
            tag.decompose()

        text = soup.get_text(separator = " ", strip = True)

        cleaned = re.sub(r'\s+', ' ', text)

        if cleaned:
            return cleaned[:1500]

    except Exception:
        pass

    # Strategy 4 → Fallback to Tavily extract (bypasses bot blocks, JS rendering, 403s)
    try:
        tav_res = tavily.extract(urls=[url])
        if tav_res and tav_res.get("results"):
            content = tav_res["results"][0].get("raw_content", "")
            if content and len(content.strip()) > 50:
                cleaned = re.sub(r"\s+", " ", content)
                return cleaned[:1500]
    except Exception as e:
        return f"Could not scrape URL: {str(e)}"

    return "Could not extract meaningful content from the page."
