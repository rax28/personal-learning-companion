from __future__ import annotations

from dataclasses import dataclass

from transformers import GPT2Config

# The supplied source imports PATCH_SIZE and PATCH_SAMPLING_BATCH_SIZE from
# data.model.bgpt.config, but that config file was not included in the PDF.
# Keep the values explicit and overridable rather than inventing a hidden
# checkpoint-specific configuration.
PATCH_SIZE = 16
PATCH_SAMPLING_BATCH_SIZE = 0


@dataclass
class BGPTConfig:
    """Project-level configuration for the recovered bGPT implementation.

    GPT-2 configs are accepted directly by the model classes. This helper is
    only for constructing a compatible config when no Code Ocean config file
    or checkpoint metadata is available.
    """

    patch_size: int = PATCH_SIZE
    patch_sampling_batch_size: int = PATCH_SAMPLING_BATCH_SIZE

    @staticmethod
    def gpt2(**kwargs) -> GPT2Config:
        return GPT2Config(**kwargs)
