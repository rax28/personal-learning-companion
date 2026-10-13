# Source knowledge layer

This is intentionally separate from the learner loop.

- `ingestion/` creates stable chunks from extracted educational material.
- `source_knowledge/` represents source concepts and relationships.
- `compression/` exposes the existing lossless storage interface. The recovered Code Ocean bGPT implementation is isolated under `ai-backend/app/lmcompress/`; it does not alter the learner/tutor loop. The supplied source did not include the original trained checkpoint/configuration, so the project does not claim a trained Code Ocean codec is available.
- The tutor continues to use the learner-side loop: State → Gap → Teaching → Evaluation → Evidence → Mastery → Graph.
