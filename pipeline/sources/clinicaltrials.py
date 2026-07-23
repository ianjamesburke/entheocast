import json
import subprocess
import urllib.parse
from datetime import date

import dates
import relevance
from classify import COMPOUND_ORDER, detect_compound, detect_condition
from dedup import make_id
from snippet import condense

BASE = "https://clinicaltrials.gov/api/v2/studies"

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
    for compound in COMPOUND_ORDER:
        params = {
            "query.intr": compound,
            "pageSize": 50,
            "fields": (
                "NCTId,BriefTitle,BriefSummary,OverallStatus,Phase,LeadSponsorName,"
                "EnrollmentCount,StartDate,PrimaryCompletionDate,Condition,InterventionName"
            ),
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
            brief_summary = proto.get("descriptionModule", {}).get("briefSummary", "")
            interventions = " ".join(
                i.get("name", "")
                for i in proto.get("armsInterventionsModule", {}).get("interventions", [])
            )

            # query.intr matches the intervention text, which collides with unrelated
            # procedures sharing a compound acronym (LSD, DMT most often).
            if not relevance.is_relevant(f"{title} {interventions}", brief_summary):
                continue

            status_raw = status_mod.get("overallStatus", "")
            phases = design_mod.get("phases", [])
            phase_raw = phases[0] if phases else "NA"
            institution = sponsor_mod.get("leadSponsor", {}).get("name")
            sample_size = enroll_mod.get("count")
            start_date = dates.to_iso(status_mod.get("startDateStruct", {}).get("date"))
            if min_date and start_date and start_date < min_date:
                continue

            url = f"https://clinicaltrials.gov/study/{nct_id}"
            compound_detected = detect_compound(f"{title} {interventions}")
            conditions_list = proto.get("conditionsModule", {}).get("conditions", [])
            condition_text = " ".join(conditions_list)
            condition = detect_condition(condition_text + " " + title)

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
                "abstract": condense(brief_summary),
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
