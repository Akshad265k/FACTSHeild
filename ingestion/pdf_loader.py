"""PDF loader using PyMuPDF (fitz)."""
from __future__ import annotations

import io
from pathlib import Path


def load_pdf(source: str | bytes | Path) -> str:
    """
    Extract plain text from a PDF file using PyMuPDF.

    Parameters
    ----------
    source
        File path or raw bytes content of the PDF.

    Returns
    -------
    str
        All page text joined by newlines.
    """
    try:
        import fitz  # type: ignore  # PyMuPDF
    except ImportError as exc:
        raise ImportError(
            "PyMuPDF is required for .pdf support. "
            "Install it with: pip install PyMuPDF"
        ) from exc

    if isinstance(source, (str, Path)):
        doc = fitz.open(str(source))
    elif isinstance(source, bytes):
        doc = fitz.open(stream=source, filetype="pdf")
    else:
        raise TypeError(f"Unsupported source type: {type(source)}")

    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(pages)
