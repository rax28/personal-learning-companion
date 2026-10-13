

import os
import time
from pathlib import Path

import numpy as np

from app.lmcompress.arithmetic_coder import probabilities_to_cumulative
from app.lmcompress.llama_backend import Llama32Backend
from app.lmcompress.compressor import LMCompressor


N_CTX = 8192
N_BATCH = 64
N_GPU_LAYERS = -1

CORPUS = Path("benchmarks/nptel_medium.txt")


def timed(label: str, fn):
    start = time.perf_counter()
    result = fn()
    elapsed = time.perf_counter() - start
    print(f"{label:<28} {elapsed:10.4f}s")
    return result, elapsed


def profile(model_path: str, corpus_path: Path) -> None:
    print("=" * 70)
    print("LM COMPRESSION PROFILER")
    print("=" * 70)
    print(f"Corpus: {corpus_path}")
    print(f"Model:  {model_path}")
    print()

    original = corpus_path.read_bytes()
    text = original.decode("utf-8")

    print(f"Original bytes: {len(original):,}")

    backend = Llama32Backend(
        model_path,
        n_ctx=N_CTX,
        n_batch=N_BATCH,
        n_gpu_layers=N_GPU_LAYERS,
    )

    compressor = LMCompressor(backend)

    print(f"N_CTX: {backend.n_ctx}")
    print(f"N_BATCH: {backend.llm.n_batch}")
    print(f"VOCAB SIZE: {backend.vocab_size}")
    print()

    # ------------------------------------------------------------
    # Tokenization
    # ------------------------------------------------------------

    tokens, tokenization_time = timed(
        "Tokenization",
        lambda: compressor.tokenize(text),
    )

    print(f"Tokens: {len(tokens):,}")
    print()

    if len(tokens) > N_CTX:
        raise RuntimeError(
            f"Corpus has {len(tokens)} tokens but N_CTX={N_CTX}. "
            "Increase N_CTX before profiling this corpus."
        )

    if len(tokens) < 2:
        raise RuntimeError("Need at least two tokens.")

    # ------------------------------------------------------------
    # Profile the actual incremental LM path.
    #
    # We deliberately measure:
    #   1. Llama eval
    #   2. softmax
    #   3. CDF construction
    #   4. arithmetic encode
    #
    # This does NOT replace compressor.compress().
    # It is diagnostic only.
    # ------------------------------------------------------------

    backend.reset()

    first_logits, first_time = timed(
        "First Llama evaluation",
        lambda: backend.start_context(tokens[0]),
    )

    llama_time = first_time
    softmax_time = 0.0
    cdf_time = 0.0
    arithmetic_time = 0.0

    # We profile the same probability preparation used by LMCompressor.
    # Arithmetic coding itself is measured separately below using a
    # lightweight pass through the existing encoder implementation.

    from app.lmcompress.arithmetic_coder import ArithmeticEncoder

    encoder = ArithmeticEncoder(32)

    for i, target in enumerate(tokens[1:], start=1):
        # Llama inference
        start = time.perf_counter()
        logits = backend.evaluate_next(target)
        llama_time += time.perf_counter() - start

        # Softmax
        start = time.perf_counter()
        probabilities = backend.softmax(logits)
        softmax_time += time.perf_counter() - start

        # CDF
        start = time.perf_counter()
        cumulative = probabilities_to_cumulative(
            probabilities,
            total=1 << 24,
        )
        cdf_time += time.perf_counter() - start

        # Arithmetic coding
        start = time.perf_counter()

        symbol = int(target)

        cumulative_low = cumulative[symbol]
        cumulative_high = cumulative[symbol + 1]
        total = cumulative[-1]

        encoder.encode(
            cumulative_low,
            cumulative_high,
            total,
        )

        arithmetic_time += time.perf_counter() - start

        if i % 500 == 0 or i == len(tokens) - 1:
            print(f"Profiled {i:,}/{len(tokens)-1:,} tokens")

    # Flush timing is included in arithmetic coding.
    start = time.perf_counter()
    encoder.finish()
    arithmetic_time += time.perf_counter() - start

    print()
    print("=" * 70)
    print("PROFILE RESULTS")
    print("=" * 70)

    total = (
        tokenization_time
        + llama_time
        + softmax_time
        + cdf_time
        + arithmetic_time
    )

    rows = [
        ("Tokenization", tokenization_time),
        ("Llama inference", llama_time),
        ("Softmax", softmax_time),
        ("CDF construction", cdf_time),
        ("Arithmetic coding", arithmetic_time),
    ]

    for name, seconds in rows:
        pct = (seconds / total * 100.0) if total else 0.0
        per_token = seconds / max(len(tokens) - 1, 1)
        print(
            f"{name:<28} "
            f"{seconds:10.4f}s  "
            f"{pct:7.2f}%  "
            f"{per_token*1000:9.3f} ms/token"
        )

    print("-" * 70)
    print(
        f"{'Measured total':<28} "
        f"{total:10.4f}s"
    )

    print()
    print("=" * 70)
    print("ACTUAL COMPRESSOR CHECK")
    print("=" * 70)

    backend.reset()

    start = time.perf_counter()
    result = compressor.compress(text)
    actual_compression_time = time.perf_counter() - start

    print(
        f"Actual compressor time: {actual_compression_time:.4f}s"
    )
    print(
        f"Compressed bytes: {len(result.data):,}"
    )
    print(
        f"Compression bits/byte: "
        f"{len(result.data) * 8 / len(original):.4f}"
    )

    print()
    print("PROFILE COMPLETE")


if __name__ == "__main__":
    model = os.environ.get("LLAMA_MODEL_PATH")

    if not model:
        raise RuntimeError(
            "Set LLAMA_MODEL_PATH before running."
        )

    corpus = Path(
        os.environ.get(
            "LM_PROFILE_CORPUS",
            str(CORPUS),
        )
    )

    if not corpus.exists():
        raise FileNotFoundError(
            f"Corpus does not exist: {corpus}"
        )

    profile(model, corpus)
