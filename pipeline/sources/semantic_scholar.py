import httpx
from datetime import date
from dedup import make_id

BASE = "https://api.semanticscholar.org/graph/v1/paper/search"
COMPOUND_KEYWORDS = ["psilocybin", "mdma", "lsd", "ketamine", "dmt", "ibogaine", "ayahuasca", "mescaline"]
QUERY = "psilocybin | MDMA | LSD | ketamine | DMT | ibogaine | ayahuasca | mescaline"
FIELDS = "title,year,externalIds,publicationTypes,abstract"


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
        year = paper.get("year")
        pub_date = f"{year}-01-01" if year else str(date.today())
        external_ids = paper.get("externalIds") or {}
        doi = external_ids.get("DOI")
        url = f"https://www.semanticscholar.org/paper/{paper['paperId']}" if paper.get("paperId") else ""
        abstract = paper.get("abstract") or ""
        compound = _detect_compound(title + " " + abstract)
        condition = _detect_condition(title + " " + abstract)
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
                "outcome_summary": None,
                "doi": doi,
                "url": url,
                "source": "Semantic Scholar",
                "first_seen": str(date.today()),
            })

    return entries
