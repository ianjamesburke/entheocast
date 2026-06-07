import httpx
from datetime import date, timedelta
from dedup import make_id

BASE = "https://api.biorxiv.org/details"
COMPOUND_KEYWORDS = ["psilocybin", "mdma", "lsd", "ketamine", "dmt", "ibogaine", "ayahuasca", "mescaline"]
SERVERS = ["biorxiv", "medrxiv"]


def _detect_compound(text: str) -> str:
    t = text.lower()
    for c in COMPOUND_KEYWORDS:
        if c in t:
            return c
    return "other"


def _detect_condition(text: str) -> str:
    t = text.lower()
    cond_map = {
        "depression": "depression",
        "ptsd": "PTSD",
        "anxiety": "anxiety",
        "addiction": "addiction",
        "ocd": "OCD",
        "eating disorder": "eating_disorder",
        "cluster headache": "cluster_headache",
    }
    for k, v in cond_map.items():
        if k in t:
            return v
    return "other"


def fetch(start_date: str | None = None) -> list[dict]:
    if not start_date:
        start_date = str(date.today() - timedelta(days=90))
    end_date = str(date.today())

    all_entries = []
    for server in SERVERS:
        url = f"{BASE}/{server}/{start_date}/{end_date}/0"
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            print(f"bioRxiv fetch error ({server}): {e}")
            continue

        for paper in data.get("collection", []):
            title = paper.get("title", "")
            abstract = paper.get("abstract", "")
            text = (title + " " + abstract).lower()
            if not any(kw in text for kw in COMPOUND_KEYWORDS):
                continue

            doi = paper.get("doi")
            paper_url = f"https://doi.org/{doi}" if doi else ""
            pub_date = paper.get("date", str(date.today()))

            all_entries.append({
                "id": make_id(title, doi, paper_url),
                "title": title,
                "compound": _detect_compound(title + " " + abstract),
                "type": "preprint",
                "institution": paper.get("institution"),
                "condition": _detect_condition(title + " " + abstract),
                "sample_size": None,
                "status": "published",
                "date": pub_date,
                "outcome_summary": None,
                "doi": doi,
                "url": paper_url,
                "source": "bioRxiv/medRxiv",
                "first_seen": str(date.today()),
            })

    seen_ids: set[str] = set()
    deduped = []
    for e in all_entries:
        if e["id"] not in seen_ids:
            seen_ids.add(e["id"])
            deduped.append(e)
    return deduped
