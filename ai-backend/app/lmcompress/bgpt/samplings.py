from __future__ import annotations

import numpy as np


def top_k_sampling(probs, top_k: int = 0, return_probs: bool = False):
    """Apply top-k filtering to a probability vector."""
    p = np.asarray(probs, dtype=np.float64).copy()
    if top_k and top_k > 0 and top_k < p.size:
        idx = np.argpartition(p, -top_k)[:-top_k]
        p[idx] = 0.0
    total = p.sum()
    if total > 0:
        p /= total
    return p if return_probs else int(np.random.choice(len(p), p=p))


def top_p_sampling(probs, top_p: float = 1.0, return_probs: bool = False):
    """Apply nucleus/top-p filtering to a probability vector."""
    p = np.asarray(probs, dtype=np.float64).copy()
    if top_p < 1.0:
        order = np.argsort(p)[::-1]
        cumulative = np.cumsum(p[order])
        remove = cumulative > top_p
        if remove.any():
            # Keep the first token that crosses the threshold.
            remove[0] = False
            if len(remove) > 1:
                remove[1:] &= cumulative[:-1] >= top_p
            p[order[remove]] = 0.0
    total = p.sum()
    if total > 0:
        p /= total
    return p if return_probs else int(np.random.choice(len(p), p=p))


def temperature_sampling(probs, temperature: float = 1.0):
    """Sample from probabilities after temperature adjustment."""
    p = np.asarray(probs, dtype=np.float64)
    if temperature <= 0:
        return int(np.argmax(p))
    logits = np.log(np.clip(p, 1e-40, None)) / temperature
    logits -= logits.max()
    q = np.exp(logits)
    q /= q.sum()
    return int(np.random.choice(len(q), p=q))
