# Personal Learning Companion V8 — Final QA Report

## Scope

This build focuses the MVP on the intended online/local-offline architecture:

- Llama 3.2 through Ollama is the local model used for chat testing.
- Source material is chunked and stored as independently compressed lossless cache entries.
- Chat carries the active source cache ID.
- Retrieval decompresses only relevant source chunks and injects them into the Llama prompt as source evidence.
- Learner graph/state remains separate from source knowledge.

## Automated results

- Python `compileall`: PASS
- `tests/`: PASS — 3/3
- `scripts/test-50-scenarios.py`: PASS — 50/50
- Lossless compression/decompression: PASS across 20 varied inputs
- Source cache round trip: PASS
- Source retrieval by query: PASS
- Negative source retrieval: PASS
- Missing source cache handling: PASS
- Source evidence reaching chat model: PASS using a deterministic model stub
- CORS preflight for compression: PASS
- `/health`, graph, gaps, source-default, docs and OpenAPI routes: PASS

## Live-model limitation

The build environment does not have an Ollama daemon available, so a live `llama3.2` generation could not be executed here. On the developer machine, the live model can be tested with:

```bash
ollama show llama3.2
ollama run llama3.2 "What is active code?"
```

Then start the project and run the 50-scenario suite again.

## Browser build limitation

The build environment could not complete an npm dependency installation because the required npm registry package was not cached. Therefore the source was validated with Python tests and static inspection, but a fresh Vite/TypeScript production build was not marked as passed in this environment.

## Source-specific acceptance test

Use this exact source:

```text
SOURCE_TEST_V8

My favorite compression experiment is called BLUE-PENGUIN-4821.

It uses an ImageGPT-based probability model and arithmetic coding.
```

After Source compression, ask Chat:

> What is my compression experiment called?

Expected:

```text
BLUE-PENGUIN-4821
```

The deterministic regression suite already proves that this value comes from the compressed source cache and is passed into the model prompt.
