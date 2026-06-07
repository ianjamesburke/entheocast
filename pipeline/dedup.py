import hashlib
import json
from pathlib import Path

SEEN_PATH = Path(__file__).parent / "seen_urls.json"


def _load_seen() -> set[str]:
    if SEEN_PATH.exists():
        return set(json.loads(SEEN_PATH.read_text()))
    return set()


def _save_seen(seen: set[str]) -> None:
    SEEN_PATH.write_text(json.dumps(sorted(seen), indent=2))


def make_id(title: str, doi: str | None, url: str) -> str:
    key = f"{title}|{doi or ''}|{url}"
    return hashlib.sha256(key.encode()).hexdigest()


def filter_new(entries: list[dict]) -> list[dict]:
    seen = _load_seen()
    new_entries = []
    for entry in entries:
        if entry["id"] not in seen:
            new_entries.append(entry)
            seen.add(entry["id"])
    _save_seen(seen)
    return new_entries
