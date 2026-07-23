"""Entry identity and deduplication.

The set of already-known entries is derived from data/entries.json — the committed,
authoritative corpus — rather than a side-car state file. A separate seen-ids file
desynchronizes the moment anything writes one without the other, which is exactly
what happened in CI: the workflow committed data/ but not the state file, so every
weekly run rediscovered the entire back catalogue and appended it again.
"""

import hashlib


def make_id(title: str, doi: str | None, url: str) -> str:
    key = f"{title}|{doi or ''}|{url}"
    return hashlib.sha256(key.encode()).hexdigest()


def seen_ids(existing: list[dict]) -> set[str]:
    """Ids already present in the corpus."""
    return {e["id"] for e in existing if e.get("id")}


def filter_new(entries: list[dict], seen: set[str]) -> list[dict]:
    """Entries not already known. `seen` is updated in place, so passing the same set
    across sources also collapses duplicates found by two sources in one run."""
    new_entries = []
    for entry in entries:
        if entry["id"] in seen:
            continue
        new_entries.append(entry)
        seen.add(entry["id"])
    return new_entries
