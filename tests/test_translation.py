"""Tests for the translation module."""
from __future__ import annotations

from core.translation import translate, DemoTranslationProvider, set_provider


def test_demo_translation_stub():
    """Test that the demo provider returns a stub for unknown text."""
    # Force demo provider for this test
    set_provider(DemoTranslationProvider())
    hi = translate("Hello world", "English", "Hindi")
    assert "[Demo Translation — Hindi]" in hi
    assert "Hello world" in hi


def test_translation_returns_string():
    """Translation always returns a non-empty string."""
    result = translate("Test text", "English", "Hindi")
    assert isinstance(result, str)
    assert len(result) > 0
