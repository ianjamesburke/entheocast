from datetime import date
import feedparser
from dedup import make_id
import jina
import mimo

COMPOUND_KEYWORDS = ["psilocybin", "mdma", "lsd", "ketamine", "dmt", "ibogaine", "ayahuasca", "mescaline"]


def _is_relevant(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in COMPOUND_KEYWORDS)


def fetch_rss(feed_url: str, source_name: str, min_date: str | None = None) -> list[dict]:
    feed = feedparser.parse(feed_url)
    entries = []

    for item in feed.entries:
        title = item.get("title", "")
        url = item.get("link", "")
        pub_date = item.get("published", "")[:10] if item.get("published") else str(date.today())

        if min_date and pub_date < min_date:
            continue

        summary = item.get("summary", "") or item.get("description", "")
        if not _is_relevant(title + " " + summary):
            continue

        try:
            text = jina.fetch_text(url)
        except Exception as e:
            print(f"{source_name}: Jina error for {url}: {e}")
            continue

        extracted = mimo.extract(text, url)
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
            "outcome_summary": extracted.get("outcome_summary"),
            "doi": extracted.get("doi"),
            "url": url,
            "source": source_name,
            "first_seen": str(date.today()),
        })

    return entries
