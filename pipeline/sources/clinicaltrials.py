import json
import subprocess
import urllib.parse
from datetime import date
from dedup import make_id

BASE = "https://clinicaltrials.gov/api/v2/studies"
COMPOUND_KEYWORDS = ["psilocybin", "mdma", "lsd", "ketamine", "dmt", "ibogaine", "ayahuasca", "mescaline"]

PHASE_MAP = {
    "PHASE1": "phase_1",
    "PHASE2": "phase_2",
    "PHASE3": "phase_3",
    "NA": "observational",
}

STATUS_MAP = {
    "RECRUITING": "recruiting",
    "ACTIVE_NOT_RECRUITING": "active",
    "COMPLETED": "completed",
    "NOT_YET_RECRUITING": "recruiting",
    "TERMINATED": "completed",
    "WITHDRAWN": "completed",
    "SUSPENDED": "active",
    "ENROLLING_BY_INVITATION": "recruiting",
}

CONDITION_MAP = {
    "depression": "depression",
    "ptsd": "PTSD",
    "post-traumatic": "PTSD",
    "anxiety": "anxiety",
    "addiction": "addiction",
    "substance use": "addiction",
    "ocd": "OCD",
    "obsessive": "OCD",
    "eating disorder": "eating_disorder",
    "anorexia": "eating_disorder",
    "bulimia": "eating_disorder",
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


def _curl_get(url: str, params: dict) -> dict:
    qs = urllib.parse.urlencode(params)
    full_url = f"{url}?{qs}"
    result = subprocess.run(
        ["curl", "-s", "--compressed", full_url],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"curl failed: {result.stderr}")
    return json.loads(result.stdout)


def fetch(min_date: str | None = None) -> list[dict]:
    all_entries = []
    for compound in COMPOUND_KEYWORDS:
        params = {
            "query.intr": compound,
            "pageSize": 50,
            "fields": "NCTId,BriefTitle,OverallStatus,Phase,LeadSponsorName,EnrollmentCount,StartDate,PrimaryCompletionDate,Condition,InterventionName",
        }
        try:
            data = _curl_get(BASE, params)
        except Exception as e:
            print(f"ClinicalTrials fetch error for {compound}: {e}")
            continue

        for study in data.get("studies", []):
            proto = study.get("protocolSection", {})
            id_mod = proto.get("identificationModule", {})
            status_mod = proto.get("statusModule", {})
            design_mod = proto.get("designModule", {})
            sponsor_mod = proto.get("sponsorCollaboratorsModule", {})
            enroll_mod = design_mod.get("enrollmentInfo", {})

            nct_id = id_mod.get("nctId", "")
            title = id_mod.get("briefTitle", "")
            status_raw = status_mod.get("overallStatus", "")
            phases = design_mod.get("phases", [])
            phase_raw = phases[0] if phases else "NA"
            institution = sponsor_mod.get("leadSponsor", {}).get("name")
            sample_size = enroll_mod.get("count")
            start_date = status_mod.get("startDateStruct", {}).get("date", "")[:10] or str(date.today())
            if min_date and start_date < min_date:
                continue

            url = f"https://clinicaltrials.gov/study/{nct_id}"
            compound_detected = _detect_compound(title)
            conditions_list = proto.get("conditionsModule", {}).get("conditions", [])
            condition_text = " ".join(conditions_list)
            condition = _detect_condition(condition_text + " " + title)

            all_entries.append({
                "id": make_id(title, None, url),
                "title": title,
                "compound": compound_detected,
                "type": PHASE_MAP.get(phase_raw, "observational"),
                "institution": institution,
                "condition": condition,
                "sample_size": sample_size,
                "status": STATUS_MAP.get(status_raw, "active"),
                "date": start_date,
                "outcome_summary": None,
                "doi": None,
                "url": url,
                "source": "ClinicalTrials.gov",
                "first_seen": str(date.today()),
            })

    seen_ids: set[str] = set()
    deduped = []
    for e in all_entries:
        if e["id"] not in seen_ids:
            seen_ids.add(e["id"])
            deduped.append(e)
    return deduped
