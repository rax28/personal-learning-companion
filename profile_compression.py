from __future__ import annotations

import os
import time
from pathlib import Path

import numpy as np

from app.lmcompress.arithmetic_coder import (
    ArithmeticEncoder,
    probabilities_to_cumulative,
)
from app.lmcompress.compressor import LMCompressor
from app.lmcompress.llama_backend import Llama32Backend


# =====================================================================
# CONFIGURATION
# =====================================================================

N_CTX = 8192
N_BATCH = 64
N_GPU_LAYERS = -1

CORPUS = Path(
    os.environ.get(
        "LM_PROFILE_CORPUS",
        "benchmarks/nptel_medium.txt",
    )
)


# =====================================================================
# PROFILER
# =====================================================================

def profile(
    model_path: str,
    corpus_path: Path,
) -> None:

    print("=" * 70)
    print("LM COMPRESSION PROFILER")
    print("=" * 70)

    print(
        "Corpus:",
        corpus_path,
    )

    print(
        "Model:",
        model_path,
    )

    print()

    # ---------------------------------------------------------------
    # Load corpus
    # ---------------------------------------------------------------

    original = corpus_path.read_bytes()

    text = original.decode(
        "utf-8"
    )

    print(
        f"Original bytes: {len(original):,}"
    )

    # ---------------------------------------------------------------
    # Load backend
    # ---------------------------------------------------------------

    backend = Llama32Backend(
        model_path,
        n_ctx=N_CTX,
        n_batch=N_BATCH,
        n_gpu_layers=N_GPU_LAYERS,
    )

    compressor = LMCompressor(
        backend
    )

    print(
        "N_CTX:",
        backend.n_ctx,
    )

    print(
        "N_BATCH:",
        backend.llm.n_batch,
    )

    print(
        "VOCAB SIZE:",
        backend.vocab_size,
    )

    print()

    # ===============================================================
    # TOKENIZATION
    # ===============================================================

    tokenization_start = time.perf_counter()

    tokens = compressor.tokenize(
        text
    )

    tokenization_time = (
        time.perf_counter()
        - tokenization_start
    )

    print(
        f"{'Tokenization':<30}"
        f"{tokenization_time:>10.4f}s"
    )

    print(
        f"Tokens: {len(tokens):,}"
    )

    if len(tokens) < 2:
        raise RuntimeError(
            "Need at least two tokens."
        )

    if len(tokens) > N_CTX:
        raise RuntimeError(
            f"Corpus contains {len(tokens)} tokens, "
            f"but N_CTX={N_CTX}."
        )

    print()

    # ===============================================================
    # STAGE TIMERS
    # ===============================================================

    llama_time = 0.0
    softmax_time = 0.0
    cdf_time = 0.0
    arithmetic_time = 0.0

    # ===============================================================
    # ARITHMETIC ENCODER
    # ===============================================================

    encoder = ArithmeticEncoder(
        precision=compressor.precision
    )

    # ===============================================================
    # FIRST TOKEN
    #
    # The compressor stores the first token literally.
    # It does not arithmetic-code it.
    # ===============================================================

    first_token = int(
        tokens[0]
    )

    start = time.perf_counter()

    logits = backend.start_context(
        first_token
    )

    llama_time += (
        time.perf_counter()
        - start
    )

    # ===============================================================
    # INCREMENTAL COMPRESSION PROFILE
    # ===============================================================

    print(
        "Profiling incremental compression..."
    )

    total_tokens_to_encode = len(tokens) - 1

    for position in range(
        1,
        len(tokens),
    ):

        target = int(
            tokens[position]
        )

        # -----------------------------------------------------------
        # SOFTMAX
        # -----------------------------------------------------------

        start = time.perf_counter()

        probabilities = backend.softmax(
            logits
        )

        softmax_time += (
            time.perf_counter()
            - start
        )

        # -----------------------------------------------------------
        # CDF
        # -----------------------------------------------------------

        start = time.perf_counter()

        cumulative = (
            probabilities_to_cumulative(
                probabilities,
                total=compressor.cdf_total,
            )
        )

        cdf_time += (
            time.perf_counter()
            - start
        )

        # -----------------------------------------------------------
        # ARITHMETIC ENCODE
        # -----------------------------------------------------------

        start = time.perf_counter()

        cumulative_low = int(
            cumulative[target]
        )

        cumulative_high = int(
            cumulative[target + 1]
        )

        encoder.encode(
            cumulative_low,
            cumulative_high,
            compressor.cdf_total,
        )

        arithmetic_time += (
            time.perf_counter()
            - start
        )

        # -----------------------------------------------------------
        # APPEND TARGET TO LM CONTEXT
        #
        # This must happen AFTER coding because the prediction was
        # generated from the prefix before target was known.
        # -----------------------------------------------------------

        start = time.perf_counter()

        logits = backend.evaluate_next(
            target
        )

        llama_time += (
            time.perf_counter()
            - start
        )

        # -----------------------------------------------------------
        # Progress
        # -----------------------------------------------------------

        if (
            position % 500 == 0
            or position == len(tokens) - 1
        ):

            print(
                f"  {position:,}/"
                f"{total_tokens_to_encode:,} tokens"
            )

    # ===============================================================
    # FINISH ARITHMETIC CODER
    # ===============================================================

    start = time.perf_counter()

    encoded_data, padded_bits = (
        encoder.finish()
    )

    arithmetic_time += (
        time.perf_counter()
        - start
    )

    # ===============================================================
    # RESULTS
    # ===============================================================

    stage_total = (
        tokenization_time
        + llama_time
        + softmax_time
        + cdf_time
        + arithmetic_time
    )

    print()

    print("=" * 70)
    print("PROFILE RESULTS")
    print("=" * 70)

    print(
        f"{'Stage':<30}"
        f"{'Time':>12}"
        f"{'%':>10}"
        f"{'ms/token':>14}"
    )

    print("-" * 70)

    stages = [
        (
            "Tokenization",
            tokenization_time,
        ),
        (
            "Llama inference",
            llama_time,
        ),
        (
            "Softmax",
            softmax_time,
        ),
        (
            "CDF construction",
            cdf_time,
        ),
        (
            "Arithmetic coding",
            arithmetic_time,
        ),
    ]

    for name, seconds in stages:

        percentage = (
            seconds
            / stage_total
            * 100.0
            if stage_total > 0
            else 0.0
        )

        per_token_ms = (
            seconds
            / total_tokens_to_encode
            * 1000.0
        )

        print(
            f"{name:<30}"
            f"{seconds:>12.4f}"
            f"{percentage:>9.2f}%"
            f"{per_token_ms:>13.3f}"
        )

    print("-" * 70)

    print(
        f"{'Measured pipeline total':<30}"
        f"{stage_total:>12.4f}s"
    )

    print()

    # ===============================================================
    # COMPRESSION RESULT
    # ===============================================================

    # The actual compressor includes a header and first token.
    # This raw encoder result is only useful as a sanity check.
    print(
        "Raw arithmetic payload:",
        f"{len(encoded_data):,}",
        "bytes",
    )

    print(
        "Padded bits:",
        padded_bits,
    )

    # ===============================================================
    # ACTUAL COMPRESSOR
    # ===============================================================

    print()

    print("=" * 70)
    print("ACTUAL COMPRESSOR CHECK")
    print("=" * 70)

    backend.reset()

    start = time.perf_counter()

    result = compressor.compress(
        text
    )

    actual_compression_time = (
        time.perf_counter()
        - start
    )

    print(
        f"Actual compression time:"
        f" {actual_compression_time:.4f}s"
    )

    print(
        f"Compressed bytes:"
        f" {len(result.data):,}"
    )

    print(
        f"Compression ratio:"
        f" {len(result.data) / len(original):.6f}"
    )

    print(
        f"Bits / byte:"
        f" {len(result.data) * 8 / len(original):.4f}"
    )

    # ===============================================================
    # FINAL
    # ===============================================================

    print()

    print("=" * 70)
    print("PROFILER COMPLETE")
    print("=" * 70)


# =====================================================================
# MAIN
# =====================================================================

if __name__ == "__main__":

    model = os.environ.get(
        "LLAMA_MODEL_PATH"
    )

    if not model:
        raise RuntimeError(
            "Set LLAMA_MODEL_PATH before running."
        )

    if not CORPUS.exists():
        raise FileNotFoundError(
            f"Corpus does not exist: {CORPUS}"
        )

    profile(
        model,
        CORPUS,
    )
