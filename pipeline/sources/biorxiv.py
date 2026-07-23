import httpx
from datetime import date, timedelta

import dates
import relevance
from classify import detect_compound, detect_condition
from dedup import make_id
from snippet import condense

BASE = "https://api.biorxiv.org/details"
SERVERS = ["biorxiv", "medrxiv"]


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
            if not relevance.is_relevant(title, abstract):
                continue

            doi = paper.get("doi")
            paper_url = f"https://doi.org/{doi}" if doi else ""
            pub_date = dates.to_iso(paper.get("date"))

            all_entries.append({
                "id": make_id(title, doi, paper_url),
                "title": title,
                "compound": detect_compound(title + " " + abstract),
                "type": "preprint",
                "institution": paper.get("institution"),
                "condition": detect_condition(title + " " + abstract),
                "sample_size": None,
                "status": "published",
                "date": pub_date,
                "abstract": condense(abstract),
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
