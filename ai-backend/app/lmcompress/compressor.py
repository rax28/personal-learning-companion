from __future__ import annotations

import os
import struct
from dataclasses import dataclass

from .arithmetic_coder import (
    ArithmeticDecoder,
    ArithmeticEncoder,
    probabilities_to_cumulative,
)
from .llama_backend import Llama32Backend


MAGIC = b"LMC1"

# 4s  = magic
# B   = arithmetic precision
# Q   = token count
# I   = first token
# I   = padded bits
HEADER_FORMAT = ">4sBQII"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


@dataclass
class CompressionResult:
    data: bytes
    original_tokens: int
    compressed_bytes: int


class LMCompressor:
    """
    Llama-guided arithmetic compressor.

    Compression:

        text
          ↓
        tokens
          ↓
        first token stored literally
          ↓
        Llama predicts next token
          ↓
        probability distribution → CDF
          ↓
        arithmetic encode token
          ↓
        append token to persistent Llama context
          ↓
        repeat

    Decompression performs the exact same model operations on the
    reconstructed token prefix.
    """

    def __init__(
        self,
        backend: Llama32Backend,
        *,
        precision: int = 32,
        cdf_total: int = 1 << 24,
    ) -> None:
        self.backend = backend
        self.precision = precision
        self.cdf_total = cdf_total

    # ================================================================
    # TOKENIZATION
    # ================================================================

    def tokenize(self, text: str) -> list[int]:
        return self.backend.tokenize(
            text.encode("utf-8")
        )

    def detokenize(self, tokens: list[int]) -> str:
        data = self.backend.detokenize(tokens)
        return data.decode("utf-8", errors="strict")

    # ================================================================
    # MODEL PROBABILITIES
    # ================================================================

    def _probabilities_to_cdf(self, logits):
        probabilities = self.backend.softmax(logits)

        return probabilities_to_cumulative(
            probabilities,
            total=self.cdf_total,
        )

    # ================================================================
    # COMPRESSION
    # ================================================================

    def compress(self, text: str) -> CompressionResult:
        """
        Compress text using persistent incremental Llama evaluation.
        """

        tokens = self.tokenize(text)

        if not tokens:
            raise ValueError(
                "Tokenizer produced no tokens."
            )

        first_token = int(tokens[0])

        encoder = ArithmeticEncoder(
            precision=self.precision,
        )

        # Start Llama context with first token.
        logits = self.backend.start_context(
            first_token
        )

        for position in range(1, len(tokens)):
            target = int(tokens[position])

            if target < 0 or target >= self.backend.vocab_size:
                raise ValueError(
                    f"Token {target} is outside model vocabulary "
                    f"0..{self.backend.vocab_size - 1}"
                )

            cumulative = self._probabilities_to_cdf(
                logits
            )

            encoder.encode(
                cumulative_low=cumulative[target],
                cumulative_high=cumulative[target + 1],
                total=cumulative[-1],
            )

            # IMPORTANT:
            # Only after encoding the current token do we append it
            # to the model context. The returned logits predict the
            # following token.
            logits = self.backend.evaluate_next(
                target
            )

        payload, padded_bits = encoder.finish()

        header = struct.pack(
            HEADER_FORMAT,
            MAGIC,
            self.precision,
            len(tokens),
            first_token,
            padded_bits,
        )

        compressed = header + payload

        return CompressionResult(
            data=compressed,
            original_tokens=len(tokens),
            compressed_bytes=len(compressed),
        )

    # ================================================================
    # DECOMPRESSION
    # ================================================================

    def decompress(self, data: bytes) -> str:
        """
        Decompress an LM-compressed stream.

        The decoder reconstructs the exact token sequence by running
        the same incremental Llama predictions used by compression.
        """

        if len(data) < HEADER_SIZE:
            raise ValueError(
                "Compressed data is too short."
            )

        (
            magic,
            precision,
            token_count,
            first_token,
            padded_bits,
        ) = struct.unpack(
            HEADER_FORMAT,
            data[:HEADER_SIZE],
        )

        if magic != MAGIC:
            raise ValueError(
                f"Invalid LMCompress magic: {magic!r}"
            )

        if precision < 16 or precision > 62:
            raise ValueError(
                f"Unsupported arithmetic precision: {precision}"
            )

        if token_count <= 0:
            raise ValueError(
                f"Invalid token count: {token_count}"
            )

        payload = data[HEADER_SIZE:]

        if not payload:
            raise ValueError(
                "Compressed payload is empty."
            )

        if padded_bits < 0 or padded_bits > 7:
            raise ValueError(
                f"Invalid padded bit count: {padded_bits}"
            )

        decoder = ArithmeticDecoder(
            data=payload,
            padded_bits=padded_bits,
            precision=precision,
        )

        tokens = [int(first_token)]

        # The first token establishes the model context.
        logits = self.backend.start_context(
            first_token
        )

        for _ in range(1, token_count):
            cumulative = self._probabilities_to_cdf(
                logits
            )

            total = cumulative[-1]

            symbol = decoder.decode(
                cumulative
            )

            if symbol < 0 or symbol >= self.backend.vocab_size:
                raise RuntimeError(
                    f"Decoder produced invalid token: {symbol}"
                )

            tokens.append(int(symbol))

            # Reconstructed token becomes the next model context.
            logits = self.backend.evaluate_next(
                int(symbol)
            )

        return self.detokenize(tokens)


# ====================================================================
# STANDALONE ROUND-TRIP TEST
# ====================================================================

if __name__ == "__main__":

    MODEL = os.environ.get(
        "LLAMA_MODEL_PATH"
    )

    if not MODEL:
        raise RuntimeError(
            "Set LLAMA_MODEL_PATH before running this module."
        )

    backend = Llama32Backend(
        MODEL,
        n_ctx=8192,
        n_gpu_layers=-1,
    )

    compressor = LMCompressor(
        backend,
        precision=32,
        cdf_total=1 << 24,
    )

    text = "The capital of France is Paris."

    # --------------------------------------------------------------
    # Tokenization
    # --------------------------------------------------------------

    tokens = compressor.tokenize(text)

    print(
        "TOKENS:",
        tokens,
    )

    print(
        "TOKEN COUNT:",
        len(tokens),
    )

    # --------------------------------------------------------------
    # Compression
    # --------------------------------------------------------------

    result = compressor.compress(
        text
    )

    print(
        "ORIGINAL BYTES:",
        len(text.encode("utf-8")),
    )

    print(
        "COMPRESSED BYTES:",
        result.compressed_bytes,
    )

    if len(text.encode("utf-8")) > 0:
        bits_per_byte = (
            result.compressed_bytes * 8
            / len(text.encode("utf-8"))
        )

        print(
            "BITS / UTF-8 BYTE:",
            bits_per_byte,
        )

    # --------------------------------------------------------------
    # Decompression
    # --------------------------------------------------------------

    recovered = compressor.decompress(
        result.data
    )

    print(
        "RECOVERED:",
        repr(recovered),
    )

    print(
        "EXACT MATCH:",
        recovered == text,
    )

    # --------------------------------------------------------------
    # Final assertion
    # --------------------------------------------------------------

    if recovered != text:
        raise RuntimeError(
            "Round-trip compression/decompression failed."
        )

    print(
        "ROUND-TRIP TEST PASSED"
    )