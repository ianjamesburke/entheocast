from sources.tavily_base import fetch_tavily

QUERIES = [
    "site:psychedelicalpha.com psilocybin",
    "site:psychedelicalpha.com MDMA therapy",
    "site:psychedelicalpha.com ketamine clinical trial",
]


def fetch(min_date: str | None = None) -> list[dict]:
    return fetch_tavily(QUERIES, "Psychedelic Alpha", min_date=min_date)
