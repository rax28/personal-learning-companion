from __future__ import annotations

import base64
import hashlib
import math
import os
import zlib
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class CompressionResult:
    original_bytes: int
    compressed_bytes: int
    ratio: float
    sha256: str
    codec: str
    model: str | None
    model_used: bool
    estimated_model_bits: float | None
    payload_b64: str
    note: str


def compress_lossless(data: bytes, level: int = 9) -> bytes:
    """Baseline lossless archive. The bytes round-trip exactly."""
    return zlib.compress(data, level)


def decompress_lossless(data: bytes) -> bytes:
    return zlib.decompress(data)


def _safe_bits(logprobs: list[dict[str, Any]]) -> float | None:
    if not logprobs:
        return None
    total = 0.0
    count = 0
    for item in logprobs:
        lp = item.get("logprob")
        if isinstance(lp, (int, float)) and math.isfinite(lp):
            total += -float(lp) / math.log(2)
            count += 1
    return total if count else None


async def _ollama_predictability(text: str, model: str) -> tuple[float | None, int, str]:
    """Ask Ollama for prompt-token logprobs when its OpenAI-compatible endpoint supports echo.

    LMCompress uses predictive distributions plus arithmetic coding. Ollama exposes
    logprobs on its native and OpenAI-compatible APIs, so we use those probabilities
    to measure model-predictability here. The actual archive remains lossless and is
    encoded by the deterministic zlib fallback because Ollama does not expose a
    complete vocabulary distribution suitable for a standalone arithmetic decoder.
    """
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    url = f"{base}/v1/completions"
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            r = await client.post(url, json={
                "model": model,
                "prompt": text,
                "max_tokens": 0,
                "echo": True,
                "logprobs": 1,
                "stream": False,
            })
            r.raise_for_status()
            data = r.json()
            choice = (data.get("choices") or [{}])[0]
            lp = ((choice.get("logprobs") or {}).get("token_logprobs") or [])
            bits = _safe_bits([{"logprob": x} for x in lp if x is not None])
            return bits, len(lp), model
    except Exception:
        return None, 0, model


async def compress_text(text: str, model: str | None = None) -> CompressionResult:
    raw = text.encode("utf-8")
    packed = compress_lossless(raw)
    model = model or os.getenv("LOCAL_MODEL", "llama3.2")
    bits, token_count, used_model = None, 0, False
    if model:
        bits, token_count, _ = await _ollama_predictability(text, model)
        used_model = bits is not None

    return CompressionResult(
        original_bytes=len(raw),
        compressed_bytes=len(packed),
        ratio=(len(raw) / len(packed)) if packed else 1.0,
        sha256=hashlib.sha256(raw).hexdigest(),
        codec="lmcompress-inspired/zlib-lossless",
        model=model,
        model_used=used_model,
        estimated_model_bits=bits,
        payload_b64=base64.b64encode(packed).decode("ascii"),
        note=(
            f"Model predictability measured over {token_count} returned prompt tokens; "
            "the stored payload is still a byte-exact lossless archive. "
            "This is an LMCompress-inspired integration, not a claim of reproducing the paper's full codec."
            if used_model else
            "Ollama model scoring was unavailable, so the lossless archive was produced without the model pass."
        ),
    ).__dict__
