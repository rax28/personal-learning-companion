# Running locally

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install

# in another terminal, start Ollama and make sure the model exists
ollama serve
ollama pull llama3.2

# start frontend + Node + Python
npm run dev
```

Services:
- Frontend: http://localhost:5173
- Express backend: http://localhost:4000
- FastAPI AI backend: http://localhost:8000

If you want to run them separately:

```bash
npm run dev:frontend
npm run dev:backend
npm run dev:ai
```

For the AI backend only, this is also valid:

```bash
cd ai-backend
python -m uvicorn app.main:app --reload --port 8000
```

The important detail is that `app.main:app` is resolved from `ai-backend`, where the Python `app/` package lives.
