from sources.rss_base import fetch_rss

FEED_URL = "https://chacruna.net/feed/"


def fetch(min_date: str | None = None) -> list[dict]:
    return fetch_rss(FEED_URL, "Chacruna Institute", min_date=min_date)
