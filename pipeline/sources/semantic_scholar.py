import httpx
from datetime import date

import relevance
from classify import detect_compound, detect_condition
from dedup import make_id
from snippet import condense

BASE = "https://api.semanticscholar.org/graph/v1/paper/search"
QUERY = "psilocybin | MDMA | LSD | ketamine | DMT | ibogaine | ayahuasca | mescaline"
FIELDS = "title,year,externalIds,publicationTypes,abstract"


def _classify_type(pub_types: list[str]) -> str:
    types_lower = [t.lower() for t in pub_types]
    if "review" in types_lower:
        return "meta_analysis"
    if "clinical trial" in types_lower:
        return "phase_2"
    return "phase_2"


def fetch(min_year: int | None = None) -> list[dict]:
    params: dict = {"query": QUERY, "limit": 100, "fields": FIELDS}
    if min_year:
        params["year"] = f"{min_year}-"

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(BASE, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        print(f"Semantic Scholar fetch error: {e}")
        return []

    entries = []
    seen_ids: set[str] = set()
    for paper in data.get("data", []):
        title = paper.get("title", "")
        abstract = paper.get("abstract") or ""

        # The OR query matches on any field; most hits merely cite a compound name.
        if not relevance.is_relevant(title, abstract):
            continue

        year = paper.get("year")
        pub_date = f"{year}-01-01" if year else None
        external_ids = paper.get("externalIds") or {}
        doi = external_ids.get("DOI")
        url = f"https://www.semanticscholar.org/paper/{paper['paperId']}" if paper.get("paperId") else ""
        compound = detect_compound(title + " " + abstract)
        condition = detect_condition(title + " " + abstract)
        pub_types = paper.get("publicationTypes") or []
        entry_id = make_id(title, doi, url)

        if entry_id not in seen_ids:
            seen_ids.add(entry_id)
            entries.append({
                "id": entry_id,
                "title": title,
                "compound": compound,
                "type": _classify_type(pub_types),
                "institution": None,
                "condition": condition,
                "sample_size": None,
                "status": "published",
                "date": pub_date,
                "abstract": condense(abstract),
                "outcome_summary": None,
                "doi": doi,
                "url": url,
                "source": "Semantic Scholar",
                "first_seen": str(date.today()),
            })

    return entries
