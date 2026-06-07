import httpx
from datetime import date
from dedup import make_id

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
QUERY = "psilocybin OR MDMA OR LSD OR ketamine OR DMT OR ibogaine OR ayahuasca OR mescaline"
COMPOUND_KEYWORDS = ["psilocybin", "mdma", "lsd", "ketamine", "dmt", "ibogaine", "ayahuasca", "mescaline"]

CONDITION_MAP = {
    "depression": "depression",
    "ptsd": "PTSD",
    "anxiety": "anxiety",
    "addiction": "addiction",
    "ocd": "OCD",
    "eating disorder": "eating_disorder",
    "cluster headache": "cluster_headache",
}


def _detect_compound(text: str) -> str:
    t = text.lower()
    for c in COMPOUND_KEYWORDS:
        if c in t:
            return c
    return "other"


def _detect_condition(text: str) -> str:
    t = text.lower()
    for k, v in CONDITION_MAP.items():
        if k in t:
            return v
    return "other"


def fetch(min_date: str | None = None) -> list[dict]:
    params = {
        "db": "pubmed",
        "term": QUERY,
        "retmax": 200,
        "retmode": "json",
        "sort": "pub+date",
    }
    if min_date:
        params["mindate"] = min_date
        params["datetype"] = "pdat"

    with httpx.Client(timeout=30) as client:
        search = client.get(f"{BASE}/esearch.fcgi", params=params)
        search.raise_for_status()
        ids = search.json()["esearchresult"]["idlist"]

        if not ids:
            return []

        summary = client.get(f"{BASE}/esummary.fcgi", params={
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "json",
        })
        summary.raise_for_status()
        result = summary.json()["result"]

    entries = []
    for uid in ids:
        art = result.get(uid)
        if not art:
            continue

        title = art.get("title", "")
        pub_date = art.get("pubdate", "")[:10] or str(date.today())
        doi = next((id_["value"] for id_ in art.get("articleids", []) if id_["idtype"] == "doi"), None)
        url = f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"
        compound = _detect_compound(title)
        condition = _detect_condition(title)

        pub_types = [pt.lower() for pt in art.get("pubtype", [])]
        if "clinical trial" in pub_types:
            entry_type = "phase_2"
        elif "meta-analysis" in pub_types:
            entry_type = "meta_analysis"
        elif "review" in pub_types:
            entry_type = "meta_analysis"
        else:
            entry_type = "phase_2"

        entries.append({
            "id": make_id(title, doi, url),
            "title": title,
            "compound": compound,
            "type": entry_type,
            "institution": None,
            "condition": condition,
            "sample_size": None,
            "status": "published",
            "date": pub_date,
            "outcome_summary": None,
            "doi": doi,
            "url": url,
            "source": "PubMed",
            "first_seen": str(date.today()),
        })

    return entries
