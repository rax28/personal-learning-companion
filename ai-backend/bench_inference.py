import os
import time

from app.lmcompress.llama_backend import Llama32Backend

model = os.environ["LLAMA_MODEL_PATH"]

text = "The goal of this benchmark is to measure incremental language model evaluation speed. " * 100

backend = Llama32Backend(
    model,
    n_ctx=8192,
    n_batch=256,
    n_gpu_layers=-1,
    flash_attn=False,
)

tokens = backend.llm.tokenize(text.encode("utf-8"))

print("tokens:", len(tokens))
print("n_ctx:", backend.llm.n_ctx())
print("n_batch:", backend.llm.n_batch)

backend.start_context(tokens[0])

start = time.perf_counter()

for token in tokens[1:]:
    backend.evaluate_next(token)

elapsed = time.perf_counter() - start
count = len(tokens) - 1

print()
print("EVALUATION TIME:", elapsed)
print("TOKENS:", count)
print("MS/TOKEN:", elapsed / count * 1000)
print("TOKENS/SECOND:", count / elapsed)
