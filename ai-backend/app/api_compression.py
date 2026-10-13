from __future__ import annotations

import base64
import io
from pathlib import Path
from urllib.parse import urlparse

import httpx
from pypdf import PdfReader

from app.source_compression import compress_text, decompress_lossless
from app.source_chunking import chunk_text

DEFAULT_SOURCE = "https://assets-eu.researchsquare.com/files/rs-4735292/v1_covered_8023c9b3-2212-4462-b164-74a1849c30e7.pdf"


def _extract_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return "\n\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()


async def load_source(url: str) -> dict:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Source URL must use http or https")
    async with httpx.AsyncClient(timeout=90, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
    content = response.content
    content_type = response.headers.get("content-type", "")
    if url.lower().endswith(".pdf") or "application/pdf" in content_type:
        text = _extract_pdf(content)
        kind = "pdf"
    else:
        text = content.decode("utf-8", errors="replace")
        kind = "text"
    return {"url": url, "kind": kind, "text": text}


async def compress_input(text: str, model: str | None = None, source_url: str | None = None) -> dict:
    if not text.strip():
        raise ValueError("Input text is empty")
    chunks = chunk_text(source_url or "manual-input", text)
    result = await compress_text(text, model=model)
    result.update({
        "source_url": source_url,
        "chunks": len(chunks),
        "chunk_preview": [c.text[:220] for c in chunks[:5]],
    })
    return result
