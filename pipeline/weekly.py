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


def current_week_key(today: date) -> tuple[str, int]:
    """(key, week number) of the issue covering `today`.

    An issue week runs Sunday to Saturday, but ISO weeks start on Monday, so the key
    must be derived from the issue's Sunday — not from today. Deriving it from today
    made index.html link to a week number the generator never wrote on any day except
    Sunday.
    """
    key, _ = week_label(last_sunday(today))
    return key, int(key.split("-W")[1])


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
    summary = entry.get("outcome_summary") or entry.get("abstract")

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

    corpus: list[dict] = json.loads(entries_path.read_text())
    # Entries the relevance screen rejected are kept in the corpus for audit but
    # are not part of any issue. Unjudged entries pass: a failed call must not
    # silently shrink a week's issue.
    all_entries = [
        e for e in corpus
        if not isinstance(e.get("relevance"), dict)
        or e["relevance"].get("relevant") is not False
    ]
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

    index_path = html_dir / "index.html"
    index_path.write_text(_render_index(json_dir))
    print(f"Wrote {index_path}")

    return data


def _render_index(json_dir: Path) -> str:
    """Rebuild weekly/index.html from every issue snapshot on disk.

    Generated on every run: the previous hand-written index listed a single issue and
    never grew, so published issues were unreachable from the site.
    """
    issues = []
    for path in sorted(json_dir.glob("*.json"), reverse=True):
        try:
            issues.append(json.loads(path.read_text()))
        except (OSError, json.JSONDecodeError) as e:
            print(f"Skipping unreadable weekly snapshot {path}: {e}")

    rows_by_year: dict[str, list[str]] = {}
    for issue in issues:
        stats = issue.get("stats", {})
        week = issue.get("week", "")
        year = week.split("-")[0] or "Unknown"
        compounds = [
            COMPOUND_LABELS.get(c, c.title())
            for c in list(issue.get("by_compound", {}))[:3]
        ]
        blurb = ", ".join(compounds) + " and more" if compounds else "No new entries"
        label = issue.get("label", week)
        # "Week 30 — July 19–25, 2026" -> the date range alone reads better in a list.
        title = label.split("—", 1)[1].strip() if "—" in label else label
        rows_by_year.setdefault(year, []).append(f"""
  <a href="{week}.html" class="issue-row">
    <div class="issue-num">W{week.split('-W')[-1]}</div>
    <div class="issue-row-body">
      <div class="issue-row-title">{title}</div>
      <div class="issue-row-meta">{stats.get('new_this_week', 0)} entries · {stats.get('compounds_represented', 0)} compounds · {blurb}</div>
    </div>
    <div class="issue-row-cta">Read →</div>
  </a>""")

    sections = "".join(
        f'\n  <div class="section-label">{year}</div>{"".join(rows)}\n'
        for year, rows in sorted(rows_by_year.items(), reverse=True)
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Weekly Issues — Entheocast</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../style.css">
  <script defer src="../molecules.js"></script>
  <style>
    .issue-row {{ display: flex; align-items: center; gap: 1.25rem; padding: 1rem 0; border-bottom: 1px solid var(--border); text-decoration: none; color: inherit; }}
    .issue-row:last-child {{ border-bottom: none; }}
    .issue-row:hover .issue-row-title {{ color: var(--accent); }}
    .issue-num {{ font-family: 'Syne', sans-serif; font-weight: 700; font-size: 1.05rem; color: var(--accent); min-width: 3.5rem; opacity: 0.7; }}
    .issue-row-body {{ flex: 1; }}
    .issue-row-title {{ font-size: 0.9rem; font-weight: 600; color: var(--text); margin-bottom: 0.2rem; transition: color 0.15s; }}
    .issue-row-meta {{ font-size: 0.72rem; color: var(--muted); }}
    .issue-row-cta {{ font-size: 0.72rem; font-weight: 600; color: var(--accent); }}
  </style>
</head>
<body>
<div class="page">
<header>
  <div class="header-inner">
    <a href="../index.html" class="wordmark">ENTHEO<span class="dot">·</span>CAST</a>
    <nav>
      <a href="../index.html">Home</a>
      <a href="../trials.html">Trials</a>
      <a href="../weekly/index.html" class="active">Weekly</a>
      <a href="../podcast.html">Podcast</a>
      <a href="../about.html">About</a>
      <a href="../contact.html">Contact</a>
    </nav>
  </div>
</header>

<main class="main-wrap" style="max-width:720px">
  <div class="page-heading">Weekly Issues</div>
  <p class="page-sub">Every Sunday: new entries, regulatory updates, and research summaries. Generated automatically from the pipeline — no editorial prose added.</p>
{sections}
  <p style="font-size:0.78rem;color:var(--muted);margin-top:2rem;line-height:1.6;">
    New issues are generated automatically every Sunday at 8pm ET via GitHub Actions.
    The pipeline fetches from PubMed, ClinicalTrials.gov, and curated sources, then writes
    a weekly snapshot to <code style="font-size:0.72rem">data/weekly/</code> and generates this HTML.
  </p>
</main>

<footer>
  <span>Entheocast · Open data · MIT</span>
  <span><a href="https://github.com/ianjamesburke/entheocast">GitHub</a></span>
</footer>
</div>
</body>
</html>
"""


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
