from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class SourceChunk:
    source_id: str
    index: int
    text: str


def chunk_text(source_id: str, text: str, max_chars: int = 1800) -> list[SourceChunk]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out: list[SourceChunk] = []
    buf = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            words = paragraph.split()
            piece = ""
            for word in words:
                candidate = f"{piece} {word}".strip()
                if piece and len(candidate) > max_chars:
                    out.append(SourceChunk(source_id, len(out), piece))
                    piece = word
                else:
                    piece = candidate
            if piece:
                if buf:
                    out.append(SourceChunk(source_id, len(out), buf))
                    buf = ""
                out.append(SourceChunk(source_id, len(out), piece))
            continue
        if buf and len(buf) + len(paragraph) + 1 > max_chars:
            out.append(SourceChunk(source_id, len(out), buf))
            buf = ""
        buf = f"{buf}\n{paragraph}".strip()
    if buf:
        out.append(SourceChunk(source_id, len(out), buf))
    return out
