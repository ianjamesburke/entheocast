from sources.tavily_base import fetch_tavily

QUERIES = [
    "site:fda.gov psilocybin",
    "site:fda.gov MDMA therapy approval",
    "site:fda.gov psychedelic drug",
]


def fetch(min_date: str | None = None) -> list[dict]:
    return fetch_tavily(QUERIES, "FDA Press Releases", min_date=min_date)
