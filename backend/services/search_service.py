import os

from dotenv import load_dotenv
from tavily import TavilyClient



load_dotenv()



API_KEY = os.getenv("TAVILY_API_KEY")


if not API_KEY:
    raise ValueError(
        "TAVILY_API_KEY is missing from .env"
    )



tavily_client = TavilyClient(
    api_key=API_KEY
)


def search_web(query: str):

    # Internet search
    response = tavily_client.search(
        query=query,
        search_depth="basic",
        max_results=5
    )

    return response