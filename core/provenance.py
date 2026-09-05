"""Cryptographic fact fingerprints and circulating-copy verification.

The fingerprint covers normalized extracted facts rather than source wording.
Formatting or prose changes therefore do not invalidate an official release;
factual additions, removals, and substitutions do.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
from typing import Iterable

from .models import CanonicalFact, ProvenanceResult
from .source_extraction import extract_canonical_facts

_TYPE_ORDER = {"name": "PERSON", "location": "LOCATION", "date": "DATE", "number": "NUMBER"}


def canonical_lines(facts: Iterable[CanonicalFact]) -> list[str]:
    """Produce a stable, order-independent serialization of a fact set."""
    return sorted(
        f"{_TYPE_ORDER[fact.type]}|{fact.canonical_value.strip().casefold()}"
        for fact in facts
    )


def fact_fingerprint(facts: Iterable[CanonicalFact]) -> str:
    """Return the SHA-256 fingerprint for a canonical fact set."""
    return sha256("\n".join(canonical_lines(facts)).encode("utf-8")).hexdigest()


def verify_circulating_copy(
    authoritative_facts: list[CanonicalFact], circulating_text: str,
) -> ProvenanceResult:
    """Compare facts from a later English copy against the authoritative set."""
    circulating = extract_canonical_facts(circulating_text)["all"]
    # Counters preserve multiplicity: omitting one of two occurrences of a
    # number is still meaningful factual drift.
    expected = Counter(canonical_lines(authoritative_facts))
    observed = Counter(canonical_lines(circulating))

    def display(line: str) -> dict[str, str]:
        kind, value = line.split("|", 1)
        return {"type": kind, "value": value}

    missing = sorted((expected - observed).elements())
    added = sorted((observed - expected).elements())
    return ProvenanceResult(
        authoritative_fingerprint=fact_fingerprint(authoritative_facts),
        circulating_fingerprint=fact_fingerprint(circulating),
        status="VERIFIED" if not missing and not added else "TAMPER_DETECTED",
        missing_facts=[display(line) for line in missing],
        added_facts=[display(line) for line in added],
        authoritative_lines=canonical_lines(authoritative_facts),
        circulating_lines=canonical_lines(circulating),
    )
