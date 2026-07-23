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

### Relevance screening

Two stages, in this order, because the cheap one makes the expensive one cheaper.

1. **`pipeline/relevance.py`** — pattern matching at ingest. Removes lexical false positives for free: LSD is also lumpy skin disease and laparoscopic splenectomy, DMT is also disease-modifying therapy. Deterministic and reviewable in git.
2. **`pipeline/judge.py`** — an LLM verdict on what survives. Pattern matching cannot tell "Ketamine for Treatment-Resistant Depression" from "Anaesthetic management of dogs": both name a compound unambiguously, and the difference is context.

Verdicts are stored on the entry, so **each entry is judged exactly once**. The weekly run screens only what dedup identified as new. Rejected entries stay in `data/entries.json` as an audit trail — a re-fetch cannot resurrect them — but no page renders them.

```bash
uv run python judge.py --dry-run      # how many entries lack a current verdict
uv run python judge.py                # judge them
uv run python judge.py --revision 2   # re-judge after changing the prompt
```

Bump `PROMPT_REVISION` in `judge.py` when you change `RELEVANCE_PROMPT`; entries judged under the old revision are then re-screened, and only those. Changing `MODEL` invalidates verdicts the same way.

A failed call leaves an entry **unjudged, not rejected**, and unjudged entries render. A provider outage can never silently empty the site.

## Operations

Everything swappable is isolated to one file. Two vendors cost money; nothing else does.

### Switching the LLM

Edit `MODEL` in `pipeline/llm.py`. Any [OpenRouter model id](https://openrouter.ai/models) works — the client is the OpenAI SDK pointed at OpenRouter's base URL, so there is no vendor-specific code to change.

```python
MODEL = "google/gemini-2.5-flash-lite"
MAX_TOKENS = 500
```

Two things to know before picking one:

- **Reasoning models spend `MAX_TOKENS` on hidden reasoning before emitting any content.** A budget that is fine for a normal model returns empty or truncated JSON on a reasoning model. If extraction starts failing with JSON parse errors right after a model swap, raise `MAX_TOKENS` first — that is almost always the cause.
- **`:free` model variants are rate-capped and get discontinued without warning.** Both have already broken this pipeline: `moonshotai/kimi-k2.6:free` was withdrawn and every extraction 404'd for weeks. The account is on paid credits, so the free variants buy nothing.

Cost is not a real constraint here. A weekly run makes roughly 30–40 extraction calls:

| Model | $/M in | $/M out | ~$/run | Speed |
| --- | --- | --- | --- | --- |
| `google/gemini-2.5-flash-lite` (current) | 0.10 | 0.40 | ~$0.01 | ~1s/call |
| `openai/gpt-oss-20b` | 0.03 | 0.13 | ~$0.01 | ~22s/call |
| `moonshotai/kimi-k2.6` | 0.68 | 3.42 | ~$0.23 | — |

Verify current pricing rather than trusting this table:

```bash
curl -s https://openrouter.ai/api/v1/models | jq '.data[] | select(.id=="google/gemini-2.5-flash-lite") | .pricing'
```

Check remaining credit and whether the key is on the free tier:

```bash
curl -s https://openrouter.ai/api/v1/key -H "Authorization: Bearer $OPENROUTER_API_KEY" | jq
```

### Switching the search engine

`pipeline/tavily_client.py` is the entire integration — one `search()` function returning `{url, title, content, raw_content, published_date}`. Every Tier 3 source calls it through `pipeline/sources/tavily_base.py` and touches nothing vendor-specific. To swap providers, reimplement `search()` to return that shape.

Two Tavily behaviours the pipeline depends on:

- `topic="news"` is required. On the default topic Tavily returns no `published_date`, which forced entries to be stamped with the ingest date, and the `days` recency window has no effect.
- `include_raw_content=True` returns full page text, which removed the need for a separate article-reader service.

### Secrets

| Key | Used by | Local | CI |
| --- | --- | --- | --- |
| `OPENROUTER_API_KEY` | `pipeline/llm.py` | `.env` | repo secret |
| `TAVILY_API_KEY` | `pipeline/tavily_client.py` | `.env` | repo secret |

CI reads them from **GitHub repo secrets** (Settings → Secrets and variables → Actions), injected in `.github/workflows/weekly.yml`. Tier 1 needs neither key, so the pipeline still produces data if both are missing — it just loses Tier 2/3.

### Other knobs

| Change | File |
| --- | --- |
| Run schedule | `.github/workflows/weekly.yml` (cron) |
| Which tiers run | `weekly.yml` → `run.py --tier 3` |
| What counts as on-topic (patterns) | `pipeline/relevance.py` |
| What counts as on-topic (LLM) | `RELEVANCE_PROMPT` in `pipeline/llm.py` |
| Compound / condition taxonomy | `pipeline/classify.py` |
| Accepted date formats | `pipeline/dates.py` |
| How far back "Featured" reaches | `FEATURED_WINDOW_DAYS` in `pipeline/build.py` |
| Abstract snippet length | `MAX_CHARS` in `pipeline/snippet.py` |
| Page layout | `pipeline/templates/index.html.j2` |

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
