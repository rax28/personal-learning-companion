# Offline source cache (V8 MVP)

The Source Lab is now a real retrieval path, not only a compression demo.

```text
ONLINE / local services

Source URL or pasted material
        |
        v
   ingest + chunk
        |
        +--------------------+
        |                    |
        v                    v
 compressed source      model predictability
   cache (zlib)          (Ollama/Llama)
        |
        v
 source_id
        |
        v
 user asks in Chat
        |
        v
 lexical retrieval over chunk metadata
        |
        v
 decompress only matching chunks
        |
        v
 source evidence added to Llama prompt
        |
        v
 grounded answer
```

The cache stores independently compressed UTF-8 chunks. The original source can be reconstructed byte-for-byte. Retrieval does not load the entire source into the model prompt.

For a future mobile shell, this same record can move from the AI service's JSON file to an on-device database/IndexedDB/SQLite store. The important MVP contract is already present: `source_id -> compressed chunks -> retrieve -> decompress -> answer`.

## Important distinction

The current Ollama integration can use Llama for normal chat and can attempt token-logprob predictability measurement. Ollama does not expose a complete vocabulary distribution suitable for a standalone arithmetic decoder in the current integration, so the stored source archive is deliberately deterministic zlib lossless compression. `model_used` therefore reports whether predictability scoring succeeded; it does not claim that Llama generated the archive bytes.

## Source-aware chat

After a successful Source compression, the frontend automatically caches that source and keeps the `source_id` in local storage. Chat requests carry that ID. The AI service retrieves relevant compressed chunks and supplies them to the model as authoritative source evidence.

A deterministic regression test uses:

```text
BLUE-PENGUIN-4821
```

and verifies that Chat receives the value from the compressed source cache rather than from the learner graph or conversation history.
