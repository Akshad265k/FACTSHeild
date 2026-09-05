"""
Translation / localization layer.

Provides an abstracted ``translate()`` function that can be backed by:
  1. **Demo mode** (default): returns pre-prepared sample translations from disk
  2. **API mode** (optional): calls an external translation API if configured

The system remains fully runnable without paid APIs.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional, Protocol

try:
    from deep_translator import GoogleTranslator
    _HAS_TRANSLATOR = True
except ImportError:
    _HAS_TRANSLATOR = False

try:
    from transformers import pipeline
    _HAS_TRANSFORMERS = True
except ImportError:
    _HAS_TRANSFORMERS = False

logger = logging.getLogger(__name__)

_SAMPLES_DIR = Path(__file__).parent.parent / "data" / "sample_releases"

# Pre-built sample translations keyed by (English text fingerprint → release dir)
# In demo mode we match based on the loaded release.
_LANG_FILE_MAP = {
    "Hindi":   "hindi.txt",
    "Marathi": "marathi.txt",
}


# ---------------------------------------------------------------------------
# Provider protocol
# ---------------------------------------------------------------------------


class TranslationProvider(Protocol):
    """Abstract interface for a translation backend."""

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        ...


# ---------------------------------------------------------------------------
# Demo provider (uses pre-prepared sample files)
# ---------------------------------------------------------------------------


class DemoTranslationProvider:
    """
    Returns pre-prepared sample translations from the data/sample_releases/ folder.

    For each release, the provider looks up the Hindi/Marathi file that was
    written alongside the English original. This allows the full pipeline to
    work offline without any API.
    """

    def __init__(self, release_dir: Optional[Path] = None):
        self._release_dir = release_dir
        self._cache: dict[str, str] = {}

    def set_release_dir(self, release_dir: Path) -> None:
        """Point this provider at a specific release directory."""
        self._release_dir = release_dir
        self._cache.clear()

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Return the pre-prepared translation for *target_lang*.

        Falls back to a stub message if no sample file is available.
        """
        if target_lang in self._cache:
            return self._cache[target_lang]

        if self._release_dir:
            fname = _LANG_FILE_MAP.get(target_lang)
            if fname:
                p = self._release_dir / fname
                if p.exists():
                    translated = p.read_text(encoding="utf-8")
                    self._cache[target_lang] = translated
                    return translated

        # Fallback stub
        stub = (
            f"[Demo Translation — {target_lang}]\n\n"
            f"A production translation provider would generate a {target_lang} "
            f"version of the source text here.\n\n"
            f"--- Original ({source_lang}) ---\n{text[:500]}"
        )
        return stub


class RealTranslationProvider:
    """
    Uses deep_translator (Google Translate API) to actually translate text.
    """

    def __init__(self):
        self._lang_map = {
            "Hindi": "hi",
            "Marathi": "mr",
        }

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if not _HAS_TRANSLATOR:
            return f"[Error] deep_translator not installed. Cannot translate to {target_lang}."
        
        target_code = self._lang_map.get(target_lang, "en")
        try:
            translator = GoogleTranslator(source="auto", target=target_code)
            
            # Split by double newline to preserve paragraph structure and keep chunks small
            # Google Translate unofficial API often truncates long continuous strings
            paragraphs = text.split("\n")
            translated_paragraphs = []
            
            for p in paragraphs:
                if not p.strip():
                    translated_paragraphs.append("")
                    continue
                
                # If a single paragraph is still too long, chunk it by characters safely
                if len(p) > 2000:
                    chunks = [p[i:i+2000] for i in range(0, len(p), 2000)]
                    trans_chunks = [translator.translate(c) for c in chunks]
                    translated_paragraphs.append("".join(trans_chunks))
                else:
                    translated_paragraphs.append(translator.translate(p))
                    
            return "\n".join(translated_paragraphs)
        except Exception as e:
            logger.error("Translation failed: %s", e)
            return f"[Translation Error] {e}"


class LocalNeuralTranslationProvider:
    """
    Uses HuggingFace transformers (MarianMT) for robust offline translation.
    """

    def __init__(self):
        self._models = {}
        self._model_map = {
            "Hindi": "Helsinki-NLP/opus-mt-en-hi",
            "Marathi": "Helsinki-NLP/opus-mt-en-mr",
        }

    def _get_model_and_tokenizer(self, target_lang: str):
        if target_lang not in self._models:
            model_name = self._model_map.get(target_lang)
            if not model_name:
                raise ValueError(f"No local model available for {target_lang}")
            logger.info(f"Loading local translation model for {target_lang}...")
            
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            self._models[target_lang] = (model, tokenizer)
        return self._models[target_lang]

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        if not _HAS_TRANSFORMERS:
            return f"[Error] transformers not installed. Cannot translate."
        
        try:
            model, tokenizer = self._get_model_and_tokenizer(target_lang)
            
            paragraphs = text.split("\n")
            translated_paragraphs = []
            
            for p in paragraphs:
                if not p.strip():
                    translated_paragraphs.append("")
                    continue
                
                # Simple chunking if paragraph is too long (avoiding token limit)
                # Max length for Marian is typically 512 tokens. 
                if len(p) > 1500:
                    chunks = [p[i:i+1500] for i in range(0, len(p), 1500)]
                    trans_chunks = []
                    for c in chunks:
                        inputs = tokenizer(c, return_tensors="pt", truncation=True, max_length=512)
                        outputs = model.generate(**inputs, max_length=512)
                        trans_chunks.append(tokenizer.decode(outputs[0], skip_special_tokens=True))
                    translated_paragraphs.append(" ".join(trans_chunks))
                else:
                    inputs = tokenizer(p, return_tensors="pt", truncation=True, max_length=512)
                    outputs = model.generate(**inputs, max_length=512)
                    translated_paragraphs.append(tokenizer.decode(outputs[0], skip_special_tokens=True))
                    
            return "\n".join(translated_paragraphs)
        except Exception as e:
            logger.error("Local Neural Translation failed: %s", e)
            return f"[Translation Error] {e}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Module-level default provider — use Google if available, else demo stub
if _HAS_TRANSLATOR:
    _provider: TranslationProvider = RealTranslationProvider()
else:
    _provider: TranslationProvider = DemoTranslationProvider()


def set_provider(provider: TranslationProvider) -> None:
    """Replace the active translation provider."""
    global _provider
    _provider = provider


def get_provider() -> TranslationProvider:
    """Return the active translation provider."""
    return _provider


def translate(text: str, source_lang: str, target_lang: str) -> str:
    """
    Translate *text* from *source_lang* to *target_lang* using the active
    provider.

    Parameters
    ----------
    text : str
        Source text to translate.
    source_lang : str
        Source language name (e.g. "English").
    target_lang : str
        Target language name (e.g. "Hindi", "Marathi").

    Returns
    -------
    str
        Translated text.
    """
    return _provider.translate(text, source_lang, target_lang)


def get_sample_release_dirs() -> list[Path]:
    """Return a sorted list of available sample release directories."""
    if _SAMPLES_DIR.exists():
        return sorted(d for d in _SAMPLES_DIR.iterdir() if d.is_dir())
    return []
