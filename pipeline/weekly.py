"""Weekly issue generator.

Reads data/entries.json, identifies entries added since the most recent Sunday,
writes data/weekly/YYYY-WNN.json and weekly/YYYY-WNN.html.
"""

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Compound display order and labels
COMPOUND_ORDER = [
    "psilocybin", "mdma", "ketamine", "lsd", "dmt",
    "ibogaine", "ayahuasca", "mescaline", "other",
]
COMPOUND_LABELS = {
    "psilocybin": "Psilocybin",
    "mdma": "MDMA",
    "lsd": "LSD",
    "ketamine": "Ketamine",
    "dmt": "DMT",
    "ibogaine": "Ibogaine",
    "ayahuasca": "Ayahuasca",
    "mescaline": "Mescaline",
    "other": "Other",
}

TYPE_LABELS = {
    "phase_1": "Phase 1",
    "phase_2": "Phase 2",
    "phase_3": "Phase 3",
    "observational": "Observational",
    "meta_analysis": "Meta-analysis",
    "regulatory": "Regulatory",
    "news": "News",
    "preprint": "Preprint",
    "case_study": "Case Study",
}


def last_sunday(today: date) -> date:
    """Return the most recent Sunday (today if today is Sunday)."""
    days_back = (today.weekday() + 1) % 7
    return today - timedelta(days=days_back)


def week_label(sunday: date) -> tuple[str, str]:
    """Return (iso_key, display_label) for the week starting on sunday."""
    iso_year, iso_week, _ = sunday.isocalendar()
    key = f"{iso_year}-W{iso_week:02d}"
    week_end = sunday + timedelta(days=6)
    label = f"Week {iso_week} — {sunday.strftime('%B %-d')}–{week_end.strftime('%-d, %Y')}"
    return key, label


def parse_first_seen(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def entry_line(entry: dict) -> str:
    parts = []
    etype = TYPE_LABELS.get(entry.get("type", ""), entry.get("type", ""))
    if etype:
        parts.append(etype)
    inst = entry.get("institution")
    if inst:
        parts.append(inst)
    n = entry.get("sample_size")
    if n:
        parts.append(f"n={n}")
    status = entry.get("status")
    if status and status not in ("published", "other"):
        parts.append(status)
    meta = ", ".join(parts)

    title = entry.get("title", "Untitled")
    url = entry.get("url", "")
    summary = entry.get("outcome_summary")

    line = f'<a href="{url}" target="_blank" rel="noopener">{title}</a>'
    if meta:
        line += f" ({meta})"
    if summary:
        line += f" — {summary}"
    return line


def generate(since: date | None = None, all_entries_path: str = "data/entries.json") -> dict:
    """Generate weekly issue. Returns the JSON data dict."""
    repo_root = Path(__file__).parent.parent
    entries_path = repo_root / all_entries_path

    all_entries: list[dict] = json.loads(entries_path.read_text())
    today = date.today()
    week_start = since or last_sunday(today)
    week_key, week_display = week_label(week_start)

    new_entries = [
        e for e in all_entries
        if (fs := parse_first_seen(e.get("first_seen"))) and fs >= week_start
    ]

    # Group by compound
    by_compound: dict[str, list[dict]] = {}
    for entry in new_entries:
        compound = entry.get("compound") or "other"
        by_compound.setdefault(compound, []).append(entry)

    # Compounds represented (in display order)
    compounds_present = [c for c in COMPOUND_ORDER if c in by_compound]
    # Any compounds not in ORDER list
    for c in sorted(by_compound):
        if c not in COMPOUND_ORDER:
            compounds_present.append(c)

    data = {
        "week": week_key,
        "label": week_display,
        "week_start": str(week_start),
        "generated": str(today),
        "stats": {
            "total_entries": len(all_entries),
            "new_this_week": len(new_entries),
            "compounds_represented": len(compounds_present),
        },
        "by_compound": {
            c: by_compound[c] for c in compounds_present
        },
    }

    # Write JSON
    json_dir = repo_root / "data" / "weekly"
    json_dir.mkdir(parents=True, exist_ok=True)
    json_path = json_dir / f"{week_key}.json"
    json_path.write_text(json.dumps(data, indent=2))
    print(f"Wrote {json_path}")

    # Write HTML
    html_dir = repo_root / "weekly"
    html_dir.mkdir(parents=True, exist_ok=True)
    html_path = html_dir / f"{week_key}.html"
    html_path.write_text(_render_html(data))
    print(f"Wrote {html_path}")

    return data


def _render_html(data: dict) -> str:
    stats = data["stats"]
    compounds_section = ""
    for compound, entries in data["by_compound"].items():
        label = COMPOUND_LABELS.get(compound, compound.title())
        items = "\n".join(f"      <li>{entry_line(e)}</li>" for e in entries)
        compounds_section += f"""
    <section class="compound-group">
      <h3>{label}</h3>
      <ul>
{items}
      </ul>
    </section>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data['label']} — Entheocast</title>
  <link rel="stylesheet" href="../style.css">
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 860px; margin: 2rem auto; padding: 0 1.5rem; color: #1a1a1a; }}
    h1 {{ font-size: 1.6rem; margin-bottom: 0.25rem; }}
    .subtitle {{ color: #555; margin-bottom: 2rem; font-size: 0.95rem; }}
    .stats {{ background: #f5f5f5; padding: 1rem 1.25rem; border-radius: 6px; margin-bottom: 2rem; }}
    .stats p {{ margin: 0.2rem 0; font-size: 0.9rem; }}
    h2 {{ font-size: 1.2rem; border-bottom: 2px solid #e0e0e0; padding-bottom: 0.4rem; margin-top: 2rem; }}
    h3 {{ font-size: 1rem; color: #333; margin: 1.25rem 0 0.4rem; }}
    ul {{ padding-left: 1.25rem; }}
    li {{ margin: 0.4rem 0; font-size: 0.92rem; line-height: 1.5; }}
    a {{ color: #2563eb; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    nav {{ margin-bottom: 1.5rem; font-size: 0.9rem; }}
    nav a {{ color: #555; }}
  </style>
</head>
<body>
  <nav><a href="../index.html">← Entheocast</a></nav>
  <h1>{data['label']}</h1>
  <p class="subtitle">Generated {data['generated']} · <a href="../data/weekly/{data['week']}.json">raw JSON</a></p>

  <div class="stats">
    <p><strong>New this week:</strong> {stats['new_this_week']}</p>
    <p><strong>Total entries:</strong> {stats['total_entries']}</p>
    <p><strong>Compounds represented:</strong> {stats['compounds_represented']}</p>
  </div>

  <h2>New This Week ({stats['new_this_week']} entries)</h2>
{compounds_section if compounds_section else '  <p>No new entries this week.</p>'}

</body>
</html>
"""


if __name__ == "__main__":
    # Allow --since YYYY-MM-DD to override the week start
    since_date: date | None = None
    if "--since" in sys.argv:
        idx = sys.argv.index("--since")
        since_date = datetime.strptime(sys.argv[idx + 1], "%Y-%m-%d").date()

    data = generate(since=since_date)
    s = data["stats"]
    print(f"\n{data['label']}")
    print(f"  New this week: {s['new_this_week']}")
    print(f"  Total entries: {s['total_entries']}")
    print(f"  Compounds:     {s['compounds_represented']}")
