"""LLM calls for the pipeline, via OpenRouter.

Named for the layer rather than the model: this module was previously called
mimo.py after the model it launched with, and outlived three of them.

Uses the OpenAI SDK pointed at OpenRouter's base URL, so switching models means
changing MODEL and nothing else.
"""

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

SCHEMA_PROMPT = """Extract structured data from this article. Return a single JSON
object — not an array, and not an object wrapping one. Use exactly these fields:
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

RELEVANCE_PROMPT = """You screen entries for a psychedelic research tracker. It covers
psychedelic and dissociative compounds given as a THERAPEUTIC or investigational
treatment in humans, plus the regulation, policy, and industry news around them.

Return a single JSON object: {"relevant": true|false, "reason": "<10 words"}

relevant=true for:
- psychiatric indications: depression, PTSD, anxiety, addiction, OCD, eating
  disorders, end-of-life and existential distress
- CHRONIC pain as a treatment target: cluster headache, migraine, fibromyalgia,
  chronic back pain, neuropathic pain, phantom limb pain
- human studies in patients or healthy volunteers: mechanism of action,
  neuroimaging, phenomenology, dose-finding, pharmacokinetics, safety/tolerability
- naturalistic, survey, and observational studies of human psychedelic use
- regulatory decisions, policy, legal status, industry and company news
- reviews and meta-analyses of any of the above

relevant=false for:
- the compound used as an ANESTHETIC or SEDATIVE: general anesthesia, procedural
  sedation, post-operative or intra-operative analgesia, ICU sedation. This is
  the main thing to exclude, and it is overwhelmingly ketamine and esketamine
- veterinary medicine: the patients are animals (dogs, cattle, wildlife)
- purely preclinical work in animals or cell culture, with no human arm
- analytical chemistry, assay development, and forensic detection methods
- toxicology, poisoning, and overdose case reports
- papers whose actual subject is a different drug class entirely
  (methamphetamine, antipsychotics, MS disease-modifying therapy)
- fungal taxonomy, biosynthesis, and chemical ecology

Read carefully before deciding:
- "Vet" and "Veteran" mean military veterans — a human population, relevant.
  Only "veterinary" means animals.
- Treating chronic pain WITH a psychedelic is relevant. Using ketamine for
  surgical or procedural pain is not. The distinction is whether the compound is
  the therapy under study or an anesthetic adjunct.

The compound is already confirmed present. Judge only whether the CONTEXT fits
the scope above. When genuinely ambiguous, answer true."""


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


def _as_entry(parsed: object, url: str) -> dict | None:
    """Coerce a parsed response to a single record, or None.

    Models are inconsistent about wrapping: a one-element array carries the same
    answer and is unwrapped. Anything else — a multi-element array, a bare string —
    means the model misread the task, and passing it on would surface as an
    AttributeError deep in a source module rather than here.
    """
    if isinstance(parsed, list):
        if len(parsed) == 1 and isinstance(parsed[0], dict):
            return parsed[0]
        print(f"LLM returned a {len(parsed)}-element array for {url}; discarding")
        return None
    if not isinstance(parsed, dict):
        print(f"LLM returned {type(parsed).__name__}, expected object, for {url}")
        return None
    return parsed


def extract(article_text: str, url: str) -> dict | None:
    """Extract schema fields from article text. None if the model returns unusable JSON."""
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
        return _as_entry(json.loads(raw.strip()), url)
    except json.JSONDecodeError as e:
        print(f"LLM JSON parse error ({MODEL}) for {url}: {e}")
        return None
    except Exception as e:
        print(f"LLM extraction error ({MODEL}) for {url}: {e}")
        return None


def judge_relevance(title: str, context: str = "") -> dict | None:
    """Decide whether an entry is psychedelic research as this tracker scopes it.

    Returns {"relevant": bool, "reason": str}, or None if the call failed — callers
    must treat None as "unknown" and leave the entry unjudged, never as "irrelevant".
    Regex cannot make this call: "Ketamine for Treatment-Resistant Depression" and
    "Anaesthetic management of dogs" both name a compound unambiguously.
    """
    prompt = f"{title}\n\n{context[:1500]}" if context else title
    _throttle()
    try:
        resp = _get_client().chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": RELEVANCE_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=200,
        )
        raw = (resp.choices[0].message.content or "").strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = _as_entry(json.loads(raw.strip()), title)
        if not parsed or not isinstance(parsed.get("relevant"), bool):
            print(f"LLM relevance verdict malformed for {title[:60]!r}")
            return None
        return {"relevant": parsed["relevant"], "reason": str(parsed.get("reason", ""))[:120]}
    except json.JSONDecodeError as e:
        print(f"LLM relevance parse error for {title[:60]!r}: {e}")
        return None
    except Exception as e:
        print(f"LLM relevance error for {title[:60]!r}: {e}")
        return None
