# Entheocast

Psychedelic clinical trials, regulatory updates, and research — aggregated weekly into a structured open dataset. Live at [ianjamesburke.github.io/entheocast](https://ianjamesburke.github.io/entheocast).

Updated every Sunday night via GitHub Actions. No editorial prose — raw structured data from primary sources.

## Data Sources

- **PubMed** — clinical research and peer-reviewed papers
- **ClinicalTrials.gov** — active trial registrations
- **Semantic Scholar** — academic papers
- **bioRxiv / medRxiv** — preprints
- **MAPS, Chacruna, Lucid News** — RSS feeds via Jina Reader + LLM extraction
- **Psychedelic Alpha, FDA, General News** — Tavily search + Jina Reader + LLM extraction

## Schema

`data/entries.json` is an array of objects:

| Field | Type | Description |
|---|---|---|
| `id` | string | SHA-256 of title+doi+url |
| `title` | string | Article or trial title |
| `url` | string | Canonical source URL |
| `compound` | string | `psilocybin`, `mdma`, `ketamine`, `lsd`, `dmt`, `ibogaine`, `ayahuasca`, `mescaline`, `other` |
| `type` | string | `phase_1`, `phase_2`, `phase_3`, `observational`, `meta_analysis`, `regulatory`, `news`, `preprint` |
| `date` | string | ISO 8601 publication date |
| `institution` | string | Lead institution or journal |
| `condition` | string | Medical condition studied |
| `sample_size` | integer | Participant count (trials) |
| `status` | string | `active`, `recruiting`, `completed`, `published` |
| `source` | string | Data source identifier |
| `added_date` | string | ISO 8601 date added to dataset |

## Local Run

```bash
cp .env.example .env
# fill in TAVILY_API_KEY and OPENROUTER_API_KEY

cd pipeline
uv sync
uv run python run.py
```

Writes updated `data/entries.json` and generates `data/weekly/YYYY-WNN.json` + `weekly/YYYY-WNN.html`.

## License

MIT
