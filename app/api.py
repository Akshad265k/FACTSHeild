"""HTTP adapter for the FACTSHIELD engine.

This module deliberately contains no matching or scoring rules.  It only
turns requests from the React interface into calls to the existing engine.
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.comparison import compare_versions
from core.entity_matching import load_aliases_db
from core.location_matching import load_location_aliases
from core.provenance import fact_fingerprint, verify_circulating_copy
from core.source_extraction import extract_canonical_facts
from core.translation import RealTranslationProvider, translate, set_provider
from evaluation.benchmark import run_benchmark
from ingestion.docx_loader import load_docx

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "data" / "sample_releases"

app = FastAPI(title="FACTSHIELD API", version="2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict:
    return {
        "status": "ok",
        "message": "FACTSHIELD API is running",
        "docs": "/docs",
        "health": "/api/health",
    }



class AnalysisRequest(BaseModel):
    source_text: str
    hindi_text: str | None = None
    marathi_text: str | None = None
    auto_translate: bool = False


class TranslationRequest(BaseModel):
    source_text: str


class ProvenanceRequest(BaseModel):
    facts: list[dict]
    circulating_text: str


class SocialPostRequest(BaseModel):
    facts: list[dict]
    qc_status: str
    qc_score: int = 0
    theme: str = "professional"
    source_text: str = ""


class SocialVerificationRequest(BaseModel):
    facts: list[dict]
    post_text: str


def _analyse(source_text: str, hindi_text: str, marathi_text: str) -> dict:
    """Run the unchanged extraction and comparison pipeline."""
    aliases = load_aliases_db()
    locations = load_location_aliases()
    facts = extract_canonical_facts(source_text, aliases, locations)
    result = compare_versions(
        versions={"English": source_text, "Hindi": hindi_text, "Marathi": marathi_text},
        canonical_names=[fact.canonical_value for fact in facts["names"]],
        canonical_dates=[fact.source_text for fact in facts["dates"]],
        canonical_numbers=[fact.canonical_value for fact in facts["numbers"]],
        canonical_locations=[fact.canonical_value for fact in facts["locations"]],
    )
    result.canonical_facts = facts["all"]
    return {
        "result": result.model_dump(mode="json"),
        "facts": [fact.model_dump(mode="json") for fact in facts["all"]],
        "versions": {"English": source_text, "Hindi": hindi_text, "Marathi": marathi_text},
    }


def _social_hashtags(facts: list, theme: str) -> list[str]:
    """Build content-relevant hashtags from the actual facts."""
    tags: list[str] = []
    locations = [f.canonical_value for f in facts if f.type == "location"]
    for loc in locations[:2]:
        tags.append(f"#{loc.replace(' ', '')}")
    if any(f.type == "name" for f in facts):
        tags.append("#IndianArmy")
    if theme == "community":
        tags.extend(["#CommunityOutreach", "#ServeAndProtect", "#PublicWelfare"])
    else:
        tags.extend(["#DefenceUpdates", "#IndianDefence", "#NationFirst"])
    tags.extend(["#OfficialUpdate", "#VerifiedRelease"])
    return tags


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/samples")
def samples() -> list[dict]:
    return [
        {"id": item.name, "label": item.name.replace("_", " ").title()}
        for item in sorted(SAMPLES.glob("release_*"))
        if item.is_dir()
    ]


@app.get("/api/samples/{release_name}")
def sample(release_name: str) -> dict:
    folder = SAMPLES / release_name
    if not folder.is_dir() or folder.parent != SAMPLES:
        raise HTTPException(status_code=404, detail="Sample release not found")
    try:
        return {
            "English": (folder / "english.txt").read_text(encoding="utf-8"),
            "Hindi": (folder / "hindi.txt").read_text(encoding="utf-8"),
            "Marathi": (folder / "marathi.txt").read_text(encoding="utf-8"),
        }
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Sample release is incomplete") from error


@app.post("/api/analyse")
def analyse(request: AnalysisRequest) -> dict:
    if not request.source_text.strip():
        raise HTTPException(status_code=422, detail="English source text is required")
    hindi, marathi = request.hindi_text, request.marathi_text
    if request.auto_translate:
        set_provider(RealTranslationProvider())
        hindi = translate(request.source_text, "English", "Hindi")
        marathi = translate(request.source_text, "English", "Marathi")
    if not hindi or not marathi:
        raise HTTPException(status_code=422, detail="Provide both Hindi and Marathi text, or enable auto-translation")
    return _analyse(request.source_text, hindi, marathi)


@app.post("/api/translate")
def translate_source(request: TranslationRequest) -> dict:
    """Generate the reviewable Hindi and Marathi texts before QC is run."""
    if not request.source_text.strip():
        raise HTTPException(status_code=422, detail="English source text is required")
    set_provider(RealTranslationProvider())
    return {
        "Hindi": translate(request.source_text, "English", "Hindi"),
        "Marathi": translate(request.source_text, "English", "Marathi"),
    }


@app.post("/api/documents/extract")
async def extract_document(file: UploadFile = File(...)) -> dict:
    """Extract text from a user-provided TXT or DOCX document for the React UI."""
    filename = file.filename or ""
    raw = await file.read()
    if filename.lower().endswith(".docx"):
        return {"text": load_docx(raw)}
    if filename.lower().endswith(".txt"):
        return {"text": raw.decode("utf-8", errors="replace")}
    raise HTTPException(status_code=422, detail="Only .txt and .docx files are supported")


@app.post("/api/provenance")
def provenance(request: ProvenanceRequest) -> dict:
    if not request.circulating_text.strip():
        raise HTTPException(status_code=422, detail="Circulating copy is required")
    # Rebuild validated models so the existing provenance implementation stays intact.
    from core.models import CanonicalFact
    facts = [CanonicalFact.model_validate(item) for item in request.facts]
    verification = verify_circulating_copy(facts, request.circulating_text)
    return {
        "fingerprint": fact_fingerprint(facts),
        "verification": verification.model_dump(mode="json"),
    }


@app.post("/api/social-posts")
def create_social_posts(request: SocialPostRequest) -> dict:
    """Create platform-ready drafts using extractive summarization."""
    if request.qc_score <= 80:
        raise HTTPException(status_code=422, detail="Social drafts require a QC score above 80")
    from core.models import CanonicalFact
    from core.summarization import summarize, format_linkedin_post, format_instagram_post

    facts = [CanonicalFact.model_validate(item) for item in request.facts]
    if not facts:
        raise HTTPException(status_code=422, detail="No verified facts are available for this release")

    hashtags = _social_hashtags(facts, request.theme)
    names = [f.canonical_value for f in facts if f.type == "name"]
    locations = [f.canonical_value for f in facts if f.type == "location"]
    dates = [f.source_text for f in facts if f.type == "date"]

    # Generate platform-specific summaries using LexRank extractive summarization
    li_summary = summarize(request.source_text, sentence_count=3, platform="linkedin")
    ig_summary = summarize(request.source_text, sentence_count=2, platform="instagram")

    linked_in = format_linkedin_post(li_summary, names, locations, dates, hashtags)
    instagram = format_instagram_post(ig_summary, locations, hashtags)

    return {"linkedin": linked_in, "instagram": instagram, "hashtags": hashtags}


@app.post("/api/social-posts/verify")
def verify_social_post(request: SocialVerificationRequest) -> dict:
    """Reject a caption that introduces extractable facts absent from the QC baseline."""
    from collections import Counter
    from core.models import CanonicalFact
    from core.provenance import canonical_lines

    facts = [CanonicalFact.model_validate(item) for item in request.facts]
    # Hashtags and language labels are platform metadata, not release facts.
    # Exclude them from fact extraction so a generic tag cannot be mistaken
    # for a name by a fuzzy alias rule.
    fact_prose = re.sub(r"#[\w]+", "", request.post_text)
    fact_prose = re.sub(r"\b(English|Hindi|Marathi)\b", "", fact_prose, flags=re.I)
    observed = extract_canonical_facts(fact_prose)["all"]
    approved = Counter(canonical_lines(facts))
    present = Counter(canonical_lines(observed))
    unexpected = sorted((present - approved).elements())
    covered = sorted((present & approved).elements())
    return {
        "status": "SAFE" if not unexpected else "REVIEW_REQUIRED",
        "unexpected_facts": [line.replace("|", ": ", 1) for line in unexpected],
        "verified_facts_used": [line.replace("|", ": ", 1) for line in covered],
    }


@app.post("/api/benchmark/{release_name}")
def benchmark(release_name: str) -> dict:
    if not (SAMPLES / release_name).is_dir():
        raise HTTPException(status_code=404, detail="Sample release not found")
    return run_benchmark(release_name=release_name, output_dir=ROOT / "reports")
