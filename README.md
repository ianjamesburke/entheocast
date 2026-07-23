# Entheocast

Psychedelic clinical trials, regulatory updates, and research aggregated weekly into a structured open dataset. Live at [ianjamesburke.github.io/entheocast](https://ianjamesburke.github.io/entheocast).

GitHub Actions runs the pipeline every Sunday night. Data, not commentary.

## Stack

| Layer | What it is | Where |
| --- | --- | --- |
| Pipeline | Python 3.11+, managed by `uv` | `pipeline/` |
| Site | Static HTML, vanilla CSS, vanilla JS. No framework, no database | repo root |
| Templating | Jinja2 — `index.html` is generated, never hand-edited | `pipeline/templates/index.html.j2` |
| Hosting | GitHub Pages, deployed from the workflow | `.github/workflows/weekly.yml` |
| Schedule | GitHub Actions cron, Sunday 8pm ET | `.github/workflows/weekly.yml` |
| Search | Tavily (Tier 3 discovery) | `pipeline/tavily_client.py` |
| LLM | OpenRouter (Tier 2/3 extraction) | `pipeline/llm.py` |
| Storage | One JSON file. There is no database | `data/entries.json` |

### Data sources

**Tier 1** — structured APIs, no LLM, no key required:
PubMed, ClinicalTrials.gov, Semantic Scholar, bioRxiv/medRxiv.

**Tier 2** — RSS feeds, LLM-extracted: MAPS, Chacruna, Lucid News.

**Tier 3** — Tavily search, LLM-extracted: Psychedelic Alpha, FDA, Compass Pathways, Atai Life Sciences, general news.

Operational how-tos (swapping the LLM or search provider, secrets, all the tuning knobs) live in `CLAUDE.md` and the local, gitignored `OPERATIONS.md` — not here.

## Run locally

```bash
cp .env.example .env          # add TAVILY_API_KEY and OPENROUTER_API_KEY

cd pipeline && uv sync
uv run python run.py --tier 3   # omit --tier and it defaults to 2, skipping Tier 3
```

Writes `data/entries.json`, generates `data/weekly/YYYY-WNN.json` + `weekly/YYYY-WNN.html`, rebuilds `weekly/index.html`, then renders `index.html`.

Individual stages:

```bash
uv run python build.py     # re-render index.html from existing data
uv run python weekly.py    # regenerate the current weekly issue and its index
```

## Entry schema

`data/entries.json` is a flat array. One object per study, trial, or article.

| Field | Notes |
| --- | --- |
| `id` | sha256 of title + doi + url. Dedup key |
| `title`, `url`, `source` | |
| `compound` | psilocybin, mdma, ketamine, lsd, dmt, ibogaine, ayahuasca, mescaline, other |
| `type` | phase_1/2/3, observational, meta_analysis, regulatory, news, preprint |
| `condition` | depression, PTSD, anxiety, addiction, OCD, eating_disorder, cluster_headache, other |
| `date` | Publication date, ISO `YYYY-MM-DD`. Null when the source gave nothing usable |
| `first_seen` | When the pipeline ingested it. Not a publication date — never rank on this |
| `abstract` | Condensed source abstract, verbatim |
| `outcome_summary` | LLM-extracted finding. Tier 2/3 only |
| `relevance` | `{relevant, reason, model, revision, judged}`. Absent means not yet screened, which renders |
| `institution`, `sample_size`, `status`, `doi` | Nullable |

Deduplication derives from `data/entries.json` itself. There is deliberately no side-car state file: one previously existed, CI never committed it, and every run re-appended the entire back catalogue.

MIT
