"""
Rule engine — loads rule definitions and settings from YAML config files.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).parent.parent / "config"


def load_rules(path: Optional[Path] = None) -> dict[str, dict]:
    """
    Load QC rules from *rules.yaml*.

    Returns
    -------
    dict keyed by rule ID (e.g. ``{"RULE-NUM-001": {...}, ...}``)
    """
    try:
        import yaml
    except ImportError:
        logger.warning("pyyaml not installed; returning empty rules dict.")
        return {}

    rules_path = path or (_CONFIG_DIR / "rules.yaml")
    if not rules_path.exists():
        logger.warning("rules.yaml not found at %s", rules_path)
        return {}

    with open(rules_path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    return {rule["id"]: rule for rule in data.get("rules", [])}


def load_settings(path: Optional[Path] = None) -> dict:
    """
    Load system settings from *settings.yaml*.

    Falls back to hard-coded defaults when the file is unavailable.
    """
    try:
        import yaml
    except ImportError:
        return _defaults()

    settings_path = path or (_CONFIG_DIR / "settings.yaml")
    if not settings_path.exists():
        logger.warning("settings.yaml not found at %s; using defaults.", settings_path)
        return _defaults()

    with open(settings_path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data or _defaults()


def _defaults() -> dict:
    return {
        "scoring": {
            "base_score": 100,
            "critical_penalty": -20,
            "warning_penalty": -10,
            "minor_penalty": -5,
        },
        "matching": {
            "name_strong_threshold": 0.88,
            "name_probable_threshold": 0.75,
            "name_review_threshold": 0.65,
        },
    }
