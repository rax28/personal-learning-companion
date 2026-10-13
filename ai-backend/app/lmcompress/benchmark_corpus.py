from __future__ import annotations

import os
import time
from pathlib import Path

from .compressor import LMCompressor
from .llama_backend import Llama32Backend


# =====================================================================
# CONFIGURATION
# =====================================================================

MODEL_PATH = os.environ.get("LLAMA_MODEL_PATH")

if not MODEL_PATH:
    raise RuntimeError(
        "Set LLAMA_MODEL_PATH before running the benchmark."
    )


# ---------------------------------------------------------------------
# Llama configuration
# ---------------------------------------------------------------------
#
# n_ctx=8192 is required for nptel_medium.txt.
#
# nptel_medium.txt contains approximately 3,741 tokens.
#
# n_batch=64 was tested successfully with 1,000 incremental
# evaluations. n_batch=512 previously caused:
#
#     llama_decode returned 1
#
# Therefore keep this at 64.
# ---------------------------------------------------------------------

N_CTX = 8192
N_BATCH = 64
N_GPU_LAYERS = -1


# =====================================================================
# CORPUS
# =====================================================================

# benchmark_corpus.py:
#
# ai-backend/
# ├── app/
# │   └── lmcompress/
# │       └── benchmark_corpus.py
# │
# └── benchmarks/
#     ├── nptel_small.txt
#     └── nptel_medium.txt
#
# parents[2] resolves to ai-backend/.

CORPUS_DIR = (
    Path(__file__).resolve().parents[2] / "benchmarks"
)


# =====================================================================
# RESULT FORMATTING
# =====================================================================

def format_bytes(value: int) -> str:
    return f"{value:,}"


def format_float(
    value: float,
    digits: int = 6,
) -> str:
    return f"{value:.{digits}f}"


# =====================================================================
# BENCHMARK ONE FILE
# =====================================================================

def benchmark_file(
    compressor: LMCompressor,
    path: Path,
) -> dict:

    print()
    print("=" * 70)
    print(
        f"BENCHMARK: {path.name}"
    )
    print("=" * 70)

    # ---------------------------------------------------------------
    # Read original
    # ---------------------------------------------------------------

    original = path.read_bytes()

    print(
        f"Original bytes: "
        f"{format_bytes(len(original))}"
    )

    try:
        original_text = original.decode(
            "utf-8"
        )
    except UnicodeDecodeError as exc:
        raise RuntimeError(
            f"Corpus file is not valid UTF-8: "
            f"{path}"
        ) from exc

    # ---------------------------------------------------------------
    # Tokenization
    # ---------------------------------------------------------------

    tokens = compressor.tokenize(
        original_text
    )

    print(
        f"Tokens: "
        f"{format_bytes(len(tokens))}"
    )

    # ---------------------------------------------------------------
    # Compression
    # ---------------------------------------------------------------

    print()
    print("Starting compression...")

    compression_start = (
        time.perf_counter()
    )

    compressed_result = (
        compressor.compress(
            original_text
        )
    )

    compression_time = (
        time.perf_counter()
        - compression_start
    )

    compressed_bytes = (
        compressed_result.data
    )

    print(
        "Compression complete."
    )

    # ---------------------------------------------------------------
    # Decompression
    # ---------------------------------------------------------------

    print()
    print("Starting decompression...")

    decompression_start = (
        time.perf_counter()
    )

    recovered = compressor.decompress(
        compressed_bytes
    )

    decompression_time = (
        time.perf_counter()
        - decompression_start
    )

    print(
        "Decompression complete."
    )

    # ---------------------------------------------------------------
    # Recovered bytes
    # ---------------------------------------------------------------

    recovered_bytes = recovered.encode(
        "utf-8"
    )

    # ---------------------------------------------------------------
    # Statistics
    # ---------------------------------------------------------------

    original_size = len(
        original
    )

    compressed_size = len(
        compressed_bytes
    )

    token_count = len(
        tokens
    )

    if original_size > 0:

        compression_ratio = (
            compressed_size
            / original_size
        )

        size_reduction = (
            1.0
            - compression_ratio
        ) * 100.0

        bits_per_byte = (
            compressed_size
            * 8.0
            / original_size
        )

    else:

        compression_ratio = 0.0
        size_reduction = 0.0
        bits_per_byte = 0.0

    if token_count > 0:

        bits_per_token = (
            compressed_size
            * 8.0
            / token_count
        )

    else:

        bits_per_token = 0.0

    exact_match = (
        recovered_bytes
        == original
    )

    # ---------------------------------------------------------------
    # Print result
    # ---------------------------------------------------------------

    print()
    print(
        "Original bytes:       "
        f"{format_bytes(original_size)}"
    )

    print(
        "Compressed bytes:     "
        f"{format_bytes(compressed_size)}"
    )

    print(
        "Compression ratio:    "
        f"{format_float(compression_ratio)}"
    )

    print(
        "Size reduction:       "
        f"{size_reduction:.2f}%"
    )

    print(
        "Bits / byte:          "
        f"{bits_per_byte:.4f}"
    )

    print(
        "Bits / token:         "
        f"{bits_per_token:.4f}"
    )

    print(
        "Token count:          "
        f"{format_bytes(token_count)}"
    )

    print(
        "Compression time:     "
        f"{compression_time:.3f}s"
    )

    print(
        "Decompression time:   "
        f"{decompression_time:.3f}s"
    )

    print(
        "EXACT BYTE MATCH:     "
        f"{exact_match}"
    )

    # ---------------------------------------------------------------
    # Hard correctness check
    # ---------------------------------------------------------------

    if not exact_match:

        print()
        print(
            "ERROR: ROUND-TRIP FAILED"
        )

        print(
            "Original length:",
            len(original),
        )

        print(
            "Recovered length:",
            len(recovered_bytes),
        )

        # Find first differing byte.
        first_difference = None

        limit = min(
            len(original),
            len(recovered_bytes),
        )

        for index in range(limit):

            if (
                original[index]
                != recovered_bytes[index]
            ):
                first_difference = index
                break

        if first_difference is not None:

            print(
                "First differing byte:",
                first_difference,
            )

            print(
                "Original byte:",
                original[
                    first_difference
                ],
            )

            print(
                "Recovered byte:",
                recovered_bytes[
                    first_difference
                ],
            )

        raise RuntimeError(
            f"Round-trip failed for "
            f"{path.name}"
        )

    print(
        "ROUND-TRIP TEST PASSED"
    )

    # ---------------------------------------------------------------
    # Return structured result
    # ---------------------------------------------------------------

    return {
        "file": path.name,
        "original_bytes": original_size,
        "compressed_bytes": compressed_size,
        "compression_ratio": (
            compression_ratio
        ),
        "size_reduction_percent": (
            size_reduction
        ),
        "bits_per_byte": (
            bits_per_byte
        ),
        "bits_per_token": (
            bits_per_token
        ),
        "token_count": token_count,
        "compression_time": (
            compression_time
        ),
        "decompression_time": (
            decompression_time
        ),
        "exact_match": exact_match,
    }


# =====================================================================
# MAIN
# =====================================================================

def main() -> None:

    # ---------------------------------------------------------------
    # Model
    # ---------------------------------------------------------------

    print(
        "Loading Llama backend..."
    )

    backend = Llama32Backend(
        MODEL_PATH,
        n_ctx=N_CTX,
        n_batch=N_BATCH,
        n_gpu_layers=N_GPU_LAYERS,
    )

    print(
        "N_CTX:",
        backend.llm.n_ctx(),
    )

    print(
        "N_BATCH:",
        backend.llm.n_batch,
    )

    print(
        "VOCAB SIZE:",
        backend.vocab_size,
    )

    # ---------------------------------------------------------------
    # Compressor
    # ---------------------------------------------------------------

    compressor = LMCompressor(
        backend
    )

    # ---------------------------------------------------------------
    # Verify corpus directory
    # ---------------------------------------------------------------

    print()
    print(
        "CORPUS DIRECTORY:"
    )
    print(
        CORPUS_DIR
    )

    if not CORPUS_DIR.exists():

        raise FileNotFoundError(
            "Corpus directory does not exist: "
            f"{CORPUS_DIR}"
        )

    if not CORPUS_DIR.is_dir():

        raise RuntimeError(
            "Corpus path is not a directory: "
            f"{CORPUS_DIR}"
        )

    # ---------------------------------------------------------------
    # Find all TXT corpus files
    # ---------------------------------------------------------------

    corpus_files = sorted(
        CORPUS_DIR.glob("*.txt"),
        key=lambda path: (
            0
            if path.name == "nptel_small.txt"
            else (
                1
                if path.name == "nptel_medium.txt"
                else 2
            ),
            path.name,
        ),
    )

    if not corpus_files:

        raise RuntimeError(
            "No .txt corpus files found in: "
            f"{CORPUS_DIR}"
        )

    # ---------------------------------------------------------------
    # Print discovered corpus
    # ---------------------------------------------------------------

    print()
    print(
        "=" * 70
    )
    print(
        "CORPUS FILES"
    )
    print(
        "=" * 70
    )

    for index, path in enumerate(
        corpus_files,
        start=1,
    ):

        print(
            f"{index}. "
            f"{path.name} "
            f"("
            f"{path.stat().st_size:,}"
            f" bytes)"
        )

    print()
    print(
        "TOTAL CORPUS FILES:",
        len(corpus_files),
    )

    # ---------------------------------------------------------------
    # Run benchmarks
    # ---------------------------------------------------------------

    results: list[dict] = []

    for index, path in enumerate(
        corpus_files,
        start=1,
    ):

        print()
        print(
            "#" * 70
        )

        print(
            f"STARTING CORPUS "
            f"{index}/{len(corpus_files)}: "
            f"{path.name}"
        )

        print(
            "#" * 70
        )

        result = benchmark_file(
            compressor,
            path,
        )

        results.append(
            result
        )

    # ---------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------

    print()
    print(
        "=" * 70
    )
    print(
        "BENCHMARK SUMMARY"
    )
    print(
        "=" * 70
    )

    print()

    for result in results:

        print(
            result["file"]
        )

        print(
            f"  Original bytes:     "
            f"{result['original_bytes']:,}"
        )

        print(
            f"  Compressed bytes:   "
            f"{result['compressed_bytes']:,}"
        )

        print(
            f"  Compression ratio:  "
            f"{result['compression_ratio']:.6f}"
        )

        print(
            f"  Size reduction:     "
            f"{result['size_reduction_percent']:.2f}%"
        )

        print(
            f"  Bits / byte:        "
            f"{result['bits_per_byte']:.4f}"
        )

        print(
            f"  Bits / token:       "
            f"{result['bits_per_token']:.4f}"
        )

        print(
            f"  Tokens:             "
            f"{result['token_count']:,}"
        )

        print(
            f"  Compression time:   "
            f"{result['compression_time']:.3f}s"
        )

        print(
            f"  Decompression time: "
            f"{result['decompression_time']:.3f}s"
        )

        print(
            f"  Exact byte match:   "
            f"{result['exact_match']}"
        )

        print()

    # ---------------------------------------------------------------
    # Aggregate statistics
    # ---------------------------------------------------------------

    if results:

        total_original = sum(
            result["original_bytes"]
            for result in results
        )

        total_compressed = sum(
            result["compressed_bytes"]
            for result in results
        )

        total_tokens = sum(
            result["token_count"]
            for result in results
        )

        total_compression_time = sum(
            result["compression_time"]
            for result in results
        )

        total_decompression_time = sum(
            result["decompression_time"]
            for result in results
        )

        if total_original > 0:

            aggregate_ratio = (
                total_compressed
                / total_original
            )

            aggregate_reduction = (
                1.0
                - aggregate_ratio
            ) * 100.0

            aggregate_bits_per_byte = (
                total_compressed
                * 8.0
                / total_original
            )

        else:

            aggregate_ratio = 0.0
            aggregate_reduction = 0.0
            aggregate_bits_per_byte = 0.0

        if total_tokens > 0:

            aggregate_bits_per_token = (
                total_compressed
                * 8.0
                / total_tokens
            )

        else:

            aggregate_bits_per_token = 0.0

        all_exact = all(
            result["exact_match"]
            for result in results
        )

        print(
            "=" * 70
        )

        print(
            "AGGREGATE"
        )

        print(
            "=" * 70
        )

        print(
            f"Total original bytes:     "
            f"{total_original:,}"
        )

        print(
            f"Total compressed bytes:   "
            f"{total_compressed:,}"
        )

        print(
            f"Aggregate ratio:          "
            f"{aggregate_ratio:.6f}"
        )

        print(
            f"Aggregate reduction:      "
            f"{aggregate_reduction:.2f}%"
        )

        print(
            f"Aggregate bits / byte:    "
            f"{aggregate_bits_per_byte:.4f}"
        )

        print(
            f"Aggregate bits / token:   "
            f"{aggregate_bits_per_token:.4f}"
        )

        print(
            f"Total tokens:              "
            f"{total_tokens:,}"
        )

        print(
            f"Total compression time:   "
            f"{total_compression_time:.3f}s"
        )

        print(
            f"Total decompression time: "
            f"{total_decompression_time:.3f}s"
        )

        print(
            f"ALL EXACT BYTE MATCH:      "
            f"{all_exact}"
        )

    # ---------------------------------------------------------------
    # Final status
    # ---------------------------------------------------------------

    print()
    print(
        "=" * 70
    )

    if all_exact:
        print(
            "ALL BENCHMARKS PASSED"
        )
    else:
        print(
            "BENCHMARK FAILURE"
        )

    print(
        "=" * 70
    )


# =====================================================================
# ENTRY POINT
# =====================================================================

if __name__ == "__main__":
    main()