# Data flow
1. User message arrives at Express.
2. Express forwards goal + relevant learner state to FastAPI.
3. FastAPI extracts evidence, updates provisional learner state, identifies gaps/root blocks, selects teaching strategy and generates a response.
4. Structured state returns to Express and is persisted in the real database in the production path.
