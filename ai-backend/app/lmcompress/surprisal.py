import math


def surprisal_bits(probability: float) -> float:
    if probability <= 0:
        return float("inf")
    return -math.log2(probability)


def sequence_bits(probabilities):
    return [surprisal_bits(float(p)) for p in probabilities]


def total_bits(probabilities) -> float:
    return sum(sequence_bits(probabilities))


def bits_per_byte(total: float, text: str) -> float:
    size = len(text.encode("utf-8"))
    return total / size if size else float("inf")
