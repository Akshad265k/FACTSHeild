"""Plain text file loader."""
from __future__ import annotations

from pathlib import Path


def load_text(source: str | bytes | Path, encoding: str = "utf-8") -> str:
    """
    Load plain text from a file path or raw bytes.

    Parameters
    ----------
    source
        File path (str / Path) or raw bytes content.
    encoding
        Text encoding; defaults to UTF-8.

    Returns
    -------
    str
        Decoded text content.
    """
    if isinstance(source, (str, Path)):
        return Path(source).read_text(encoding=encoding)
    if isinstance(source, bytes):
        return source.decode(encoding, errors="replace")
    raise TypeError(f"Unsupported source type: {type(source)}")
