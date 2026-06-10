# Entheocast

Psychedelic clinical trials, regulatory updates, and research aggregated weekly into a structured open dataset. Live at [ianjamesburke.github.io/entheocast](https://ianjamesburke.github.io/entheocast).

GitHub Actions runs the pipeline every Sunday night. Data, not commentary.

## Sources

- PubMed
- ClinicalTrials.gov
- Semantic Scholar
- bioRxiv / medRxiv
- MAPS, Chacruna, Lucid News (RSS + Jina Reader)
- Psychedelic Alpha, FDA, general news (Tavily search + Jina Reader)

## Run locally

```bash
cp .env.example .env
# add TAVILY_API_KEY and OPENROUTER_API_KEY

cd pipeline && uv sync && uv run python run.py
```

Writes `data/entries.json` and generates `data/weekly/YYYY-WNN.json` + `weekly/YYYY-WNN.html`.

MIT
