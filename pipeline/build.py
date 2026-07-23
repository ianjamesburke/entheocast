"""Build-time site generator. Renders index.html from data/entries.json + Jinja2 template.

Run directly: uv run python build.py
Called by run.py after entries are written.

index.html is a generated artifact — edit pipeline/templates/index.html.j2, not the output.
"""

import json
from datetime import date, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

import dates
from weekly import current_week_key

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

# How far back "Featured This Week" may reach. The corpus contains trials registered
# as far back as 2004; they enter the dataset on a backfill and would otherwise rank
# as this week's news, because ingest date says nothing about publication date.
FEATURED_WINDOW_DAYS = 180

# Type importance, used only to break ties between entries published the same day.
_TYPE_PRIORITY = {
    "regulatory": 6, "news": 5, "phase_3": 4,
    "phase_2": 3, "meta_analysis": 3, "phase_1": 2, "observational": 2,
}


def published(entry: dict) -> date | None:
    """Publication date, not ingest date. None when the source gave nothing usable."""
    return dates.parse(entry.get("date"))


def blurb(entry: dict) -> str | None:
    """Display text for a card: the LLM-extracted outcome if the entry has one,
    otherwise the condensed source abstract."""
    return entry.get("outcome_summary") or entry.get("abstract")


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


def _recent_pool(entries: list[dict], today: date) -> list[dict]:
    """Notable entries published inside the featured window, newest first."""
    cutoff = today - timedelta(days=FEATURED_WINDOW_DAYS)
    pool = []
    for e in entries:
        pub = published(e)
        if pub and cutoff <= pub <= today and _is_notable(e):
            pool.append((pub, e))
    pool.sort(key=lambda pair: (pair[0], pair[1].get("id", "")), reverse=True)
    return [e for _, e in pool]


def select_spotlight(entries: list[dict], today: date | None = None) -> dict | None:
    """Single hero item: the most recently published notable entry that has something
    to say. Ranked on publication date, so a backfill of old records can never
    displace the week's actual news."""
    today = today or date.today()
    pool = _recent_pool(entries, today)
    if not pool:
        return None
    return max(
        pool,
        key=lambda e: (
            1 if blurb(e) else 0,
            published(e) or date.min,
            _TYPE_PRIORITY.get(e.get("type") or "", 1),
            e.get("id", ""),
        ),
    )


def select_featured(
    entries: list[dict],
    n: int = 3,
    exclude_ids: frozenset[str] = frozenset(),
    today: date | None = None,
) -> list[dict]:
    """Most recently published notable entries, preferring distinct compounds and
    entries that carry a summary or abstract. exclude_ids avoids repeating the hero."""
    today = today or date.today()
    pool = [e for e in _recent_pool(entries, today) if e.get("id") not in exclude_ids]
    # Stable sort: pool is already newest-first, so this only lifts entries with text.
    pool.sort(key=lambda e: 0 if blurb(e) else 1)

    selected: list[dict] = []
    used_compounds: set[str] = set()
    for e in pool:
        compound = e.get("compound") or "other"
        if compound not in used_compounds:
            selected.append(e)
            used_compounds.add(compound)
        if len(selected) >= n:
            break

    selected_ids = {e.get("id") for e in selected}
    for e in pool:
        if len(selected) >= n:
            break
        if e.get("id") not in selected_ids:
            selected.append(e)
            selected_ids.add(e.get("id"))

    return selected[:n]


def select_feed(entries: list[dict], n: int = 10, today: date | None = None) -> list[dict]:
    """Latest published entries, regardless of topic or notability.

    Future dates are excluded: ClinicalTrials.gov reports a study's *planned* start,
    so trials scheduled years out would otherwise permanently head the feed.
    """
    today = today or date.today()
    dated = [(p, e) for e in entries if (p := published(e)) and p <= today]
    dated.sort(key=lambda pair: (pair[0], pair[1].get("id", "")), reverse=True)
    return [e for _, e in dated[:n]]


def format_date(raw: str | None) -> str:
    """Human-readable publication date for display. Empty when unknown."""
    parsed = dates.parse(raw)
    return parsed.strftime("%b %-d, %Y") if parsed else ""


def build(entries_path: Path | None = None) -> None:
    if entries_path is None:
        entries_path = REPO_ROOT / "data" / "entries.json"

    entries: list[dict] = json.loads(entries_path.read_text())
    today = date.today()
    week_key, week_num = current_week_key(today)

    spotlight = select_spotlight(entries, today=today)
    exclude = frozenset({spotlight["id"]}) if spotlight and spotlight.get("id") else frozenset()
    featured = select_featured(entries, exclude_ids=exclude, today=today)
    feed = select_feed(entries)

    context = {
        "entries": entries,
        "total": len(entries),
        "spotlight": spotlight,
        "featured": featured,
        "feed": feed,
        "week_key": week_key,
        "week_num": week_num,
        "month_year": today.strftime("%B %Y"),
        "compound_labels": COMPOUND_LABELS,
        "type_labels": TYPE_LABELS,
        "compound_order": COMPOUND_ORDER,
    }

    env = Environment(
        loader=FileSystemLoader(PIPELINE_DIR / "templates"),
        autoescape=True,
    )
    env.filters["fmt_date"] = format_date
    env.filters["blurb"] = blurb
    template = env.get_template("index.html.j2")
    html = template.render(**context)

    out_path = REPO_ROOT / "index.html"
    out_path.write_text(html)
    print(f"Built {out_path} ({len(entries)} entries, week {week_key})")


if __name__ == "__main__":
    build()
