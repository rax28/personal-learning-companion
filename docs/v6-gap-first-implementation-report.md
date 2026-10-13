# v6 Gap-First / Resumable Learning Report

## Core behavior fixed
The companion now treats **State -> Gap -> Teaching -> Evaluation -> Evidence -> Mastery -> Graph** as the learning loop, while keeping each topic as a resumable conversation thread.

### State
- Explicit topic, stage, difficulty, pending-question, current-gap, waiting-for-answer and paused/active status are persisted in SQLite.
- A topic switch pauses the previous topic instead of overwriting it.
- Returning to a previous topic reuses its saved state.

### Gap
- The latest message has priority over stale conversation context.
- Explicit prerequisite gaps are tracked separately from the parent topic.
- Example: saying `I don't know what a palindrome is` while learning Two Pointers records **Palindrome definition** as the current gap instead of continuing to ask about pointer initialization.
- `what/wut is my gap?` is answered from saved state rather than inventing a new gap.

### Teaching
- The model is constrained to teach the smallest missing idea.
- Understanding moves into a single small practice question.
- The tutor waits for the answer instead of immediately solving its own question.
- Math and DSA keep the intended adaptive loops.

### Evaluation
- Deterministic tiny practice checks remain in the teaching engine.
- Correct answers advance difficulty and keep the learner in a waiting-for-the-next-question state.
- Incorrect answers stay on the same idea and request a simpler retry.
- Ambiguous answers are not falsely graded.

### Evidence
- Learner statements and practice results become evidence attached to concepts.
- Raw chat messages never become knowledge-graph nodes.
- Repeated generic confusion remains attached to the same concept instead of creating duplicate pseudo-concepts.

### Mastery
- Mastery changes only from meaningful evidence/practice signals.
- Attempts and correct counts are persisted.
- Topic mentions alone do not award mastery.

### Graph
- SQLite remains the durable knowledge graph store.
- Existing graph tables are preserved.
- `conversation_state` now also stores `current_gap` and `status`.
- The graph represents concepts and relationships; evidence stores the supporting messages.

## Topic/conversation separation
Each learning area can have separate topic threads:

- Education
- Self Understanding
- Interview Prep

Within an area, topics are independently resumable. For example:

`Two Pointers -> HashMap -> Two Pointers`

returns to the Two Pointers thread rather than feeding the HashMap conversation into it.

The shared learner graph remains available across areas for relevant durable knowledge, without merging conversation histories.

Node persists the topic-thread mapping in `.data/companion.json`; the AI backend persists topic learning state in SQLite.

## UI behavior
- Existing simple pixel-cat UI is preserved.
- Existing idle/listening/sleep/jump/fall frames remain in use.
- Three floating navigation areas remain: Education, Self Understanding, Interview Prep.
- Progress/knowledge-map page continues to show concept nodes, mastery, gaps and evidence.
- Topic-thread IDs are persisted in browser local storage so switching back can request the correct saved thread.

## Files changed
- `backend/src/app.ts`
  - Added topic-aware conversation routing.
  - Added persistent topic-thread mapping.
  - Added `topicHint` API field.
  - Stores topic metadata with messages.
- `ai-backend/app/main.py`
  - Accepts and forwards `topicHint`.
- `ai-backend/app/orchestrator/companion.py`
  - Added resumable topic threads.
  - Added explicit gap state.
  - Added move-on/pause behavior.
  - Added prerequisite-gap handling.
  - Tightened the teaching/evaluation prompt and state transitions.
- `ai-backend/app/orchestrator/conversation_store.py`
  - Added `current_gap` and `status` state.
- `ai-backend/app/knowledge/persistent_graph.py`
  - Persisted `current_gap` and `status` with backward-compatible SQLite upgrades.
- `frontend/src/main.tsx`
  - Added topic-thread local persistence and topic hints so returning to a known topic loads its saved thread.
- `ai-backend/tests/test_v5_conversation.py`
  - Updated the old topic-switch expectation to match the requested separate-thread behavior.
- `ai-backend/tests/test_v6_learning.py`
  - Added pause/resume and explicit prerequisite-gap tests.

## Tests performed
- AI backend test suite: **13 passed**.
- Python source compilation: passed.
- TypeScript/TSX syntax transpilation checks: passed for backend and frontend source files.
- Verified graph message rule: messages remain evidence, not nodes.
- Verified persisted conversation state.
- Verified Two Pointers practice loop.
- Verified topic switching creates separate topic threads.
- Verified returning to a topic resolves to the original topic thread.
- Verified explicit `Palindrome definition` gap tracking.

## Not fully tested
- Full React/Vite production build could not be completed in this sandbox because the dependency tree in the supplied project was incomplete/corrupted and package installation timed out/failed. TypeScript syntax itself was checked successfully.
- Full Express runtime with its installed npm dependencies was not available in the sandbox.
- Live Ollama generation was not exercised in the sandbox.

## Runtime note
Run the AI backend from `ai-backend` (or use the repository `npm run dev:ai` script) so Python can import `app.main` correctly.
