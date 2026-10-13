# LMCompress integration

The companion now contains the remaining LMCompress material supplied in the project conversation as an isolated `ai-backend/app/lmcompress` package.

## Included

- Recovered hierarchical bGPT model (`bgpt/model.py`).
- Deterministic integer arithmetic coder (`arithmetic_coder.py`).
- Generic autoregressive neural token codec (`neural.py`) with exact encoder/decoder context symmetry.
- Optional ImageGPT adapter (`imagegpt_reference.py`).
- Classical text and audio benchmark runners (`benchmarks.py`).
- Existing companion compression API remains byte-exact and continues to use its safe archive fallback unless a compatible neural checkpoint is explicitly configured.

## Important distinction

The supplied Code Ocean snippets reference trained checkpoints, configuration/data files, and a project-specific arithmetic-coder implementation that were not all supplied. The package therefore does **not** claim that the bundled MVP reproduces the original paper/Code Ocean compression numbers.

For a real neural arithmetic-coded archive, the encoder and decoder must share the same tokenizer, model weights, preprocessing, vocabulary, probability quantization, symbol order, and initial context. The included generic codec enforces that symmetry and is covered by tests.

## bGPT

The bGPT classes are retained under:

`ai-backend/app/lmcompress/bgpt/`

The recovered model is available to downstream code but is not automatically loaded by the companion because a trained checkpoint is required.

## Classical baselines

`benchmarks.py` provides the text/audio comparisons represented by the supplied script. External binaries such as `zpaq`, `7zz`, `zstd`, `ppmd`, `ffmpeg`, `ofr`, and `wavpack` must be installed separately when those benchmarks are run.
