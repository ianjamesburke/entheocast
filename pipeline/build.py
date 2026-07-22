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


# Type importance, used only to break ties within the same first_seen date.
_TYPE_PRIORITY = {
    "regulatory": 6, "news": 5, "phase_3": 4,
    "phase_2": 3, "meta_analysis": 3, "phase_1": 2, "observational": 2,
}


def _is_notable(entry: dict) -> bool:
    """Regulatory/news is always eligible; research must name both a compound and a
    psychiatric condition. This filters out ketamine/esketamine anesthesia and other
    off-topic trials that mention a compound but aren't psychedelic-psychiatry research."""
    if entry.get("type") in ("regulatory", "news"):
        return True
    return (
        entry.get("compound") not in (None, "", "other")
        and entry.get("condition") not in (None, "", "other")
    )


def _spotlight_rank(entry: dict) -> tuple:
    # Recency dominates; type importance and a present summary break ties within a date.
    return (
        _sort_key(entry),
        _TYPE_PRIORITY.get(entry.get("type") or "", 1),
        1 if entry.get("outcome_summary") else 0,
        entry.get("id", ""),
    )


def select_spotlight(entries: list[dict]) -> dict | None:
    """Single hero item: the most recent notable entry. Regulatory/news reclaims
    the hero automatically when fresh ones exist; otherwise the latest late-phase
    trial or study fills it. Never gated on outcome_summary, so it can't go stale."""
    notable = [e for e in entries if _is_notable(e)]
    return max(notable, key=_spotlight_rank) if notable else None


def select_featured(
    entries: list[dict], n: int = 3, exclude_ids: frozenset[str] = frozenset()
) -> list[dict]:
    """Top n most recent notable entries, distinct compounds preferred. Recency-driven
    (not summary-gated) so it refreshes every week; exclude_ids avoids duplicating the
    spotlight hero."""
    pool = sorted(
        [e for e in entries if _is_notable(e) and e.get("id") not in exclude_ids],
        key=lambda e: (_sort_key(e), e.get("id", "")),
        reverse=True,
    )
    selected: list[dict] = []
    used_compounds: set[str] = set()

    for e in pool:
        compound = e.get("compound") or "other"
        if compound not in used_compounds:
            selected.append(e)
            used_compounds.add(compound)
        if len(selected) >= n:
            break

    for e in pool:
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
    exclude = frozenset({spotlight["id"]}) if spotlight and spotlight.get("id") else frozenset()
    featured = select_featured(entries, exclude_ids=exclude)
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
