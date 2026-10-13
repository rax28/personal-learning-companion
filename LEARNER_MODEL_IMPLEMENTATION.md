# Learner Model Implementation — V8

This build adds the missing learner-model persistence layer while preserving the existing
Source Lab, compression, retrieval, tutor, and graph behavior.

## Implemented

- Learner profile persisted in SQLite (`learner_profile`)
- Concept list from the persistent knowledge graph
- Concept-level mastery from the existing `mastery` table
- Knowledge gaps derived from persisted mastery/attempts
- Learning history from `learning_evidence`
- Assessment evidence from successful applications, practice errors, and answer attempts
- Mastery updates persisted in `mastery_history`
- Concept relationships persisted in the existing `connections` graph
- Learning graph exposed as concepts + relationships
- Persistent learner state reconstructed from SQLite after process restart
- AI responses now expose the durable learner snapshot while retaining the legacy learner summary

## API

AI backend:
- `GET /learning/state`
- `GET /learning/profile`
- `PUT /learning/profile`
- `GET /learning/concepts`
- `GET /learning/history`
- `GET /learning/assessment-evidence`
- `GET /learning/mastery-updates`
- `GET /learning/relationships`

Node gateway proxies the same learning routes.

## Regression checks

- Python AI test suite: 26 passed
- Backend TypeScript type-check: passed
- Frontend TypeScript build-check (`tsc -b`): passed
- Full V8 compression/source tests are included and were not replaced.
