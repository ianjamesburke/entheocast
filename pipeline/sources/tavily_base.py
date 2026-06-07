from datetime import date, datetime
from dedup import make_id
import jina
import mimo
import tavily_client as tavily

COMPOUND_KEYWORDS = ["psilocybin", "mdma", "lsd", "ketamine", "dmt", "ibogaine", "ayahuasca", "mescaline"]

_SKIP_EXTENSIONS = (".pdf", ".docx", ".pptx", ".xlsx", ".zip")
_SKIP_DOMAINS = ("facebook.com", "twitter.com", "x.com", "linkedin.com", "instagram.com")
_SKIP_PATHS = ("precision.fda.gov/ginas", "download.open.fda.gov", "accessdata.fda.gov/scripts")


def _is_article_url(url: str) -> bool:
    u = url.lower()
    if any(u.endswith(ext) for ext in _SKIP_EXTENSIONS):
        return False
    if any(d in u for d in _SKIP_DOMAINS):
        return False
    if any(p in u for p in _SKIP_PATHS):
        return False
    return True


def _is_relevant(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in COMPOUND_KEYWORDS)


def _days_since(min_date: str) -> int:
    delta = date.today() - datetime.strptime(min_date, "%Y-%m-%d").date()
    return max(delta.days, 1)


def fetch_tavily(queries: list[str], source_name: str, min_date: str | None = None) -> list[dict]:
    days = _days_since(min_date) if min_date else None
    seen_urls: set[str] = set()
    entries = []

    for query in queries:
        try:
            results = tavily.search(query, max_results=10, days=days)
        except Exception as e:
            print(f"{source_name}: Tavily error for '{query}': {e}")
            continue

        for r in results:
            url = r["url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)

            if not _is_article_url(url):
                continue

            if not _is_relevant(r["title"] + " " + r["content"]):
                continue

            try:
                text = jina.fetch_text(url)
            except Exception as e:
                print(f"{source_name}: Jina error for {url}: {e}")
                continue

            extracted = mimo.extract(text, url)
            if not extracted:
                continue

            title = extracted.get("title") or r["title"]
            entry_id = make_id(title, extracted.get("doi"), url)
            entries.append({
                "id": entry_id,
                "title": title,
                "compound": extracted.get("compound", "other"),
                "type": extracted.get("type", "news"),
                "institution": extracted.get("institution"),
                "condition": extracted.get("condition", "other"),
                "sample_size": extracted.get("sample_size"),
                "status": extracted.get("status", "published"),
                "date": str(date.today()),
                "outcome_summary": extracted.get("outcome_summary"),
                "doi": extracted.get("doi"),
                "url": url,
                "source": source_name,
                "first_seen": str(date.today()),
            })

    return entries
