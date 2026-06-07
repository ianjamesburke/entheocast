# Entheocast — Product Requirements Document

A GitHub repo + GitHub Pages site that aggregates every psychedelic clinical trial, published study, and regulatory update into one structured, browsable, open dataset. The canonical reference for psychedelic research in 2026.

## What This Is

The billboard-hot-100 of psychedelic science. A structured JSON dataset that updates weekly via automated pipeline, served as a clean static site on GitHub Pages. No framework. No database. The repo IS the product.

The podcast layer comes later (YouTube episodes + transcripts). For now, the site ships with a "Coming Soon" podcast page.

## Architecture

### Stack
- Static HTML + vanilla CSS + vanilla JS on GitHub Pages
- Python pipeline (`pipeline/run.py`) managed with `uv`
- Tavily for web search (discover new research news beyond RSS/API sources)
- Jina Reader for full-page text extraction
- Mimo via OpenRouter for classification/extraction
- GitHub Actions cron: weekly (Sunday 8pm ET)
- Future enhancement: custom domain, Resend newsletter

### Pipeline Approach

Three tiers of data collection, same pattern as the-rapids local news pipeline:

**Tier 1 — Structured APIs (no LLM needed):**
- PubMed E-utilities API
- ClinicalTrials.gov V2 API
- Semantic Scholar API
- bioRxiv/medRxiv API

Direct JSON parsing. Filter by psychedelic compound keywords. Extract into schema.

**Tier 2 — RSS + Jina Reader + Mimo:**
- MAPS.org RSS
- Chacruna Institute RSS
- Lucid News RSS

Get items from feed, Jina Reader pulls full article text, Mimo extracts structured fields into schema.

**Tier 3 — Tavily Web Search + Jina Reader + Mimo:**
- Psychedelic Alpha
- FDA press releases
- Compass Pathways press releases
- Atai Life Sciences press releases
- General psychedelic research news (broad Tavily queries)

Tavily searches for recent psychedelic trial/study/regulatory updates. Jina Reader fetches full pages. Mimo identifies relevant entries and classifies into schema.

**The LLM extracts and classifies. It does NOT write articles or editorialized summaries.**

### Pipeline Sources

```json
[
  {"name": "PubMed", "tier": 1, "type": "api", "url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/", "notes": "E-utilities API. Search: psilocybin OR MDMA OR LSD OR ketamine OR DMT OR ibogaine OR ayahuasca OR mescaline in clinical trials and research articles."},
  {"name": "ClinicalTrials.gov", "tier": 1, "type": "api", "url": "https://clinicaltrials.gov/api/v2/studies", "notes": "V2 API. Filter by condition + intervention keywords. Returns structured JSON."},
  {"name": "Semantic Scholar", "tier": 1, "type": "api", "url": "https://api.semanticscholar.org/graph/v1/paper/search", "notes": "Academic paper search. Catches preprints and new publications."},
  {"name": "bioRxiv/medRxiv", "tier": 1, "type": "api", "url": "https://api.biorxiv.org/details/", "notes": "Preprint servers. Early results before peer review."},
  {"name": "MAPS.org", "tier": 2, "type": "rss", "url": "https://maps.org/feed/", "notes": "Multidisciplinary Association for Psychedelic Studies. Press releases, study updates."},
  {"name": "Chacruna Institute", "tier": 2, "type": "rss", "url": "https://chacruna.net/feed/", "notes": "Cultural and ethical perspectives on psychedelics."},
  {"name": "Lucid News", "tier": 2, "type": "rss", "url": "https://www.lucid.news/feed/", "notes": "Psychedelic journalism. Features, interviews, policy."},
  {"name": "Psychedelic Alpha", "tier": 3, "type": "tavily+jina", "url": "https://psychedelicalpha.com/", "notes": "Industry news aggregator. Regulatory + business angles."},
  {"name": "FDA Press Releases", "tier": 3, "type": "tavily+jina", "url": "https://www.fda.gov/news-events/press-announcements", "notes": "Filter for psychedelic-related approvals, breakthrough therapy designations."},
  {"name": "Compass Pathways", "tier": 3, "type": "tavily+jina", "url": "https://www.compasspathways.com/press-releases/", "notes": "Publicly traded. Phase 2/3 psilocybin trials."},
  {"name": "Atai Life Sciences", "tier": 3, "type": "tavily+jina", "url": "https://www.atai.life/press-releases/", "notes": "Publicly traded. Multiple compound portfolio."},
  {"name": "General News", "tier": 3, "type": "tavily", "queries": ["psychedelic clinical trial 2026", "psilocybin FDA", "MDMA therapy approval", "ketamine treatment study"], "notes": "Broad web search for news not caught by specific sources."}
]
```

### Data Schema

Each entry in `data/entries.json` (append-only, one object per study/trial/update):

```json
{
  "id": "sha256-hash-of-title+doi+url",
  "title": "Study or trial title",
  "compound": "psilocybin | MDMA | LSD | ketamine | DMT | ibogaine | ayahuasca | mescaline | other",
  "type": "phase_1 | phase_2 | phase_3 | observational | meta_analysis | case_study | preprint | regulatory",
  "institution": "Johns Hopkins | Imperial College London | etc.",
  "condition": "depression | PTSD | anxiety | addiction | OCD | eating_disorder | cluster_headache | other",
  "sample_size": null,
  "status": "recruiting | active | completed | published | approved | denied",
  "date": "YYYY-MM-DD",
  "outcome_summary": "One-line result if available, null otherwise",
  "doi": "10.xxxx/... or null",
  "url": "https://...",
  "source": "PubMed | ClinicalTrials.gov | MAPS | etc.",
  "first_seen": "YYYY-MM-DD"
}
```

### Weekly Issues

Auto-generated structured changelogs. NOT prose. NOT AI-written articles.

Format:
```markdown
# Week 23 — June 2-8, 2026

## New This Week (7 entries)

### Psilocybin
- Phase 2 trial for treatment-resistant depression (Johns Hopkins, n=120, recruiting)
- Published: "Long-term outcomes of psilocybin-assisted therapy..." (JAMA Psychiatry)

### MDMA
- FDA advisory committee meeting scheduled for July 15

### Ketamine
- Phase 3 results: "Intranasal esketamine vs placebo..." (completed, positive outcome)

## Stats
- Total entries: 342
- New this week: 7
- Compounds represented: 6
```

The pipeline generates this from new entries added that week, grouped by compound.

### Site Structure

```
index.html            -- homepage: latest weekly issue summary, links to all sections
trials.html           -- full table of all trials, filterable by compound/phase/status/condition (vanilla JS)
weekly/YYYY-WNN.html  -- each weekly digest (generated by pipeline)
podcast.html          -- "Coming Soon" page. Will eventually embed YouTube episodes + transcripts.
about.html            -- what Entheocast is, methodology, list of data sources, link to raw data
data/                 -- raw JSON files (the dataset)
  entries.json        -- all entries
  weekly/             -- per-week JSON snapshots
```

### Site Style

**CHECKPOINT: Present 3 style options before building all pages.**

- **Option A: Clean academic** — white bg, serif headings, minimal color, Nature/Lancet vibes
- **Option B: Dark modern** — dark bg, monospace/sans, neon accent color, hacker-meets-science
- **Option C: Warm editorial** — cream/tan bg, balanced serif+sans, muted earth tones, blog feel

Build all 3 as `index.html` variants. User picks. Apply chosen style to all pages.

## Podcast Section

Ships as "Coming Soon" in v1. The page should look intentional, not broken. Include:
- Brief description of what the podcast will be
- "Subscribe" placeholder (for future YouTube/RSS links)
- Visual that communicates "this is real, just not launched yet"

Eventually this page will show:
- Embedded YouTube episodes
- Episode transcripts
- Weekly summaries paired with the data changelog

## Environment Variables

```
TAVILY_API_KEY=        # Tavily web search
OPENROUTER_API_KEY=    # Mimo via OpenRouter
```

## File Structure

```
entheocast/
  .github/
    workflows/
      weekly.yml       -- cron: Sunday 8pm ET, runs pipeline, commits, deploys Pages
  pipeline/
    pyproject.toml     -- requires-python >= 3.11, dependencies
    sources.json       -- all sources config
    run.py             -- main pipeline script
    seen_urls.json     -- deduplication state
  data/
    entries.json       -- all entries (append-only)
    weekly/            -- per-week snapshots
  index.html
  trials.html
  podcast.html
  about.html
  weekly/              -- generated weekly issue HTML pages
  style.css            -- single shared stylesheet
  script.js            -- filtering logic for trials table
  README.md
  PRD.md               -- this file
  .gitignore
```

## README.md

Short, modeled on github.com/mhollingshead/billboard-hot-100:
- What it is (one paragraph)
- How it works (pipeline overview)
- Data schema
- How to run locally (`cd pipeline && uv sync && uv run python run.py`)
- License: MIT

## What NOT to Build

- No newsletter / Resend integration (future)
- No custom domain (future)
- No podcast audio generation (future)
- No React / Next.js / any framework
- No database
- No AI-written articles or editorialized prose
- No user accounts or community features

## Definition of Done

- [ ] Pipeline runs and produces valid `data/entries.json` with 2026 backfill
- [ ] GitHub Pages site is live with all pages
- [ ] Trials table filters work (compound, phase, status, condition)
- [ ] At least one weekly issue HTML is generated
- [ ] Podcast page shows "Coming Soon" cleanly
- [ ] GitHub Actions cron is configured
- [ ] README is complete
- [ ] PubMed + ClinicalTrials.gov scrapers work reliably (minimum viable)
- [ ] Tavily + Jina Reader pipeline works for at least 2 Tier 3 sources

## Kill Criteria

If site has < 50 GitHub stars and < 1,000 monthly visits after 8 weeks of weekly publishing, kill it.
