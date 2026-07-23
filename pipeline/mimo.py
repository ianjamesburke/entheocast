import json
import os
import threading
import time
from openai import OpenAI

# Swap the extraction model here. Any OpenRouter model id works; see README
# "Operations" for how to pick one and what it costs.
MODEL = "google/gemini-2.5-flash-lite"

# Enough for the JSON payload. Reasoning models spend this budget on hidden
# reasoning tokens before emitting content and need several times more.
MAX_TOKENS = 500

_client: OpenAI | None = None
_rate_lock = threading.Lock()
_last_call_time = 0.0
# A guard against runaway loops, not a tier limit: the account is on paid credits,
# so the old 4s spacing (built for the free tier's 20 requests/min) only made runs
# slow. Raise this if a provider starts returning 429s.
_MIN_INTERVAL = 0.2

SCHEMA_PROMPT = """Extract structured data from this article. Return JSON with exactly these fields:
- title: string (article title)
- compound: string (one of: psilocybin, mdma, lsd, ketamine, dmt, ibogaine, ayahuasca, mescaline, other)
- type: string (one of: phase_1, phase_2, phase_3, observational, meta_analysis, regulatory, news)
- institution: string or null (lead institution/sponsor)
- condition: string (one of: depression, PTSD, anxiety, addiction, OCD, eating_disorder, cluster_headache, other)
- sample_size: integer or null
- status: string (one of: recruiting, active, completed, published, approved, other)
- outcome_summary: string or null (1-2 sentence factual summary of results/status; null if no outcomes reported)
- doi: string or null

Rules: extraction only, no editorializing. If a field is unclear, use null or "other"."""


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url="https://openrouter.ai/api/v1",
        )
    return _client


def _throttle() -> None:
    global _last_call_time
    with _rate_lock:
        now = time.monotonic()
        wait = _MIN_INTERVAL - (now - _last_call_time)
        if wait > 0:
            time.sleep(wait)
        _last_call_time = time.monotonic()


def extract(article_text: str, url: str) -> dict | None:
    """Extract schema fields from article text via Mimo on OpenRouter."""
    truncated = article_text[:4000]
    _throttle()
    try:
        resp = _get_client().chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SCHEMA_PROMPT},
                {"role": "user", "content": f"URL: {url}\n\n{truncated}"},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=MAX_TOKENS,
        )
        raw = resp.choices[0].message.content or ""
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except json.JSONDecodeError as e:
        print(f"Mimo JSON parse error for {url}: {e}")
        return None
    except Exception as e:
        print(f"Mimo extraction error for {url}: {e}")
        return None
