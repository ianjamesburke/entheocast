import os
from tavily import TavilyClient

_client: TavilyClient | None = None


def _get_client() -> TavilyClient:
    global _client
    if _client is None:
        _client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    return _client


def search(query: str, max_results: int = 10, days: int | None = None) -> list[dict]:
    """Search via Tavily. Returns {url, title, content, raw_content, published_date}.

    topic="news" is required for two things every Tier 3 source depends on: the
    published_date field (absent on the general topic, which forced entries to be
    stamped with the ingest date) and the `days` recency window.
    raw_content is the full extracted page text (replaces a separate reader fetch).
    """
    kwargs: dict = {
        "max_results": max_results,
        "include_raw_content": True,
        "topic": "news",
    }
    if days is not None:
        kwargs["days"] = days
    resp = _get_client().search(query, **kwargs)
    return [
        {
            "url": r["url"],
            "title": r.get("title", ""),
            "content": r.get("content", ""),
            "raw_content": r.get("raw_content") or "",
            "published_date": r.get("published_date"),
        }
        for r in resp.get("results", [])
    ]
