from __future__ import annotations

"""Optional adapter for the recovered Code Ocean bGPT implementation.

This module deliberately does not replace the existing tutor/model-response
path. A trained bGPT checkpoint and the missing Code Ocean configuration/data
artifacts are required before it can be used as a production compressor.
"""

from pathlib import Path


def checkpoint_available(path: str | None = None) -> bool:
    if not path:
        return False
    p = Path(path)
    return p.exists() and (p.is_file() or p.is_dir())


def integration_status(checkpoint: str | None = None) -> dict:
    return {
        "implementation": "recovered-code-ocean-bgpt",
        "checkpoint_available": checkpoint_available(checkpoint),
        "production_codec_enabled": False,
        "note": (
            "Core bGPT model code is integrated from the supplied source. "
            "The supplied PDF did not include the original config/checkpoint "
            "and therefore this package does not claim to reproduce a trained "
            "Code Ocean compression run."
        ),
    }
