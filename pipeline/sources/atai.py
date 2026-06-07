from sources.tavily_base import fetch_tavily

QUERIES = [
    "site:atai.life clinical trial",
    "site:atai.life research update",
]


def fetch(min_date: str | None = None) -> list[dict]:
    return fetch_tavily(QUERIES, "Atai Life Sciences", min_date=min_date)
