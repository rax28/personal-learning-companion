from __future__ import annotations

import math
import os
from pathlib import Path

import numpy as np
from llama_cpp import Llama


class Llama32Backend:
    """
    Persistent incremental Llama backend.

    The model is loaded once and the KV/cache context is reused.

    Designed for LM-guided arithmetic compression:

        token
          ↓
        Llama prediction
          ↓
        probability distribution
          ↓
        arithmetic coding
          ↓
        next token
          ↓
        repeat
    """

    def __init__(
        self,
        model_path: str,
        *,
        n_ctx: int = 8192,
        n_gpu_layers: int = -1,
        n_batch: int = 64,
        flash_attn=False,
    ) -> None:

        path = Path(model_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Model file does not exist: {path}"
            )

        self.model_path = str(path)
        self.n_ctx = int(n_ctx)
        self.n_gpu_layers = int(n_gpu_layers)
        self.n_batch = int(n_batch)

        self.llm = Llama(
            model_path=self.model_path,
            n_ctx=self.n_ctx,
            n_batch=self.n_batch,
            n_gpu_layers=self.n_gpu_layers,
            logits_all=True,
            verbose=True    ,
            flash_attn=flash_attn,
        )

        self.vocab_size = int(
            self.llm.n_vocab()
        )

        self._tokens: list[int] = []

    # ================================================================
    # CONTEXT MANAGEMENT
    # ================================================================

    def reset(self) -> None:
        """
        Reset the llama context and token history.
        """

        self.llm.reset()
        self._tokens = []

    @property
    def tokens(self) -> list[int]:
        """
        Return a copy of the currently evaluated token sequence.
        """

        return list(self._tokens)

    def current_tokens(self) -> list[int]:
        """
        Compatibility method used by compressor.py.
        """

        return list(self._tokens)

    # ================================================================
    # INTERNAL LOGITS
    # ================================================================

    def _get_last_logits(self) -> np.ndarray:
        """
        Return only the latest logits row.

        This avoids copying the entire logits matrix on every token.
        """

        scores = self.llm._scores

        if scores is None:
            raise RuntimeError(
                "Llama returned no logits."
            )

        scores = np.asarray(scores)

        if scores.ndim == 1:

            logits = scores

        elif scores.ndim == 2:

            if scores.shape[0] == 0:
                raise RuntimeError(
                    "Llama returned zero logit rows."
                )

            logits = scores[-1]

        else:

            raise RuntimeError(
                f"Unexpected logits shape: {scores.shape}"
            )

        logits = np.asarray(
            logits,
            dtype=np.float32,
        )

        if logits.shape != (self.vocab_size,):
            raise RuntimeError(
                "Unexpected vocabulary size: "
                f"{logits.shape} != "
                f"({self.vocab_size},)"
            )

        return logits.copy()

    # ================================================================
    # INCREMENTAL EVALUATION
    # ================================================================

    def start_context(
        self,
        token: int,
    ) -> np.ndarray:
        """
        Start a new context with one token.

        Returns logits predicting the NEXT token.
        """

        self.reset()

        token = int(token)

        self.llm.eval([token])

        self._tokens.append(token)

        return self._get_last_logits()

    def evaluate_first(
        self,
        token: int,
    ) -> np.ndarray:
        """
        Compatibility alias for start_context().
        """

        return self.start_context(token)

    def append_token(
        self,
        token: int,
    ) -> np.ndarray:
        """
        Compatibility alias used by compressor.py.

        Append one token and return logits predicting
        the NEXT token.
        """

        return self.evaluate_next(token)

    def evaluate_next(
        self,
        token: int,
    ) -> np.ndarray:
        """
        Append one token to the current context.

        Returns logits predicting the NEXT token.
        """

        token = int(token)

        if not self._tokens:
            return self.start_context(token)

        if len(self._tokens) >= self.n_ctx:
            raise RuntimeError(
                "Llama context window exhausted: "
                f"{len(self._tokens)} >= {self.n_ctx}. "
                "A longer n_ctx is required for this sequence."
            )

        self.llm.eval([token])

        self._tokens.append(token)

        return self._get_last_logits()

    # ================================================================
    # TOKENIZATION
    # ================================================================

    def tokenize(
        self,
        data: bytes,
    ) -> list[int]:
        """
        Convert UTF-8 bytes into Llama token IDs.
        """

        return [
            int(token)
            for token in self.llm.tokenize(data)
        ]

    def detokenize(
        self,
        tokens: list[int],
    ) -> bytes:
        """
        Convert token IDs back into UTF-8 bytes.
        """

        return self.llm.detokenize(
            [
                int(token)
                for token in tokens
            ]
        )

    # ================================================================
    # FULL SEQUENCE EVALUATION
    # ================================================================

    def evaluate_sequence(
        self,
        tokens: list[int],
    ) -> np.ndarray:
        """
        Evaluate an entire sequence at once.

        Primarily intended for diagnostics/statistics.

        Compression should use:

            start_context()
            evaluate_next()
            evaluate_next()
            ...
        """

        if not tokens:
            raise ValueError(
                "Cannot evaluate an empty token sequence."
            )

        clean_tokens = [
            int(token)
            for token in tokens
        ]

        if len(clean_tokens) > self.n_ctx:
            raise ValueError(
                "Sequence exceeds Llama context window: "
                f"{len(clean_tokens)} > {self.n_ctx}"
            )

        self.reset()

        self.llm.eval(clean_tokens)

        self._tokens.extend(clean_tokens)

        scores = np.asarray(
            self.llm._scores,
            dtype=np.float32,
        )

        if scores.ndim != 2:
            raise RuntimeError(
                f"Unexpected full logits shape: {scores.shape}"
            )

        if scores.shape[0] != len(clean_tokens):
            raise RuntimeError(
                "Unexpected number of logits rows: "
                f"{scores.shape[0]} != "
                f"{len(clean_tokens)}"
            )

        if scores.shape[1] != self.vocab_size:
            raise RuntimeError(
                "Unexpected vocabulary size: "
                f"{scores.shape[1]} != "
                f"{self.vocab_size}"
            )

        return scores.copy()

    # ================================================================
    # SOFTMAX
    # ================================================================

    @staticmethod
    def softmax(
        logits: np.ndarray,
    ) -> np.ndarray:
        """
        Convert logits into a probability distribution.
        """

        logits = np.asarray(
            logits,
            dtype=np.float64,
        )

        shifted = (
            logits
            - np.max(logits)
        )

        probabilities = np.exp(
            shifted
        )

        total = probabilities.sum()

        if not np.isfinite(total) or total <= 0:
            raise RuntimeError(
                "Invalid probability normalization."
            )

        probabilities /= total

        return probabilities

    # ================================================================
    # TOKEN BITS
    # ================================================================

    def token_bits(
        self,
        tokens: list[int],
    ) -> list[float]:
        """
        Calculate ideal LM coding cost for every predicted token.
        """

        if len(tokens) < 2:
            return []

        scores = self.evaluate_sequence(tokens)

        result: list[float] = []

        for position in range(
            len(tokens) - 1
        ):

            probabilities = self.softmax(
                scores[position]
            )

            target = int(
                tokens[position + 1]
            )

            probability = float(
                probabilities[target]
            )

            bits = -math.log2(
                max(
                    probability,
                    1e-300,
                )
            )

            result.append(bits)

        return result

    def total_bits(
        self,
        tokens: list[int],
    ) -> float:
        """
        Total ideal arithmetic coding cost.
        """

        return sum(
            self.token_bits(tokens)
        )

    # ================================================================
    # DIAGNOSTICS
    # ================================================================

    def compare_incremental_to_full(
        self,
        tokens: list[int],
    ) -> dict:
        """
        Compare incremental and full-context logits.

        Raw logits do not necessarily have to be bit-for-bit identical.
        We also compare probabilities and the highest-probability token.
        """

        if len(tokens) < 2:
            raise ValueError(
                "Need at least two tokens."
            )

        clean_tokens = [
            int(token)
            for token in tokens
        ]

        # ------------------------------------------------------------
        # Full evaluation
        # ------------------------------------------------------------

        full_scores = self.evaluate_sequence(
            clean_tokens
        )

        # Prediction for the final token.
        full_logits = np.asarray(
            full_scores[-2],
            dtype=np.float64,
        )

        # ------------------------------------------------------------
        # Incremental evaluation
        # ------------------------------------------------------------

        incremental_logits = self.start_context(
            clean_tokens[0]
        )

        for token in clean_tokens[1:-1]:

            incremental_logits = (
                self.evaluate_next(token)
            )

        incremental_logits = np.asarray(
            incremental_logits,
            dtype=np.float64,
        )

        # ------------------------------------------------------------
        # Raw logits
        # ------------------------------------------------------------

        difference = np.abs(
            incremental_logits
            - full_logits
        )

        max_logit_difference = float(
            difference.max()
        )

        mean_logit_difference = float(
            difference.mean()
        )

        # ------------------------------------------------------------
        # Probabilities
        # ------------------------------------------------------------

        full_probabilities = self.softmax(
            full_logits
        )

        incremental_probabilities = self.softmax(
            incremental_logits
        )

        probability_difference = np.abs(
            incremental_probabilities
            - full_probabilities
        )

        max_probability_difference = float(
            probability_difference.max()
        )

        # ------------------------------------------------------------
        # Top token comparison
        # ------------------------------------------------------------

        full_top = int(
            np.argmax(
                full_probabilities
            )
        )

        incremental_top = int(
            np.argmax(
                incremental_probabilities
            )
        )

        # ------------------------------------------------------------
        # Probability comparison
        # ------------------------------------------------------------

        probabilities_close = bool(
            np.allclose(
                incremental_probabilities,
                full_probabilities,
                rtol=1e-5,
                atol=1e-7,
            )
        )

        return {
            "tokens": clean_tokens,
            "vocab_size": self.vocab_size,
            "max_logit_difference": (
                max_logit_difference
            ),
            "mean_logit_difference": (
                mean_logit_difference
            ),
            "max_probability_difference": (
                max_probability_difference
            ),
            "full_top_token": full_top,
            "incremental_top_token": (
                incremental_top
            ),
            "top_token_match": (
                full_top
                == incremental_top
            ),
            "probabilities_close": (
                probabilities_close
            ),
        }


# ====================================================================
# STANDALONE TEST
# ====================================================================

if __name__ == "__main__":

    MODEL = os.environ.get(
        "LLAMA_MODEL_PATH"
    )

    if not MODEL:
        raise RuntimeError(
            "Set LLAMA_MODEL_PATH before running "
            "this module."
        )

    backend = Llama32Backend(
        MODEL,
        n_ctx=8192,
        n_gpu_layers=-1,
        n_batch=64,
    )

    text = (
        b"The capital of France is Paris."
    )

    tokens = backend.tokenize(text)

    print(
        "TOKENS:",
        tokens,
    )

    print(
        "TOKEN COUNT:",
        len(tokens),
    )

    print(
        "N_CTX:",
        backend.n_ctx,
    )

    print(
        "N_BATCH:",
        backend.n_batch,
    )

    print(
        "VOCAB SIZE:",
        backend.vocab_size,
    )

    # ------------------------------------------------------------
    # Incremental evaluation
    # ------------------------------------------------------------

    logits = backend.start_context(
        tokens[0]
    )

    print(
        "INITIAL LOGITS:",
        logits.shape,
    )

    for token in tokens[1:]:

        logits = backend.evaluate_next(
            token
        )

    print(
        "FINAL LOGITS:",
        logits.shape,
    )

    print(
        "INCREMENTAL TOKENS:",
        backend.tokens,
    )

    print(
        "TOKENS MATCH:",
        backend.tokens == tokens,
    )

    if backend.tokens != tokens:
        raise RuntimeError(
            "Incremental token sequence mismatch."
        )

    if logits.shape != (
        backend.vocab_size,
    ):
        raise RuntimeError(
            "Unexpected final logits shape."
        )

    print(
        "INCREMENTAL EVALUATION WORKS"
    )

    # ------------------------------------------------------------
    # Compare incremental vs full
    # ------------------------------------------------------------

    comparison = (
        backend.compare_incremental_to_full(
            tokens
        )
    )

    print()
    print(
        "FULL VS INCREMENTAL"
    )

    print(
        "MAX LOGIT DIFFERENCE:",
        comparison[
            "max_logit_difference"
        ],
    )

    print(
        "MEAN LOGIT DIFFERENCE:",
        comparison[
            "mean_logit_difference"
        ],
    )

    print(
        "MAX PROBABILITY DIFFERENCE:",
        comparison[
            "max_probability_difference"
        ],
    )

    print(
        "FULL TOP TOKEN:",
        comparison[
            "full_top_token"
        ],
    )

    print(
        "INCREMENTAL TOP TOKEN:",
        comparison[
            "incremental_top_token"
        ],
    )

    print(
        "TOP TOKEN MATCH:",
        comparison[
            "top_token_match"
        ],
    )

    print(
        "PROBABILITIES CLOSE:",
        comparison[
            "probabilities_close"
        ],
    )

    print()
    print(
        "BACKEND TEST COMPLETE"
    )