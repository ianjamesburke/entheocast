from sources.tavily_base import fetch_tavily

QUERIES = [
    "psilocybin clinical trial results 2026",
    "MDMA therapy FDA approval 2026",
    "ketamine depression treatment study 2026",
    "psychedelic research breakthrough 2026",
]


def fetch(min_date: str | None = None) -> list[dict]:
    return fetch_tavily(QUERIES, "General News", min_date=min_date)
