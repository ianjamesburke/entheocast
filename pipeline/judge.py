"""LLM relevance screening — the second stage of a two-stage filter.

relevance.py removes lexical false positives (LSD the veterinary poxvirus, DMT the
multiple-sclerosis therapy) for free and deterministically. What it cannot do is
judge context: "Ketamine for Treatment-Resistant Depression" and "Anaesthetic
management of dogs" both name a compound unambiguously, and only one belongs here.

Verdicts are stored on the entry, so an entry is judged exactly once and never
re-billed. Re-judging happens only when the model or prompt version changes.

Backfill everything unjudged:   uv run python judge.py
Preview without spending:       uv run python judge.py --dry-run
Re-judge under a new prompt:    uv run python judge.py --revision 2
"""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import llm

REPO_ROOT = Path(__file__).parent.parent
ENTRIES_PATH = REPO_ROOT / "data" / "entries.json"

# Bump when RELEVANCE_PROMPT changes meaningfully; entries judged under an older
# revision are then re-screened, and only those.
PROMPT_REVISION = 2

# The judge is IO-bound. llm._MIN_INTERVAL still serializes the actual calls, so
# this only keeps that pipe full.
MAX_WORKERS = 8


def needs_judging(entry: dict, revision: int = PROMPT_REVISION) -> bool:
    """True when this entry has no verdict from the current model and prompt."""
    verdict = entry.get("relevance")
    if not isinstance(verdict, dict):
        return True
    return verdict.get("revision") != revision or verdict.get("model") != llm.MODEL


def judge_entry(entry: dict, revision: int = PROMPT_REVISION) -> bool:
    """Attach a verdict to one entry. Returns False if the call failed.

    A failed call leaves the entry unjudged rather than marking it irrelevant, so a
    provider outage can never silently empty the site. The next run retries it.
    """
    context = entry.get("outcome_summary") or entry.get("abstract") or ""
    result = llm.judge_relevance(entry.get("title") or "", context)
    if result is None:
        return False
    entry["relevance"] = {
        "relevant": result["relevant"],
        "reason": result["reason"],
        "model": llm.MODEL,
        "revision": revision,
        "judged": str(date.today()),
    }
    return True


def judge_all(entries: list[dict], revision: int = PROMPT_REVISION) -> dict:
    """Judge every entry lacking a current verdict. Mutates entries in place."""
    pending = [e for e in entries if needs_judging(e, revision)]
    if not pending:
        print("Relevance: nothing to judge, every entry already has a current verdict")
        return {"judged": 0, "failed": 0, "irrelevant": 0}

    print(f"Relevance: judging {len(pending)} of {len(entries)} entries ({llm.MODEL})", flush=True)
    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for i, ok in enumerate(pool.map(lambda e: judge_entry(e, revision), pending), 1):
            results.append(ok)
            if i % 100 == 0 or i == len(pending):
                print(f"  {i}/{len(pending)} judged", flush=True)

    judged = sum(results)
    failed = len(results) - judged
    irrelevant = sum(
        1 for e in pending
        if isinstance(e.get("relevance"), dict) and not e["relevance"]["relevant"]
    )
    print(f"Relevance: {judged} judged, {failed} failed, {irrelevant} marked irrelevant")
    return {"judged": judged, "failed": failed, "irrelevant": irrelevant}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="LLM relevance screening")
    parser.add_argument("--dry-run", action="store_true",
                        help="report how many entries would be judged, then exit")
    parser.add_argument("--revision", type=int, default=PROMPT_REVISION,
                        help="prompt revision to judge against")
    args = parser.parse_args()

    entries = json.loads(ENTRIES_PATH.read_text())
    pending = [e for e in entries if needs_judging(e, args.revision)]

    if args.dry_run:
        print(f"{len(pending)} of {len(entries)} entries would be judged at revision {args.revision}")
        return

    judge_all(entries, args.revision)
    ENTRIES_PATH.write_text(json.dumps(entries, indent=2))
    print(f"Wrote {ENTRIES_PATH}")

    kept = sum(1 for e in entries if e.get("relevance", {}).get("relevant") is not False)
    print(f"{kept} of {len(entries)} entries pass relevance")


if __name__ == "__main__":
    main()
