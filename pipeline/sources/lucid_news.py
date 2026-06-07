from sources.rss_base import fetch_rss

FEED_URL = "https://www.lucid.news/feed/"


def fetch(min_date: str | None = None) -> list[dict]:
    return fetch_rss(FEED_URL, "Lucid News", min_date=min_date)
