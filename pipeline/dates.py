"""Publication-date normalization.

Sources report dates in mutually incompatible shapes: ISO from ClinicalTrials.gov,
RFC-2822 from RSS feeds, "2026 Jun 6" from PubMed, and bare years from Semantic
Scholar. Everything is normalized to ISO YYYY-MM-DD at ingest so the site can rank
by *publication* date rather than ingest date.

Partial dates anchor to the earliest day they cover ("2014-01" -> 2014-01-01), so a
year-only record never outranks a fully-dated one from the same period.
"""

import re
from datetime import date

_MONTHS = {
    m: i
    for i, m in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun",
         "jul", "aug", "sep", "oct", "nov", "dec"],
        start=1,
    )
}

# PubMed publishes quarterly journals with a season instead of a month.
_SEASONS = {"spring": 4, "summer": 7, "fall": 10, "autumn": 10, "winter": 1}

_ISO_DAY = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_ISO_MONTH = re.compile(r"(\d{4})-(\d{2})$")
_YEAR_SEASON = re.compile(r"(\d{4})\s+([A-Za-z]{4,})")
_YEAR_MONTH_DAY = re.compile(r"(\d{4})\s+([A-Za-z]{3})[a-z]*(?:\s+(\d{1,2}))?")
_RFC2822 = re.compile(r"(\d{1,2})\s+([A-Za-z]{3})[a-z]*\s+(\d{4})")
_YEAR = re.compile(r"^(\d{4})$")


def _build(year: int, month: int, day: int) -> date | None:
    """Construct a date, clamping out-of-range components rather than raising."""
    if not 1900 <= year <= 2100:
        return None
    month = min(max(month, 1), 12)
    day = min(max(day, 1), 31)
    while day > 1:
        try:
            return date(year, month, day)
        except ValueError:
            day -= 1
    try:
        return date(year, month, 1)
    except ValueError:
        return None


def parse(raw: str | None) -> date | None:
    """Best-effort parse of any source date string. None when unparseable."""
    if not raw:
        return None
    s = raw.strip()

    if m := _ISO_DAY.match(s):
        return _build(int(m[1]), int(m[2]), int(m[3]))
    if m := _ISO_MONTH.match(s):
        return _build(int(m[1]), int(m[2]), 1)
    # PubMed quarterly: "2026 Summer". Matched by prefix so historical records
    # truncated mid-word ("2026 Summe") still resolve; four characters is enough to
    # separate the seasons from any month name.
    if m := _YEAR_SEASON.match(s):
        word = m[2].lower()
        for name, month in _SEASONS.items():
            if name.startswith(word):
                return _build(int(m[1]), month, 1)
    # PubMed: "2026 Jun 6", "2026 Jun", "2026 Jan-Dec"
    if m := _YEAR_MONTH_DAY.match(s):
        month = _MONTHS.get(m[2].lower())
        if month:
            return _build(int(m[1]), month, int(m[3]) if m[3] else 1)
    # RSS: "Fri, 17 Apr 2026 10:00:00 +0000"
    if m := _RFC2822.search(s):
        month = _MONTHS.get(m[2].lower())
        if month:
            return _build(int(m[3]), month, int(m[1]))
    if m := _YEAR.match(s):
        return _build(int(m[1]), 1, 1)
    return None


def to_iso(raw: str | None) -> str | None:
    """Normalize any source date string to ISO YYYY-MM-DD. None when unparseable."""
    parsed = parse(raw)
    return parsed.isoformat() if parsed else None
