import os

from dotenv import load_dotenv
from tavily import TavilyClient


load_dotenv()


# Created on first use, so the server can start (and process
# files that are already complete) without a Tavily key
_tavily_client = None


def _get_client():

    global _tavily_client

    if _tavily_client is None:

        api_key = os.getenv("TAVILY_API_KEY")

        if not api_key:
            raise RuntimeError(
                "TAVILY_API_KEY is missing from .env"
            )

        _tavily_client = TavilyClient(
            api_key=api_key
        )

    return _tavily_client


def search_web(query: str, max_results: int = 5):

    # Internet search
    response = _get_client().search(
        query=query,
        search_depth="basic",
        max_results=max_results
    )

    return response
