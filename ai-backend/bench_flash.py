import time
from llama_cpp import Llama

MODEL ="$HOME/.ollama/models/blobs/sha256-dde5aa3fc5ffc17176b5e8bdc82f587b24b2678c6c66101bf7da77af9f7ccdff"

llm = Llama(
    model_path=MODEL,
    n_gpu_layers=-1,
    n_ctx=8192,
    n_batch=256,
    n_ubatch=256,
    flash_attn=True,
    verbose=False,
)

prompt = """Explain photosynthesis in detail, including the light-dependent
reactions, Calvin cycle, ATP, NADPH, and how the two stages are connected."""

# Warmup
llm(prompt, max_tokens=100)

# Benchmark
runs = 3
times = []
tokens = []

for i in range(runs):
    start = time.perf_counter()

    output = llm(
        prompt,
        max_tokens=300,
        temperature=0,
    )

    elapsed = time.perf_counter() - start

    n = output["usage"]["completion_tokens"]

    times.append(elapsed)
    tokens.append(n)

    print(f"Run {i+1}: {n} tokens / {elapsed:.2f}s = {n/elapsed:.2f} tok/s")

print()
print(f"AVERAGE: {sum(tokens)/sum(times):.2f} tok/s")
