from sources.tavily_base import fetch_tavily

QUERIES = [
    "site:compasspathways.com clinical trial results",
    "site:compasspathways.com psilocybin study",
]


def fetch(min_date: str | None = None) -> list[dict]:
    return fetch_tavily(QUERIES, "Compass Pathways", min_date=min_date)
