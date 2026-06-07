"""Build-time site generator. Renders index.html from data/entries.json + Jinja2 template.

Run directly: uv run python build.py
Called by run.py after entries are written.

index.html is a generated artifact — edit pipeline/templates/index.html.j2, not the output.
"""

import json
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

COMPOUND_ORDER = [
    "psilocybin", "mdma", "ketamine", "lsd", "dmt",
    "ibogaine", "ayahuasca", "mescaline", "other",
]
COMPOUND_LABELS = {
    "psilocybin": "Psilocybin", "mdma": "MDMA", "ketamine": "Ketamine",
    "lsd": "LSD", "dmt": "DMT", "ibogaine": "Ibogaine",
    "ayahuasca": "Ayahuasca", "mescaline": "Mescaline", "other": "Other",
}
TYPE_LABELS = {
    "phase_1": "Phase 1", "phase_2": "Phase 2", "phase_3": "Phase 3",
    "observational": "Observational", "meta_analysis": "Meta-analysis",
    "regulatory": "Regulatory", "news": "News", "preprint": "Preprint",
    "case_study": "Case Study",
}

PIPELINE_DIR = Path(__file__).parent
REPO_ROOT = PIPELINE_DIR.parent


def _sort_key(entry: dict) -> str:
    return entry.get("first_seen") or ""


def select_spotlight(entries: list[dict]) -> dict | None:
    """Most recent regulatory entry with outcome_summary, falling back to news."""
    for preferred_type in ("regulatory", "news"):
        candidates = [
            e for e in entries
            if e.get("type") == preferred_type and e.get("outcome_summary")
        ]
        if candidates:
            return sorted(candidates, key=lambda e: (_sort_key(e), e.get("id", "")), reverse=True)[0]
    return None


def select_featured(entries: list[dict], n: int = 3) -> list[dict]:
    """Top n entries with outcome_summary, distinct compounds preferred."""
    with_summary = sorted(
        [e for e in entries if e.get("outcome_summary")],
        key=lambda e: (_sort_key(e), e.get("id", "")),
        reverse=True,
    )
    selected: list[dict] = []
    used_compounds: set[str] = set()

    for e in with_summary:
        compound = e.get("compound") or "other"
        if compound not in used_compounds:
            selected.append(e)
            used_compounds.add(compound)
        if len(selected) >= n:
            break

    for e in with_summary:
        if e not in selected:
            selected.append(e)
        if len(selected) >= n:
            break

    return selected[:n]


def select_feed(entries: list[dict], n: int = 10) -> list[dict]:
    return sorted(entries, key=lambda e: (_sort_key(e), e.get("id", "")), reverse=True)[:n]


def build(entries_path: Path | None = None) -> None:
    if entries_path is None:
        entries_path = REPO_ROOT / "data" / "entries.json"

    entries: list[dict] = json.loads(entries_path.read_text())
    today = date.today()
    iso_year, iso_week, _ = today.isocalendar()
    week_key = f"{iso_year}-W{iso_week:02d}"

    spotlight = select_spotlight(entries)
    featured = select_featured(entries)
    feed = select_feed(entries)

    context = {
        "entries": entries,
        "total": len(entries),
        "spotlight": spotlight,
        "featured": featured,
        "feed": feed,
        "week_key": week_key,
        "week_num": iso_week,
        "month_year": today.strftime("%B %Y"),
        "compound_labels": COMPOUND_LABELS,
        "type_labels": TYPE_LABELS,
        "compound_order": COMPOUND_ORDER,
    }

    env = Environment(
        loader=FileSystemLoader(PIPELINE_DIR / "templates"),
        autoescape=True,
    )
    template = env.get_template("index.html.j2")
    html = template.render(**context)

    out_path = REPO_ROOT / "index.html"
    out_path.write_text(html)
    print(f"Built {out_path} ({len(entries)} entries, week {week_key})")


if __name__ == "__main__":
    build()
