from sources.rss_base import fetch_rss

FEED_URL = "https://maps.org/feed/"


def fetch(min_date: str | None = None) -> list[dict]:
    return fetch_rss(FEED_URL, "MAPS.org", min_date=min_date)
