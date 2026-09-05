"""
Text summarization for social media post generation.

Uses sumy (LexRank algorithm) for extractive summarization — picks the
most representative sentences from the source text.  Falls back to
simple sentence truncation when sumy is unavailable.
"""
from __future__ import annotations

import re
from typing import Optional


def _split_sentences(text: str) -> list[str]:
    """Naive sentence splitter for fallback use."""
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s.strip()]


def summarize(
    text: str,
    sentence_count: int = 3,
    platform: str = "generic",
) -> str:
    """
    Generate a concise summary of *text*.

    Parameters
    ----------
    text : str
        Full English source text to summarize.
    sentence_count : int
        Number of sentences in the summary.
    platform : str
        ``"linkedin"`` (professional), ``"instagram"`` (short, punchy),
        or ``"generic"`` (neutral).

    Returns
    -------
    str
        The summarized text.
    """
    if not text or not text.strip():
        return ""

    # Adjust sentence count by platform
    if platform == "instagram":
        sentence_count = min(sentence_count, 2)
    elif platform == "linkedin":
        sentence_count = max(sentence_count, 3)

    try:
        from sumy.parsers.plaintext import PlaintextParser
        from sumy.nlp.tokenizers import Tokenizer
        from sumy.summarizers.lex_rank import LexRankSummarizer

        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = LexRankSummarizer()

        # LexRank picks the most representative sentences
        summary_sentences = summarizer(parser.document, sentence_count)

        if summary_sentences:
            return " ".join(str(s) for s in summary_sentences)
    except Exception:
        pass

    # ── Fallback: simple extractive pick ──────────────────────────────────
    sentences = _split_sentences(text)
    if not sentences:
        return text[:300].strip()

    selected = sentences[:sentence_count]
    result = " ".join(selected)
    if not result.endswith("."):
        result += "."
    return result


def format_linkedin_post(
    summary: str,
    names: list[str],
    locations: list[str],
    dates: list[str],
    hashtags: list[str],
) -> str:
    """Compose a professional LinkedIn post from a summary and facts."""
    post = summary + "\n"

    # Add structured fact highlights
    highlights: list[str] = []
    if names:
        highlights.append(f"👤 {', '.join(names)}")
    if locations:
        highlights.append(f"📍 {', '.join(locations)}")
    if dates:
        highlights.append(f"📅 {', '.join(dates)}")

    if highlights:
        post += "\n" + "\n".join(highlights) + "\n"

    post += "\n" + " ".join(hashtags[:6])
    return post


def format_instagram_post(
    summary: str,
    locations: list[str],
    hashtags: list[str],
) -> str:
    """Compose a concise Instagram post from a summary and facts."""
    post = summary + "\n"

    if locations:
        post += f"\n📍 {', '.join(locations)}\n"

    post += "\n" + " ".join(hashtags)
    return post
