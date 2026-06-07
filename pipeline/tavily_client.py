import os
from tavily import TavilyClient

_client: TavilyClient | None = None


def _get_client() -> TavilyClient:
    global _client
    if _client is None:
        _client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    return _client


def search(query: str, max_results: int = 10, days: int | None = None) -> list[dict]:
    """Search via Tavily. Returns list of {url, title, content} dicts."""
    kwargs: dict = {"max_results": max_results}
    if days is not None:
        kwargs["days"] = days
    resp = _get_client().search(query, **kwargs)
    return [
        {"url": r["url"], "title": r.get("title", ""), "content": r.get("content", "")}
        for r in resp.get("results", [])
    ]
