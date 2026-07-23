# Entheocast — Roadmap

Single source of truth for project progress. Every task, subtask, and decision lands here.
Check boxes off as work completes. If a task expands, add subsections inline — never in a separate doc.

---

## Phase 1 — Foundation

- [x] `git init`, initial commit, `.gitignore`
- [x] `pipeline/pyproject.toml` — `requires-python = ">=3.11"`, deps: `httpx`, `feedparser`, `tavily-python`, `openai` (OpenRouter), `jina` or raw httpx for Jina Reader
- [x] `pipeline/sources.json` — full sources list from PRD
- [x] `data/entries.json` — empty array `[]`
- [x] `data/weekly/` — empty directory (`.gitkeep`)
- [x] `weekly/` — empty directory for generated HTML (`.gitkeep`)
- [x] `.env.example` — `TAVILY_API_KEY=` and `OPENROUTER_API_KEY=`

---

## Phase 2 — Pipeline: Tier 1 (Structured APIs)

No LLM needed. Direct JSON parsing, filter by compound keywords.

- [x] `pipeline/run.py` — entrypoint: load sources, dispatch by tier, write `data/entries.json`
- [x] `pipeline/dedup.py` — `seen_urls.json` deduplication; SHA-256 id generation from title+doi+url
- [x] **PubMed** (`pipeline/sources/pubmed.py`)
  - [x] E-utilities search: `psilocybin OR MDMA OR LSD OR ketamine OR DMT OR ibogaine OR ayahuasca OR mescaline`
  - [x] Filter to clinical trials and research articles
  - [x] Map to schema fields
- [x] **ClinicalTrials.gov** (`pipeline/sources/clinicaltrials.py`)
  - [x] V2 API, filter by compound keywords in condition + intervention
  - [x] Map to schema: phase, status, institution, condition, sample_size
- [x] **Semantic Scholar** (`pipeline/sources/semantic_scholar.py`)
  - [x] Paper search API, compound keywords
  - [x] Map to schema
- [x] **bioRxiv/medRxiv** (`pipeline/sources/biorxiv.py`)
  - [x] `https://api.biorxiv.org/details/` endpoint
  - [x] Map to schema
- [x] **2026 backfill run** — 253 entries (200 PubMed, 28 Semantic Scholar, 25 ClinicalTrials). Semantic Scholar still occasionally 429; weekly cron will recover. ClinicalTrials fixed to use curl backend (httpx blocked by TLS fingerprint).

---

## Phase 3 — Pipeline: Tier 2 (RSS + Jina Reader + Mimo)

- [x] `pipeline/jina.py` — Jina Reader wrapper: `GET https://r.jina.ai/<url>` → full text (via subprocess curl)
- [x] `pipeline/mimo.py` — OpenRouter wrapper using `moonshotai/kimi-k2.6:free`; extract schema fields; prompt enforces extraction-only
- [x] **MAPS.org** (`pipeline/sources/maps.py`)
- [x] **Chacruna Institute** (`pipeline/sources/chacruna.py`)
- [x] **Lucid News** (`pipeline/sources/lucid_news.py`)
- [x] `pipeline/sources/rss_base.py` — shared RSS+Jina+Mimo fetch loop
- [x] Integration test: 7 new entries from 2-month window across 3 RSS sources

---

## Phase 4 — Pipeline: Tier 3 (Tavily + Jina + Mimo)

- [x] `pipeline/tavily_client.py` — Tavily search wrapper; returns URLs + snippets (named tavily_client.py to avoid shadowing installed tavily package)
- [x] `pipeline/sources/tavily_base.py` — shared Tavily+Jina+Mimo loop; filters PDFs/social/non-article URLs; global 4s/call rate limiter in mimo.py prevents 429s
- [x] **Psychedelic Alpha** — Tavily search `site:psychedelicalpha.com`, Jina + Mimo
- [x] **FDA Press Releases** — Tavily search `site:fda.gov psychedelic OR psilocybin OR MDMA`, Jina + Mimo
- [x] **Compass Pathways** — Tavily search `site:compasspathways.com`, Jina + Mimo
- [x] **Atai Life Sciences** — Tavily search `site:atai.life`, Jina + Mimo
- [x] **General News** — 4 broad Tavily queries from PRD, Jina + Mimo
- [x] Integration test: 278 total entries, 0 duplicate IDs/URLs across all tiers. FDA/Compass/Atai return 0 (substance DBs + PDFs filtered; content captured by PubMed Tier 1). Global 4s/call throttle prevents 429s.

---

## Phase 5 — Weekly Issue Generator

- [x] `pipeline/weekly.py` — generate weekly snapshot
  - [x] Identify new entries added since last Sunday
  - [x] Group by compound
  - [x] Compute stats: total entries, new this week, compounds represented
  - [x] Write `data/weekly/YYYY-WNN.json`
  - [x] Generate `weekly/YYYY-WNN.html` from JSON (no prose, structured changelog format per PRD)
- [x] Run generator on backfill data to produce at least one valid weekly issue — `data/weekly/2026-W23.json` + `weekly/2026-W23.html` (291 entries, 9 compounds). Bot-challenge filter added to tavily_base.py.

---

## Phase 6 — Site

**Style selection first.** Build 3 `index.html` variants, pick one, then build all pages.

- [x] **Style decision** — light cream bg, floating indole/naphthalene/benzene/pyridine ring SVGs, Syne 800 + Plus Jakarta Sans, violet accent #5b38d6. Iterated through A–H; H (light, molecular bg) chosen.
  - [x] `index-option-a.html` — clean academic
  - [x] `index-option-b.html` — dark modern
  - [x] `index-option-c.html` — warm editorial
  - [x] index-poc.html — D/E/F/G variants in switcher
  - [x] index-h.html — final chosen style (light + molecules)
  - [x] User picks style → H theme applied to all pages

- [x] **`style.css`** — single shared stylesheet (chosen style)
- [x] **`index.html`** — homepage with spotlight, featured entries w/ AI summaries, live feed
- [x] **`trials.html`** — full trials table
  - [x] Loads `data/entries.json`
  - [x] Filterable by: compound, type (vanilla JS)
  - [x] Sortable by clicking column headers
- [x] **`script.js`** — filtering + sorting logic inline in trials.html
- [x] **`weekly/index.html`** — list of all weekly issues
- [x] **`podcast.html`** — "Coming Soon" page with episode previews and email notify
- [x] **`about.html`** — methodology, tier descriptions, schema table, data sources

---

## Phase 7 — GitHub Actions + GitHub Pages

- [x] `.github/workflows/weekly.yml`
  - [x] Cron: `0 1 * * 1` (Sunday 8pm ET = Monday 1am UTC)
  - [x] Steps: checkout, uv sync, run pipeline, commit `data/` and `weekly/`, push
  - [x] GitHub Pages deploy step
- [x] Enable GitHub Pages in repo settings (source: GitHub Actions workflow)
- [x] Confirm first automated run produces valid output — pipeline + deploy passed on first manual trigger

---

## Phase 8 — Launch

- [x] **`README.md`** — description, pipeline overview, schema table, local run instructions
- [x] **`LICENSE`** — MIT
- [x] **Definition of Done audit** (from PRD):
  - [x] Pipeline runs, produces valid `data/entries.json` with 2026 backfill
  - [x] GitHub Pages site live, all pages present
  - [x] Trials table filters work
  - [x] At least one weekly issue HTML generated
  - [x] Podcast page shows "Coming Soon" cleanly
  - [x] GitHub Actions cron configured
  - [x] README complete
  - [x] PubMed + ClinicalTrials.gov scrapers reliable
  - [x] Tavily + Jina pipeline works for 2+ Tier 3 sources
- [x] Public repo, open source, MIT license confirmed

---

## Phase 9 — Post-Launch Maintenance

### Tier 2/3 revival (2026-07-22)
Tier 2/3 produced nothing for six weeks; three independent breakages stacked.

- [x] `weekly.yml` ran `run.py` with no `--tier` flag, silently defaulting to Tier 2 and never running Tier 3
- [x] Jina Reader began requiring an API key that was never provisioned — removed the dependency entirely in favour of Tavily `include_raw_content` and the RSS `content:encoded` field; deleted `pipeline/jina.py`
- [x] Mimo's model `moonshotai/kimi-k2.6:free` was discontinued — moved to `openai/gpt-oss-20b:free`, raising `max_tokens` 512 → 1500 (reasoning tokens share the budget and were starving the JSON payload)
- [x] Verified in production: run 29966525569 succeeded, 22 fresh summarized entries

### Homepage relevance and freshness (2026-07-22)
"Featured This Week" showed a 2004 trial and no summaries.

- [x] `pipeline/dates.py` — normalize every source date shape to ISO at ingest (RFC-2822, PubMed `2026 Jun 6` and seasonal `2026 Summer`, bare years)
- [x] Fix RSS dates sliced to 10 chars (`"Fri, 17 Ap"`); recover the 22 already stored
- [x] Tier 3 had no publication date at all — switch Tavily to `topic="news"` for `published_date` (which also activates its `days` window)
- [x] Rank featured/spotlight/feed on publication date, 180-day window, excluding future-dated planned trial starts
- [x] `pipeline/snippet.py` — capture abstracts at ingest (PubMed efetch, CT.gov BriefSummary, Semantic Scholar + bioRxiv already fetched and discarded theirs); cards fall back to abstract when no LLM summary exists
- [x] `pipeline/relevance.py` — gate Tier 1 at ingest; the queries match any field and LSD/DMT collide with lumpy skin disease, laparoscopic splenectomy, and disease-modifying therapy. Removed 1,653 off-topic records (42% of the corpus)
- [x] `pipeline/classify.py` — one compound detector replacing four copies, aware of spelled-out names, metabolites, and development codes; "other" fell 42% → 6%
- [x] Dedup keyed off `pipeline/seen_urls.json`, which the workflow never committed, so every run re-appended the back catalogue (4,257 rows = 1,110 studies). Derive the seen set from the committed corpus; delete the side-car file
- [x] Wire `weekly.generate()` into `run.py` and auto-generate `weekly/index.html` — weekly/ had been frozen at the single June issue
- [x] Unify the week key: `build.py` derived it from today, the generator from the issue's Sunday, so the homepage linked to a nonexistent issue on every day but Sunday
- [x] Home link in nav; spotlight restyled to the site palette

### Operations documentation (2026-07-22)
- [x] `pipeline/mimo.py` → `pipeline/llm.py`. It was named after the model it shipped with and outlived three of them (MiMo → Kimi K2.6 → gpt-oss-20b → gemini-2.5-flash-lite). Named for the layer now, so a future relevance judge lands in it without another rename. **Phase 3/4 entries above still say "Mimo" and "Jina" — that is the historical record of what was built then, not current architecture.**
- [x] Extraction moved off `:free`. The account is on paid credits, so free variants bought nothing and had already cost weeks of downtime when one was withdrawn. Measured on the live task: gemini-2.5-flash-lite matched quality at ~1s/call vs ~22s, in 500 max_tokens vs 1500. ~$0.01/run
- [x] Inter-call throttle 4s → 0.2s (the 4s spacing existed for the free tier's 20 req/min)
- [x] README rewritten: stack table, how to swap the LLM and the search provider, where secrets live locally vs CI, entry schema. It previously documented Jina Reader, which no longer exists

### LLM relevance screening (2026-07-22)
Resolves the ketamine scope question with per-entry verdicts instead of a hand-written rule.

- [x] `pipeline/judge.py` + `judge_relevance()` in `llm.py` — second-stage screen on what the pattern gate passes. Regex cannot separate "Ketamine for Treatment-Resistant Depression" from "Anaesthetic management of dogs"; both name a compound unambiguously
- [x] Verdicts stored on the entry (`relevance`: relevant, reason, model, revision, judged). Each entry is judged exactly once; the weekly run screens only what dedup flags as new. Changing `MODEL` or bumping `PROMPT_REVISION` re-screens, and only then
- [x] Failed calls leave an entry **unjudged, not rejected** — a provider outage cannot silently empty the site
- [x] Rejected entries stay in `data/entries.json` as an audit trail (so a re-fetch cannot resurrect them); site, weekly issues, and trials table all filter them out
- [x] Backfilled all 1,192 entries. Revision 1 was wrong in two ways, caught by auditing verdicts rather than trusting the pass rate: it read "Vet Brain" as veterinary and dropped **ibogaine for veterans with TBI**, and it dropped every chronic-pain trial (psilocybin for low back pain, MDMA for fibromyalgia) because the prompt conflated procedural pain with pain as a treatment target
- [x] Revision 2 scored 15/15 on those failures; re-judged the corpus. 792 pass, 400 screened out. Ketamine fell 41% → 25% of the corpus, psilocybin now 40%
- [x] Cost: ~$0.07 per full-corpus pass, well under $0.01/week ongoing

### Open
- [ ] Compass Pathways condition landing pages (e.g. "Post-traumatic stress disorder (PTSD)") still enter as entries. Low volume; the nav-page title filter does not catch them

---

## Future (Post-Launch)

Not in scope for v1. Do not build until launch criteria are met.

- [ ] Custom domain
- [ ] Resend newsletter integration
- [ ] Podcast audio generation
- [ ] YouTube episode embeds + transcripts on podcast page

---

*Kill criteria (from PRD): < 50 GitHub stars and < 1,000 monthly visits after 8 weeks → kill it.*
