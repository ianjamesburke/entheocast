import json
import os
import threading
import time
from openai import OpenAI

_client: OpenAI | None = None
_rate_lock = threading.Lock()
_last_call_time = 0.0
_MIN_INTERVAL = 4.0  # 15 calls/min — safely under free tier 20/min limit

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
            model="openai/gpt-oss-20b:free",
            messages=[
                {"role": "system", "content": SCHEMA_PROMPT},
                {"role": "user", "content": f"URL: {url}\n\n{truncated}"},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            # gpt-oss-20b is a reasoning model: reasoning tokens count toward this
            # budget, so it needs headroom above the JSON payload or content comes
            # back empty/truncated.
            max_tokens=1500,
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
