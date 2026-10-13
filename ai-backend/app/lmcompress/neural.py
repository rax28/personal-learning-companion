from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np

from .arithmetic_coder import ArithmeticDecoder, ArithmeticEncoder, probabilities_to_cumulative


Predictor = Callable[[Sequence[int]], np.ndarray]


@dataclass
class EncodedSequence:
    payload: bytes
    padded_bits: int
    length: int
    vocabulary_size: int


def _validate_pdf(pdf: np.ndarray, vocab_size: int) -> np.ndarray:
    pdf = np.asarray(pdf, dtype=np.float64).reshape(-1)
    if len(pdf) != vocab_size:
        raise ValueError(f"predictor returned {len(pdf)} probabilities, expected {vocab_size}")
    pdf = np.nan_to_num(pdf, nan=0.0, posinf=0.0, neginf=0.0)
    pdf = np.maximum(pdf, 0.0)
    if float(pdf.sum()) <= 0:
        pdf.fill(1.0 / vocab_size)
    return pdf / pdf.sum()


def encode_tokens(tokens: Sequence[int], predict: Predictor, vocab_size: int) -> EncodedSequence:
    tokens = [int(x) for x in tokens]
    if any(x < 0 or x >= vocab_size for x in tokens):
        raise ValueError("token outside predictor vocabulary")
    encoder = ArithmeticEncoder()
    context: list[int] = []
    for token in tokens:
        pdf = _validate_pdf(predict(context), vocab_size)
        cdf = probabilities_to_cumulative(pdf)
        encoder.encode(cdf[token], cdf[token + 1], cdf[-1])
        context.append(token)
    payload, padded = encoder.finish()
    return EncodedSequence(payload, padded, len(tokens), vocab_size)


def decode_tokens(encoded: EncodedSequence, predict: Predictor) -> list[int]:
    decoder = ArithmeticDecoder(encoded.payload, encoded.padded_bits)
    context: list[int] = []
    for _ in range(encoded.length):
        pdf = _validate_pdf(predict(context), encoded.vocabulary_size)
        cdf = probabilities_to_cumulative(pdf)
        token = decoder.decode(cdf)
        context.append(token)
    return context


def hf_causal_predictor(model, device=None) -> tuple[Predictor, int]:
    """Create a predictor from a Hugging Face causal LM.

    The predictor intentionally recomputes the prefix each step. This is slower
    than KV-cache inference, but guarantees that the decoder uses the same
    deterministic context construction as the encoder.
    """
    import torch

    device = device or next(model.parameters()).device
    vocab_size = int(model.config.vocab_size)

    def predict(context: Sequence[int]) -> np.ndarray:
        ids = torch.tensor([list(context) or [0]], dtype=torch.long, device=device)
        with torch.no_grad():
            logits = model(input_ids=ids).logits[0, -1]
        return torch.softmax(logits.float(), dim=-1).cpu().numpy()

    return predict, vocab_size
