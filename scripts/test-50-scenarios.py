"""Deterministic 50-scenario AI/source regression suite.
Run from project root: PYTHONPATH=ai-backend:. python scripts/test-50-scenarios.py
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ai-backend"))
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
import app.main as main
from app.models.base import ModelResponse

client = TestClient(main.app)
passed: list[str] = []
failed: list[tuple[str, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        passed.append(name)
    else:
        failed.append((name, detail))


# 1-12 route/shape checks
for name, path in [
    ("health", "/health"), ("graph", "/graph"),
    ("graph education", "/graph/education"), ("graph self", "/graph/self"),
    ("graph interview", "/graph/interview"), ("graph unknown", "/graph/unknown"),
    ("gaps", "/gaps"), ("source default", "/compression/source-default"),
    ("docs", "/docs"), ("openapi", "/openapi.json"),
]:
    r = client.get(path)
    check(name, r.status_code == 200, f"{r.status_code} {r.text[:200]}")

r = client.options("/compression/compress", headers={
    "Origin": "http://localhost:4000",
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "content-type",
})
check("compression CORS preflight", r.status_code == 200, f"{r.status_code} {r.text[:200]}")

# 13-32 compression + exact round-trip scenarios
texts = [
    "hello world",
    "Understanding is compression. A learner improves by building better internal representations.",
    "Integration is the accumulation of infinitesimal change over an interval.",
    "Two pointers often reduces a quadratic search to linear time.",
    "Binary search repeatedly halves the search interval.",
    "Recursion solves a problem by solving smaller instances of itself.",
    "Dynamic programming stores results of overlapping subproblems.",
    "Democracy distributes political power through participation and representation.",
    "Federalism divides authority between levels of government.",
    "Java is a statically typed programming language.",
    "The quick brown fox jumps over the lazy dog.",
    "1234567890 !@#$%^&*() [] {} <>",
    "line one\nline two\nline three",
    "unicode: café naïve résumé — 東京 — नमस्ते",
    "A" * 1000,
    "A learner asks a question, receives an explanation, then attempts a challenge.",
    "Correct answers should increase confidence; repeated errors should reveal a gap.",
    "Source material should remain byte-exact after compression and decompression.",
    "Model predictability can be measured separately from the lossless archive.",
    "Chunk → predictability → arithmetic coding → archive.",
]
for idx, text in enumerate(texts, 13):
    r = client.post("/compression/compress", json={"text": text, "model": "llama3.2"})
    ok = r.status_code == 200
    detail = f"compress {r.status_code} {r.text[:160]}"
    if ok:
        data = r.json()
        ok = data.get("original_bytes") == len(text.encode()) and bool(data.get("payload_b64"))
        detail = "shape mismatch"
        if ok:
            d = client.post("/compression/decompress", json={"payload_b64": data["payload_b64"]})
            ok = d.status_code == 200 and d.json().get("text") == text
            detail = f"decompress {d.status_code}"
    check(f"compression {idx}", ok, detail)

# 33-38 validation
for name, path, payload in [
    ("empty compression", "/compression/compress", {"text": ""}),
    ("bad payload", "/compression/decompress", {"payload_b64": "not-base64"}),
    ("missing payload", "/compression/decompress", {}),
    ("bad source scheme", "/compression/load-source", {"sourceUrl": "ftp://example.com/x"}),
    ("bad chat mode", "/internal/chat", {"message": "hello", "mode": "bad"}),
    ("empty chat", "/internal/chat", {"message": "", "mode": "education"}),
]:
    r = client.post(path, json=payload)
    check(name, r.status_code >= 400, f"unexpected {r.status_code}")

# 39-44 compressed source cache: retrieval must be from stored compressed chunks.
source = "SOURCE_TEST_V8\nMy favorite compression experiment is called BLUE-PENGUIN-4821.\nIt uses arithmetic coding and stores only the active source cache."
r = client.post("/source/cache", json={"text": source, "sourceUrl": "manual://source-test"})
check("source cache put", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
source_id = r.json().get("source_id") if r.status_code == 200 else ""

r = client.get(f"/source/cache/{source_id}")
check("source cache metadata", r.status_code == 200 and r.json().get("compressed_bytes", 0) > 0, f"{r.status_code}")

r = client.post(f"/source/cache/{source_id}/search", json={"query": "What is my compression experiment called?"})
hits = r.json().get("results", []) if r.status_code == 200 else []
check("source retrieval", r.status_code == 200 and hits and "BLUE-PENGUIN-4821" in hits[0]["text"], f"{r.status_code} {r.text[:200]}")

r = client.get(f"/source/cache/{source_id}/text")
check("source full decompression", r.status_code == 200 and r.json().get("text") == source, f"{r.status_code}")

# Deterministic model stub: proves the source evidence reaches the chat model.
original_router = main.companion.router
class SourceAwareStub:
    async def generate(self, system: str, messages: list[dict]) -> ModelResponse:
        if "BLUE-PENGUIN-4821" not in system:
            raise AssertionError("compressed source evidence did not reach model prompt")
        return ModelResponse("Your compression experiment is BLUE-PENGUIN-4821.", "test", "test")
main.companion.router = SourceAwareStub()
r = client.post("/internal/chat", json={
    "message": "What is my compression experiment called?",
    "mode": "education",
    "conversationId": "source-regression-chat",
    "sourceId": source_id,
})
check("source-aware chat", r.status_code == 200 and "BLUE-PENGUIN-4821" in r.json().get("response", ""), f"{r.status_code} {r.text[:250]}")
r = client.post(f"/source/cache/{source_id}/search", json={"query": "completely-unrelated-token-999"})
check("source negative retrieval", r.status_code == 200 and not r.json().get("results"), f"{r.status_code} {r.text[:200]}")
r = client.get("/source/cache/does-not-exist")
check("missing source cache safe", r.status_code == 404, f"{r.status_code} {r.text[:200]}")
main.companion.router = original_router

# 45-50 chat API shape scenarios with deterministic stub.
async def chat_stub(*args, **kwargs):
    return {"response": "ok-response", "topic": "Testing", "learnerState": {"current": {"topic": "Testing"}}, "evidence": []}
orig_respond = main.companion.respond
main.companion.respond = chat_stub
chat_cases = [
    {"message": "hello", "mode": "education"},
    {"message": "explain recursion", "mode": "education", "topicHint": "Recursion"},
    {"message": "practice", "mode": "interview", "conversationId": "c1"},
    {"message": "reflect", "mode": "self", "learnerContext": {"topic": "x"}},
    {"message": "goal check", "mode": "education", "goal": "Learn calculus"},
    {"message": "source follow-up", "mode": "education", "sourceId": source_id},
]
for idx, payload in enumerate(chat_cases, 45):
    r = client.post("/internal/chat", json=payload)
    check(f"chat shape {idx}", r.status_code == 200 and r.json().get("response") == "ok-response", f"{r.status_code} {r.text[:220]}")
main.companion.respond = orig_respond

print(f"PASSED {len(passed)}/50")
for item in failed:
    print("FAIL", item)
if failed:
    raise SystemExit(1)
