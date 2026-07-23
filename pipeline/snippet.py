"""Abstract condensation.

entries.json is fetched in full by the browser on every page load, so verbatim
abstracts cannot be stored — 4,000 entries of ~1,500 characters would add several
megabytes to the critical path. Abstracts are cut to the first couple of sentences,
which is where trial abstracts state their design and finding.
"""

import re

MAX_CHARS = 300

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
# Leading section labels from structured abstracts ("BACKGROUND: ", "Methods - ").
_LEADING_LABEL = re.compile(
    r"^(background|objectives?|aims?|introduction|purpose|methods?|importance)"
    r"\s*[:\-–]\s*",
    re.IGNORECASE,
)


def condense(text: str | None, max_chars: int = MAX_CHARS) -> str | None:
    """First whole sentences of an abstract, up to max_chars. None if empty."""
    if not text:
        return None
    cleaned = _LEADING_LABEL.sub("", " ".join(text.split())).strip()
    if not cleaned:
        return None
    if len(cleaned) <= max_chars:
        return cleaned

    out = ""
    for sentence in _SENTENCE_END.split(cleaned):
        candidate = f"{out} {sentence}".strip()
        if out and len(candidate) > max_chars:
            break
        out = candidate
    if not out:
        # A single sentence longer than the budget: cut on a word boundary.
        out = cleaned[:max_chars].rsplit(" ", 1)[0]
    return out.rstrip(" ,;:") + "…" if len(out) < len(cleaned) else out
