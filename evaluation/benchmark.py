"""
Benchmark runner for the Multilingual QC system.

Generates 40 seeded errors from a release, runs the QC engine on each,
calculates catch rate, and exports CSV + JSON reports.

Usage
-----
    python -m evaluation.benchmark
    python -m evaluation.benchmark --release release_001 --output reports/
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# -- Ensure project root is importable ------------------------------------
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.comparison import compare_versions
from core.entity_matching import load_aliases_db
from core.location_matching import load_location_aliases
from core.rules import load_settings
from evaluation.metrics import calculate_metrics
from evaluation.seed_generator import generate_seed_cases

logger = logging.getLogger(__name__)

# Force UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# -- Default canonical facts per release -----------------------------------

_RELEASE_FACTS: dict[str, dict] = {
    "release_001": {
        "names":     ["Brigadier Aditya Kumar Nair", "Dr. Priya Suresh Mehta"],
        "dates":     ["15 September 2026"],
        "numbers":   ["250", "120", "3"],
        "locations": ["Pune", "Satara", "Nashik"],
    },
    "release_002": {
        "names":     ["Colonel Meera Shankar Singh", "General Rajesh Kumar Verma"],
        "dates":     ["10 March 2026", "14 March 2026"],
        "numbers":   ["180", "12", "5"],
        "locations": ["Nashik", "Ahmednagar", "Pune"],
    },
    "release_003": {
        "names":     ["Dr. Priya Suresh Mehta", "Lieutenant General Arjun Suresh Rao"],
        "dates":     ["20 July 2026"],
        "numbers":   ["300", "8", "450"],
        "locations": ["Kolhapur", "Sangli", "Solapur", "Satara"],
    },
    "release_004": {
        "names":     ["Colonel Meera Shankar Singh"],
        "dates":     ["15 August 2026"],
        "numbers":   ["75", "7", "300"],
        "locations": [],
    },
    "release_005": {
        "names":     ["Lieutenant General Arjun Suresh Rao"],
        "dates":     ["26 November 2026"],
        "numbers":   ["200", "4", "8", "12", "2", "15"],
        "locations": [],
    },
}


def load_sample_release(release_name: str) -> dict[str, str]:
    """Load English / Hindi / Marathi texts from *data/sample_releases/*."""
    base = _ROOT / "data" / "sample_releases" / release_name
    result: dict[str, str] = {}
    for lang, fname in [("English", "english.txt"), ("Hindi", "hindi.txt"), ("Marathi", "marathi.txt")]:
        p = base / fname
        if not p.exists():
            raise FileNotFoundError(f"Missing sample file: {p}")
        result[lang] = p.read_text(encoding="utf-8")
    return result


def run_benchmark(
    release_name: str = "release_001",
    canonical_names: list[str] | None = None,
    canonical_dates: list[str] | None = None,
    canonical_numbers: list[str] | None = None,
    canonical_locations: list[str] | None = None,
    output_dir: Path | None = None,
) -> dict:
    """
    Execute the full benchmark pipeline and return a summary dict.

    Steps
    -----
    1. Load clean release.
    2. Generate 40 seeded error cases.
    3. Run QC engine on each.
    4. Determine whether each error was caught.
    5. Calculate metrics.
    6. Export CSV + JSON reports.
    """
    facts = _RELEASE_FACTS.get(release_name, _RELEASE_FACTS["release_001"])
    if canonical_names     is None: canonical_names     = facts["names"]
    if canonical_dates     is None: canonical_dates     = facts["dates"]
    if canonical_numbers   is None: canonical_numbers   = facts["numbers"]
    if canonical_locations is None: canonical_locations  = facts.get("locations", [])

    output_dir = output_dir or (_ROOT / "reports")
    output_dir.mkdir(exist_ok=True, parents=True)

    settings        = load_settings()
    aliases_db      = load_aliases_db()
    location_aliases = load_location_aliases()

    _banner("MULTILINGUAL QC BENCHMARK")
    print(f"  Release   : {release_name}")
    print(f"  Names     : {', '.join(canonical_names)}")
    print(f"  Dates     : {', '.join(canonical_dates)}")
    print(f"  Numbers   : {', '.join(canonical_numbers)}")
    print(f"  Locations : {', '.join(canonical_locations)}")
    _banner()

    base_versions = load_sample_release(release_name)
    seed_cases = generate_seed_cases(
        base_versions, canonical_numbers, canonical_dates,
        canonical_names, canonical_locations,
    )
    print(f"\n  Generated {len(seed_cases)} seeded test cases\n" + "-" * 60)

    details: list[dict] = []
    for case in seed_cases:
        result = compare_versions(
            versions=case.versions,
            canonical_names=canonical_names,
            canonical_dates=canonical_dates,
            canonical_numbers=canonical_numbers,
            canonical_locations=canonical_locations,
            aliases_db=aliases_db,
            location_aliases=location_aliases,
            settings=settings,
        )
        was_caught = any(
            f.language == case.language_affected and f.fact_type == case.fact_type
            for f in result.findings
        )
        status_sym = "PASS" if was_caught == case.expected_detection else "FAIL"
        label      = "CAUGHT" if was_caught else "MISSED"
        print(f"  [{status_sym}] {label:6s}: {case.id}: {case.description}")

        details.append({
            "ID":                 case.id,
            "Category":           case.category,
            "Language Affected":  case.language_affected,
            "Description":        case.description,
            "Expected Value":     case.expected_value,
            "Expected Detection": case.expected_detection,
            "Was Caught":         was_caught,
            "Result":             "PASS" if was_caught == case.expected_detection else "FAIL",
        })

    metrics = calculate_metrics(details)

    _banner("RESULTS SUMMARY")
    print(f"  Total seeded errors : {metrics['total']}")
    print(f"  Caught              : {metrics['caught']}")
    print(f"  Missed              : {metrics['missed']}")
    print(f"  Catch Rate          : {metrics['catch_rate']:.2f}%")
    print()
    print("  By category:")
    for cat, cm in metrics["by_category"].items():
        print(f"    {cat.capitalize():10s}: {cm['caught']}/{cm['total']}"
              f"  ->  {cm['catch_rate']:.1f}%")
    print()
    print(f"  Precision   : {metrics['precision']}%")
    print(f"  Recall      : {metrics['recall']}%")
    print(f"  F1 Score    : {metrics['f1']}%")
    print(f"  False Pos.  : {metrics['false_positives']}")
    _banner()

    # -- Export ------------------------------------------------------------
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    csv_path = output_dir / f"benchmark_{release_name}_{ts}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(details[0].keys()))
        writer.writeheader()
        writer.writerows(details)

    summary = {
        "timestamp":          ts,
        "release":            release_name,
        "canonical_names":    canonical_names,
        "canonical_dates":    canonical_dates,
        "canonical_numbers":  canonical_numbers,
        "canonical_locations": canonical_locations,
        "metrics":            metrics,
        "details":            details,
    }
    json_path = output_dir / f"benchmark_{release_name}_{ts}.json"
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    print(f"\n  CSV  : {csv_path}")
    print(f"  JSON : {json_path}\n")

    return summary


def _banner(title: str = "") -> None:
    print("=" * 60)
    if title:
        print(f"  {title}")
        print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multilingual QC Benchmark Runner")
    parser.add_argument("--release", default="release_001",
                        choices=list(_RELEASE_FACTS.keys()),
                        help="Release to benchmark (default: release_001)")
    parser.add_argument("--output", default="reports",
                        help="Output directory for reports (default: reports/)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    run_benchmark(release_name=args.release, output_dir=Path(args.output))
