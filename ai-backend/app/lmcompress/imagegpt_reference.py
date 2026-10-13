from __future__ import annotations

"""Optional ImageGPT arithmetic-coding integration based on the supplied source.

This module keeps the research implementation separate from the companion's
normal lossless archive path. A compatible ImageGPT checkpoint is required.
The codec is deliberately token-stream based: the exact tokenization used by
the encoder must also be available to the decoder.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .neural import EncodedSequence, decode_tokens, encode_tokens


@dataclass
class ImageGPTBundle:
    model: Any
    processor: Any
    device: Any


def load_imagegpt(checkpoint: str, device=None) -> ImageGPTBundle:
    import torch
    from transformers import ImageGPTForCausalImageModeling, ImageGPTImageProcessor

    path = Path(checkpoint)
    if not path.exists():
        raise FileNotFoundError(f"ImageGPT checkpoint not found: {path}")
    model = ImageGPTForCausalImageModeling.from_pretrained(str(path))
    processor = ImageGPTImageProcessor.from_pretrained(str(path))
    device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device).eval()
    return ImageGPTBundle(model, processor, device)


def image_to_tokens(bundle: ImageGPTBundle, image: np.ndarray) -> list[int]:
    import torch
    from PIL import Image

    if image.ndim != 3:
        raise ValueError("image must have shape HxWxC")
    encoded = bundle.processor(Image.fromarray(image), return_tensors="pt")["input_ids"]
    return encoded.reshape(-1).to(torch.long).cpu().tolist()


def token_predictor(bundle: ImageGPTBundle):
    import torch

    vocab = int(bundle.model.config.vocab_size)

    def predict(context):
        ids = torch.tensor([list(context) or [0]], dtype=torch.long, device=bundle.device)
        with torch.no_grad():
            logits = bundle.model(input_ids=ids).logits[0, -1]
        return torch.softmax(logits.float(), dim=-1).cpu().numpy()

    return predict, vocab


def compress_image_tokens(bundle: ImageGPTBundle, tokens: list[int]) -> EncodedSequence:
    predict, vocab = token_predictor(bundle)
    return encode_tokens(tokens, predict, vocab)


def decompress_image_tokens(bundle: ImageGPTBundle, encoded: EncodedSequence) -> list[int]:
    predict, _ = token_predictor(bundle)
    return decode_tokens(encoded, predict)
