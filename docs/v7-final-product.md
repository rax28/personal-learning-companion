# Personal Learning Companion v7 — final architecture

## Core learning loop

`State → Gap → Teaching → Evaluation → Evidence → Mastery → Learner Graph`

Conversation is the natural interface. Durable learner state lives in SQLite; raw messages are evidence, not graph nodes.

## Topic separation

Each `(mode, topic)` gets its own resumable thread. Switching topics pauses the previous thread instead of overwriting it. Returning to a topic loads its saved `conversation_state`, current gap, stage, difficulty, and pending practice question.

## Source side

Educational material is handled separately from learner state:

`Source → Ingestion → Clean/Chunk → Source Graph + Model Predictability → Lossless Archive → Retrieval`

The supplied `Understanding is Compression` paper describes LMCompress as tokenization, a generative large model producing predictive distributions, then arithmetic coding for lossless compression. This v7 implements an LMCompress-inspired integration: Ollama model scoring is collected when the local endpoint exposes prompt logprobs, while the stored archive remains byte-exact using a deterministic lossless codec. It intentionally does not claim to reproduce the paper's complete research codec.

## Source lab

The UI now has a Source Lab where a user can:

1. paste educational text;
2. load the supplied research PDF URL;
3. run the local model-backed predictability pass;
4. view original/archive size, ratio, model status and chunks;
5. download the exact lossless archive.

## Natural conversation changes

The local Ollama adapter now uses the native chat API instead of flattening roles into literal `User:` / `Companion:` strings. The tutor prompt also forbids canned praise, repetitive restatement, role labels, self-answered questions, and unrelated topic carryover.

## Verification

The AI backend test suite passes the existing learning/state/topic/evidence tests. Frontend production build depends on a complete npm dependency install on the target machine.


## Recovered Code Ocean bGPT integration

The project now includes the core bGPT model source copied from the supplied Code Ocean PDF: PatchLevelDecoder, ByteLevelDecoder, bGPTLMHeadModel, bGPTForClassification, and the sampling utilities. The implementation is isolated from the tutor/learner response path. The supplied source did not contain the original `data.model.bgpt.config` file or a trained checkpoint, so the integration does not claim to reproduce a trained Code Ocean LMCompress codec until those artifacts are available.
