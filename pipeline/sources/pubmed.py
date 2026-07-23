import xml.etree.ElementTree as ET
from datetime import date

import httpx

import dates
import relevance
from classify import detect_compound, detect_condition
from dedup import make_id
from snippet import condense

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
QUERY = "psilocybin OR MDMA OR LSD OR ketamine OR DMT OR ibogaine OR ayahuasca OR mescaline"


def _fetch_abstracts(client: httpx.Client, uids: list[str]) -> dict[str, str]:
    """Map PMID -> abstract text. efetch is a separate call from esummary; a failure
    here degrades the entry to no abstract rather than dropping it."""
    if not uids:
        return {}
    try:
        resp = client.get(
            f"{BASE}/efetch.fcgi",
            params={"db": "pubmed", "id": ",".join(uids), "retmode": "xml"},
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
    except Exception as e:
        print(f"PubMed abstract fetch error: {e}")
        return {}

    abstracts: dict[str, str] = {}
    for article in root.iter("PubmedArticle"):
        pmid_el = article.find(".//PMID")
        if pmid_el is None or not pmid_el.text:
            continue
        # Structured abstracts split across labelled sections; join in document order.
        parts = ["".join(seg.itertext()).strip() for seg in article.iter("AbstractText")]
        text = " ".join(p for p in parts if p)
        if text:
            abstracts[pmid_el.text] = text
    return abstracts


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

        abstracts = _fetch_abstracts(client, ids)

    entries = []
    for uid in ids:
        art = result.get(uid)
        if not art:
            continue

        title = art.get("title", "")
        abstract = abstracts.get(uid, "")

        # The query matches any field, so most hits are unrelated papers that merely
        # cite a compound name or reuse one of its acronyms in another sense.
        if not relevance.is_relevant(title, abstract):
            continue

        doi = next((id_["value"] for id_ in art.get("articleids", []) if id_["idtype"] == "doi"), None)
        url = f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"
        haystack = f"{title} {abstract}"
        compound = detect_compound(haystack)
        condition = detect_condition(haystack)

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
            "date": dates.to_iso(art.get("pubdate")),
            "abstract": condense(abstract),
            "outcome_summary": None,
            "doi": doi,
            "url": url,
            "source": "PubMed",
            "first_seen": str(date.today()),
        })

    return entries
