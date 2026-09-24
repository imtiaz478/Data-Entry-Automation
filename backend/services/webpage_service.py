from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


MAX_TEXT_LENGTH = 15000


def get_webpage_text(url: str):

    try:

        if urlparse(url).scheme not in ("http", "https"):
            return "ERROR: only http/https links are allowed"

        response = requests.get(
            url,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        # Pass bytes so BeautifulSoup reads the page's own charset;
        # response.text guesses wrong on many sites and breaks "৳"
        soup = BeautifulSoup(
            response.content,
            "html.parser"
        )

        # Unnecessary HTML remove
        for tag in soup([
            "script",
            "style",
            "nav",
            "footer",
            "header"
        ]):
            tag.decompose()

        # Page text
        text = soup.get_text(
            separator=" ",
            strip=True
        )

        # Too much text হলে প্রথম MAX_TEXT_LENGTH characters
        text = text[:MAX_TEXT_LENGTH]

        return text

    except Exception as error:

        return f"ERROR: {str(error)}"
