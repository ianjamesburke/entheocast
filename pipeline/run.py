import json
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

DATA_PATH = Path(__file__).parent.parent / "data" / "entries.json"


def load_existing() -> list[dict]:
    if DATA_PATH.exists():
        return json.loads(DATA_PATH.read_text())
    return []


def save_entries(entries: list[dict]) -> None:
    DATA_PATH.write_text(json.dumps(entries, indent=2))


def run_tier1(start_date: str | None = None) -> list[dict]:
    from sources.pubmed import fetch as pubmed_fetch
    from sources.clinicaltrials import fetch as ct_fetch
    from sources.semantic_scholar import fetch as ss_fetch
    from sources.biorxiv import fetch as biorxiv_fetch
    from dedup import filter_new
    from concurrent.futures import ThreadPoolExecutor, as_completed

    year = int(start_date[:4]) if start_date else None

    tasks = {
        "PubMed": lambda: pubmed_fetch(min_date=start_date),
        "ClinicalTrials.gov": lambda: ct_fetch(min_date=start_date),
        "Semantic Scholar": lambda: ss_fetch(min_year=year),
        "bioRxiv/medRxiv": lambda: biorxiv_fetch(start_date=start_date),
    }

    results: dict[str, list[dict]] = {}
    print("Fetching all Tier 1 sources in parallel...")
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fn): name for name, fn in tasks.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
                print(f"  {name}: {len(results[name])} entries fetched")
            except Exception as e:
                print(f"  {name} error: {e}", file=sys.stderr)
                results[name] = []

    all_new = []
    for name in tasks:
        new = filter_new(results.get(name, []))
        print(f"  {name}: {len(new)} new after dedup")
        all_new.extend(new)

    return all_new


def run_tier2(start_date: str | None = None) -> list[dict]:
    from sources.maps import fetch as maps_fetch
    from sources.chacruna import fetch as chacruna_fetch
    from sources.lucid_news import fetch as lucid_fetch
    from dedup import filter_new
    from concurrent.futures import ThreadPoolExecutor, as_completed

    tasks = {
        "MAPS.org": lambda: maps_fetch(min_date=start_date),
        "Chacruna Institute": lambda: chacruna_fetch(min_date=start_date),
        "Lucid News": lambda: lucid_fetch(min_date=start_date),
    }

    results: dict[str, list[dict]] = {}
    print("Fetching all Tier 2 sources in parallel...")
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(fn): name for name, fn in tasks.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
                print(f"  {name}: {len(results[name])} entries fetched")
            except Exception as e:
                print(f"  {name} error: {e}", file=sys.stderr)
                results[name] = []

    all_new = []
    for name in tasks:
        new = filter_new(results.get(name, []))
        print(f"  {name}: {len(new)} new after dedup")
        all_new.extend(new)

    return all_new


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Entheocast pipeline")
    parser.add_argument("--since", help="Start date YYYY-MM-DD (backfill)")
    parser.add_argument("--tier", type=int, default=2, help="Max tier to run (1, 2, or 3)")
    args = parser.parse_args()

    existing = load_existing()
    print(f"Existing entries: {len(existing)}")

    new_entries: list[dict] = []
    new_entries.extend(run_tier1(start_date=args.since))

    if args.tier >= 2:
        new_entries.extend(run_tier2(start_date=args.since))

    all_entries = existing + new_entries
    save_entries(all_entries)
    print(f"\nTotal entries: {len(all_entries)} (+{len(new_entries)} new)")


if __name__ == "__main__":
    main()
