from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BitWriter:
    data: bytearray
    current: int = 0
    used: int = 0

    def write(self, bit: int) -> None:
        self.current = (self.current << 1) | (bit & 1)
        self.used += 1
        if self.used == 8:
            self.data.append(self.current)
            self.current = 0
            self.used = 0

    def finish(self) -> tuple[bytes, int]:
        padded = 0
        if self.used:
            padded = 8 - self.used
            self.data.append(self.current << padded)
        return bytes(self.data), padded


class BitReader:
    def __init__(self, data: bytes, padded_bits: int = 0):
        if not 0 <= padded_bits < 8:
            raise ValueError("padded_bits must be in [0, 7]")
        self.bits = []
        total = len(data) * 8 - padded_bits
        for i in range(total):
            self.bits.append((data[i // 8] >> (7 - i % 8)) & 1)
        self.pos = 0

    def read(self) -> int:
        if self.pos >= len(self.bits):
            return 0
        bit = self.bits[self.pos]
        self.pos += 1
        return bit


class ArithmeticEncoder:
    """Small integer arithmetic/range encoder for deterministic experiments."""

    def __init__(self, precision: int = 32):
        if precision < 16 or precision > 62:
            raise ValueError("precision must be between 16 and 62")
        self.precision = precision
        self.low = 0
        self.high = (1 << precision) - 1
        self.pending = 0
        self.writer = BitWriter(bytearray())

    def _emit(self, bit: int) -> None:
        self.writer.write(bit)
        other = 1 - bit
        for _ in range(self.pending):
            self.writer.write(other)
        self.pending = 0

    def encode(self, cumulative_low: int, cumulative_high: int, total: int) -> None:
        if not 0 <= cumulative_low < cumulative_high <= total:
            raise ValueError("invalid cumulative interval")
        rng = self.high - self.low + 1
        self.high = self.low + (rng * cumulative_high // total) - 1
        self.low = self.low + (rng * cumulative_low // total)
        half = 1 << (self.precision - 1)
        quarter = 1 << (self.precision - 2)
        while True:
            if self.high < half:
                self._emit(0)
            elif self.low >= half:
                self._emit(1)
                self.low -= half
                self.high -= half
            elif self.low >= quarter and self.high < 3 * quarter:
                self.pending += 1
                self.low -= quarter
                self.high -= quarter
            else:
                break
            self.low <<= 1
            self.high = (self.high << 1) | 1

    def finish(self) -> tuple[bytes, int]:
        self.pending += 1
        if self.low < (1 << (self.precision - 2)):
            self._emit(0)
        else:
            self._emit(1)
        return self.writer.finish()


class ArithmeticDecoder:
    def __init__(self, data: bytes, padded_bits: int = 0, precision: int = 32):
        self.precision = precision
        self.reader = BitReader(data, padded_bits)
        self.low = 0
        self.high = (1 << precision) - 1
        self.code = 0
        for _ in range(precision):
            self.code = (self.code << 1) | self.reader.read()

    def decode(self, cumulative: list[int]) -> int:
        total = cumulative[-1]
        rng = self.high - self.low + 1
        value = ((self.code - self.low + 1) * total - 1) // rng
        lo, hi = 0, len(cumulative) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if cumulative[mid + 1] <= value:
                lo = mid + 1
            else:
                hi = mid
        symbol = lo
        self.high = self.low + (rng * cumulative[symbol + 1] // total) - 1
        self.low = self.low + (rng * cumulative[symbol] // total)
        half = 1 << (self.precision - 1)
        quarter = 1 << (self.precision - 2)
        while True:
            if self.high < half:
                pass
            elif self.low >= half:
                self.low -= half
                self.high -= half
                self.code -= half
            elif self.low >= quarter and self.high < 3 * quarter:
                self.low -= quarter
                self.high -= quarter
                self.code -= quarter
            else:
                break
            self.low <<= 1
            self.high = (self.high << 1) | 1
            self.code = (self.code << 1) | self.reader.read()
        return symbol

def probabilities_to_cumulative(
    probabilities,
    total: int = 1 << 24,
) -> list[int]:
    """
    Convert a floating-point PDF into a strictly increasing integer CDF.

    Optimized version:
    - avoids full np.argsort()
    - uses np.argpartition() when extra counts must be distributed
    - preserves the existing frequency construction
    - preserves deterministic output
    """

    import numpy as np

    p = np.asarray(
        probabilities,
        dtype=np.float64,
    )

    if p.ndim != 1 or len(p) == 0:
        raise ValueError(
            "probabilities must be a non-empty 1-D array"
        )

    vocab_size = len(p)

    p = np.nan_to_num(
        p,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    p = np.maximum(
        p,
        0.0,
    )

    s = float(p.sum())

    if s <= 0:
        p = np.full(
            vocab_size,
            1.0 / vocab_size,
            dtype=np.float64,
        )
    else:
        p = p / s

    # --------------------------------------------------------------
    # Initial frequency allocation
    # --------------------------------------------------------------

    available = total - vocab_size

    counts = (
        np.floor(
            p * available
        ).astype(np.int64)
        + 1
    )

    diff = total - int(
        counts.sum()
    )

    # --------------------------------------------------------------
    # Distribute remaining frequencies
    # --------------------------------------------------------------

    if diff > 0:

        # We only need the `diff` largest probabilities.
        #
        # argpartition() avoids sorting the entire vocabulary.
        #
        # IMPORTANT:
        # For deterministic compatibility, sort only the selected
        # candidates afterward using the same descending ordering
        # used by the original implementation.
        candidate_count = min(
            diff,
            vocab_size,
        )

        if candidate_count == vocab_size:

            order = np.argsort(
                -p,
                kind="stable",
            )

        else:

            candidates = np.argpartition(
                -p,
                candidate_count - 1,
            )[:candidate_count]

            order = candidates[
                np.argsort(
                    -p[candidates],
                    kind="stable",
                )
            ]

        counts[
            order[:diff]
        ] += 1

    elif diff < 0:

        # This path is normally unnecessary because the construction
        # above starts every symbol at one count and allocates the
        # remaining frequencies. Keep it for defensive compatibility.
        remove = -diff

        # Find the smallest probabilities first without sorting the
        # entire vocabulary.
        candidate_count = min(
            remove,
            vocab_size,
        )

        if candidate_count == vocab_size:

            order = np.argsort(
                p,
                kind="stable",
            )

        else:

            candidates = np.argpartition(
                p,
                candidate_count - 1,
            )[:candidate_count]

            order = candidates[
                np.argsort(
                    p[candidates],
                    kind="stable",
                )
            ]

        for idx in order:

            if remove == 0:
                break

            removable = min(
                int(counts[idx] - 1),
                remove,
            )

            counts[idx] -= removable
            remove -= removable

    # --------------------------------------------------------------
    # Validation
    # --------------------------------------------------------------

    if int(counts.sum()) != total:
        raise RuntimeError(
            "failed to construct arithmetic coding frequencies"
        )

    if np.any(counts <= 0):
        raise RuntimeError(
            "arithmetic coding frequencies must be positive"
        )

    # --------------------------------------------------------------
    # Construct cumulative frequencies
    # --------------------------------------------------------------

    cumulative = np.empty(
        vocab_size + 1,
        dtype=np.int64,
    )

    cumulative[0] = 0

    np.cumsum(
        counts,
        out=cumulative[1:],
    )

    if int(cumulative[-1]) != total:
        raise RuntimeError(
            "CDF total does not match arithmetic coding total"
        )

    return cumulative.tolist()