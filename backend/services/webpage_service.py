import requests
from bs4 import BeautifulSoup


def get_webpage_text(url: str):

    try:

        response = requests.get(
            url,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
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

        # Too much text হলে প্রথম 10000 characters
        text = text[:10000]

        return text

    except Exception as error:

        return f"ERROR: {str(error)}"