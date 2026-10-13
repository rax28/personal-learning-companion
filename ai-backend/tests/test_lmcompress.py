import numpy as np

from app.lmcompress.arithmetic_coder import ArithmeticDecoder, ArithmeticEncoder, probabilities_to_cumulative
from app.lmcompress.neural import decode_tokens, encode_tokens


def test_arithmetic_round_trip():
    pdf = np.array([0.05, 0.15, 0.30, 0.50])
    cdf = probabilities_to_cumulative(pdf)
    enc = ArithmeticEncoder()
    symbols = [3, 2, 3, 1, 0, 3, 2]
    for s in symbols:
        enc.encode(cdf[s], cdf[s + 1], cdf[-1])
    payload, padded = enc.finish()
    dec = ArithmeticDecoder(payload, padded)
    assert [dec.decode(cdf) for _ in symbols] == symbols


def test_neural_codec_round_trip():
    def predict(context):
        base = np.arange(1, 5, dtype=np.float64)
        if context:
            base = np.roll(base, context[-1])
        return base / base.sum()

    tokens = [0, 1, 3, 2, 3, 3, 0]
    encoded = encode_tokens(tokens, predict, 4)
    assert decode_tokens(encoded, predict) == tokens
