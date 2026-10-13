# v6 Architecture / Graph Fix Report

## Fixed

The learner pipeline is now explicitly persisted as:

`State → Gap → Teaching → Evaluation → Evidence → Mastery → Graph`

### 1. State
`conversation_state` persists topic, stage, difficulty, waiting-for-answer, pending question, current gap, and status.

### 2. Gap
The companion keeps the current smallest gap on the topic thread and recognizes explicit prerequisite gaps such as `I don't know what a palindrome is`.

### 3. Teaching
Existing teaching/model response behavior is preserved. This fix does not replace the model or rewrite the teaching prompt/strategy.

### 4. Evaluation
Deterministic evaluation remains in `TeachingEngine` for high-confidence tiny exercises; uncertain answers are not falsely graded.

### 5. Evidence
Meaningful evidence is now written through to SQLite even when it is not strong enough to change mastery. A learner message is evidence, never a graph node.

### 6. Mastery
Correct/incorrect practice continues to update understanding, attempts, and correct counts on stable concept nodes.

### 7. Graph
The graph is SQLite-backed and now exposes persisted conversation state alongside concepts, edges, mastery and evidence. The UI displays current topic/stage/gap/waiting state.

### 8. Conversation separation
Topic threads are stable per `(mode, topic)`. Switching from Two Pointers to Two Sum creates/switches to the Two Sum thread. Returning to Two Pointers retrieves its saved state instead of restarting it.

`Two Sum` aliases were added so a natural message such as `two sum` is recognized as a topic switch.

## Source-side architecture

A separate `knowledge/` layer was added for the source side:

- deterministic source chunking
- source concept graph representation
- lossless compression interface

The compression module currently provides a zlib lossless baseline and explicitly does **not** claim to be an LMCompress reimplementation. It is separate from the learner State → Gap loop so the model can be changed without losing learner state.

## Validation

AI backend tests: **16 passed**.

The added tests cover:

- evidence persistence without message nodes
- Two Sum / Two Pointers topic separation and resume
- graph exposure of conversation state
- source chunking and lossless round-trip
- source graph separation from learner mastery

The frontend/backend npm dependency tree was not available in the execution environment, so npm build/test was not used as the validation source; no existing model-response code was intentionally changed.
