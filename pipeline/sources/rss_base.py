from datetime import date
import feedparser
import dates
from dedup import make_id
from snippet import condense
import llm

COMPOUND_KEYWORDS = ["psilocybin", "mdma", "lsd", "ketamine", "dmt", "ibogaine", "ayahuasca", "mescaline"]


def _is_relevant(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in COMPOUND_KEYWORDS)


def _article_text(item) -> str:
    """Full post body from the feed's content:encoded, falling back to summary."""
    if item.get("content"):
        return item.content[0].value or ""
    return item.get("summary", "") or item.get("description", "")


def fetch_rss(feed_url: str, source_name: str, min_date: str | None = None) -> list[dict]:
    feed = feedparser.parse(feed_url)
    entries = []

    for item in feed.entries:
        title = item.get("title", "")
        url = item.get("link", "")
        # Feeds emit RFC-2822 ("Fri, 17 Apr 2026 10:00:00 +0000"); slicing to 10
        # characters silently produced "Fri, 17 Ap" instead of a date.
        pub_date = dates.to_iso(item.get("published"))

        if min_date and pub_date and pub_date < min_date:
            continue

        text = _article_text(item)
        if not _is_relevant(title + " " + text):
            continue

        extracted = llm.extract(text, url)
        if not extracted:
            continue

        entry_id = make_id(title, extracted.get("doi"), url)
        entries.append({
            "id": entry_id,
            "title": extracted.get("title") or title,
            "compound": extracted.get("compound", "other"),
            "type": extracted.get("type", "news"),
            "institution": extracted.get("institution"),
            "condition": extracted.get("condition", "other"),
            "sample_size": extracted.get("sample_size"),
            "status": extracted.get("status", "published"),
            "date": pub_date,
            "abstract": condense(text),
            "outcome_summary": extracted.get("outcome_summary"),
            "doi": extracted.get("doi"),
            "url": url,
            "source": source_name,
            "first_seen": str(date.today()),
        })

    return entries
