"""
Build a manually-verifiable ground-truth dataset for FACTSHIELD.

Runs the extraction + comparison pipeline on releases 001–003 and outputs
a JSONL file where each line is a fact-pair that can be reviewed (accept/reject).

Usage:
    python data/build_verified_dataset.py              # generate candidates
    python data/build_verified_dataset.py --verify     # interactive CLI review
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure project root is importable
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.source_extraction import extract_canonical_facts
from core.entity_matching import load_aliases_db
from core.location_matching import load_location_aliases
from core.comparison import compare_versions

# Force UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_RELEASES_DIR = _ROOT / "data" / "sample_releases"
_OUTPUT_FILE = _ROOT / "data" / "verified_dataset.jsonl"

_RELEASE_FACTS = {
    "release_001": {
        "names": ["Brigadier Aditya Kumar Nair", "Dr. Priya Suresh Mehta"],
        "dates": ["15 September 2026"],
        "numbers": ["250", "120", "3"],
        "locations": ["Pune", "Satara", "Nashik"],
    },
    "release_002": {
        "names": ["Colonel Meera Shankar Singh", "General Rajesh Kumar Verma"],
        "dates": ["10 March 2026", "14 March 2026"],
        "numbers": ["180", "12", "5"],
        "locations": ["Nashik", "Ahmednagar", "Pune"],
    },
    "release_003": {
        "names": ["Dr. Priya Suresh Mehta", "Lieutenant General Arjun Suresh Rao"],
        "dates": ["20 July 2026"],
        "numbers": ["300", "8", "450"],
        "locations": ["Kolhapur", "Sangli", "Solapur", "Satara"],
    },
}


def _load_release(name: str) -> dict[str, str]:
    d = _RELEASES_DIR / name
    return {
        "English": (d / "english.txt").read_text(encoding="utf-8"),
        "Hindi":   (d / "hindi.txt").read_text(encoding="utf-8"),
        "Marathi": (d / "marathi.txt").read_text(encoding="utf-8"),
    }


def generate_candidates() -> list[dict]:
    """Generate candidate fact-pairs for all configured releases."""
    aliases_db = load_aliases_db()
    loc_aliases = load_location_aliases()
    candidates = []
    fact_counter = 0

    for release_name, canon in sorted(_RELEASE_FACTS.items()):
        versions = _load_release(release_name)
        facts = extract_canonical_facts(versions["English"], aliases_db, loc_aliases)

        # Run the QC engine to determine detection status
        result = compare_versions(
            versions=versions,
            canonical_names=canon["names"],
            canonical_dates=canon["dates"],
            canonical_numbers=canon["numbers"],
            canonical_locations=canon.get("locations", []),
        )

        # Build per-fact records
        for fact in facts["all"]:
            fact_counter += 1
            # Check if any finding references this fact
            finding_for_fact = next(
                (f for f in result.findings if f.expected == fact.canonical_value),
                None,
            )

            candidates.append({
                "id": f"GV_{fact_counter:03d}",
                "release": release_name,
                "fact_id": fact.fact_id,
                "type": fact.type,
                "canonical_value": fact.canonical_value,
                "source_text": fact.source_text,
                "criticality": fact.criticality,
                "opsec_tags": fact.opsec_tags,
                "hindi_detected": finding_for_fact is None,  # True = consistent
                "marathi_detected": finding_for_fact is None,
                "finding_detail": finding_for_fact.detail if finding_for_fact else "Consistent across all versions",
                "verified_by": "",
                "status": "PENDING",
                "notes": "",
            })

    return candidates


def write_candidates(candidates: list[dict]) -> None:
    """Write candidate dataset to JSONL."""
    with open(_OUTPUT_FILE, "w", encoding="utf-8") as f:
        for c in candidates:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"\n  Written {len(candidates)} candidates to {_OUTPUT_FILE}")


def interactive_verify() -> None:
    """Interactive CLI for accept/reject review of dataset entries."""
    if not _OUTPUT_FILE.exists():
        print("No dataset file found. Run without --verify first.")
        return

    entries = []
    with open(_OUTPUT_FILE, encoding="utf-8") as f:
        for line in f:
            entries.append(json.loads(line))

    pending = [e for e in entries if e["status"] == "PENDING"]
    print(f"\n  {len(pending)} entries pending review out of {len(entries)} total.\n")

    for i, entry in enumerate(pending):
        print(f"  [{i+1}/{len(pending)}] {entry['release']} / {entry['fact_id']}")
        print(f"    Type      : {entry['type']}")
        print(f"    Value     : {entry['canonical_value']}")
        print(f"    Source    : {entry['source_text']}")
        print(f"    Criticality: {entry['criticality']}")
        print(f"    Finding   : {entry['finding_detail']}")
        print()

        while True:
            choice = input("    [a]ccept / [r]eject / [s]kip / [q]uit: ").strip().lower()
            if choice in ("a", "r", "s", "q"):
                break

        if choice == "q":
            break
        elif choice == "a":
            entry["status"] = "VERIFIED"
            entry["verified_by"] = "manual"
        elif choice == "r":
            entry["status"] = "REJECTED"
            entry["verified_by"] = "manual"
            entry["notes"] = input("    Reason: ").strip()
        # "s" leaves it PENDING

    # Rewrite
    with open(_OUTPUT_FILE, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    verified = sum(1 for e in entries if e["status"] == "VERIFIED")
    rejected = sum(1 for e in entries if e["status"] == "REJECTED")
    pending = sum(1 for e in entries if e["status"] == "PENDING")
    print(f"\n  Done: {verified} verified, {rejected} rejected, {pending} pending.\n")


if __name__ == "__main__":
    if "--verify" in sys.argv:
        interactive_verify()
    else:
        candidates = generate_candidates()
        write_candidates(candidates)
        print("  To review interactively, run: python data/build_verified_dataset.py --verify")
