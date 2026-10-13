from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).resolve().parents[2] / ".env")
import os

print("ONLINE_PROVIDER:", os.getenv("ONLINE_PROVIDER"))
print("GEMINI_MODEL:", os.getenv("GEMINI_MODEL"))
print("GEMINI_API_KEY loaded:", bool(os.getenv("GEMINI_API_KEY")))
print("OPENAI_API_KEY loaded:", bool(os.getenv("OPENAI_API_KEY")))

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import base64
from typing import Literal
from app.orchestrator.companion import Companion
from app.api_compression import compress_input, load_source, DEFAULT_SOURCE
from app.source_compression import decompress_lossless
from app.source_cache import CompressedSourceCache
from app import db
import io
from pypdf import PdfReader

app = FastAPI(title="Personal Learning Companion AI")

# The browser normally talks to the Node gateway on port 4000, but allowing
# local development origins here also makes the AI service safe to exercise
# directly from a local frontend/test page.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4000",
        "http://127.0.0.1:4000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

companion = Companion()
source_cache = CompressedSourceCache()

def load_pdf_bytes(raw: bytes) -> str:
    reader = PdfReader(io.BytesIO(raw))
    return "\n\n".join((p.extract_text() or "").strip() for p in reader.pages).strip()
companion.source_cache = source_cache

def auth_user(x_user_id: str | None, x_internal_token: str | None):
    expected=os.getenv("AI_INTERNAL_TOKEN","change-me")
    if not x_internal_token or x_internal_token != expected:
        raise HTTPException(status_code=401, detail="Invalid internal service token")
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Authenticated user id missing")
    db.set_user(x_user_id)
    return x_user_id


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversationId: str | None = None
    goal: str | None = None
    mode: Literal["education", "self", "interview", "professional", "personal"] = "education"
    history: list[dict] = Field(default_factory=list)
    topicHint: str | None = None
    learnerContext: dict = Field(default_factory=dict)
    sourceId: str | None = None
    sourceIds: list[str] = Field(default_factory=list)

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/learning/profile")
async def learning_profile(x_user_id: str|None=Header(None), x_internal_token: str|None=Header(None)):
    auth_user(x_user_id,x_internal_token)
    return companion.graph.get_or_create_profile()

class LearnerProfileUpdate(BaseModel):
    display_name: str | None = None
    grade_level: str | None = None
    goals: list[str] | None = None
    preferences: dict | None = None

@app.put("/learning/profile")
async def update_learning_profile(req: LearnerProfileUpdate, x_user_id: str|None=Header(None), x_internal_token: str|None=Header(None)):
    auth_user(x_user_id,x_internal_token)
    return companion.graph.update_profile(req.display_name, req.grade_level, req.goals, req.preferences)

@app.get("/learning/concepts")
async def learning_concepts(x_user_id: str|None=Header(None), x_internal_token: str|None=Header(None)):
    auth_user(x_user_id,x_internal_token)
    return {"concepts": companion.graph.learner_snapshot()["concepts"]}

@app.get("/learning/history")
async def learning_history(limit: int = 100, x_user_id: str|None=Header(None), x_internal_token: str|None=Header(None)):
    auth_user(x_user_id,x_internal_token)
    return {"history": companion.graph.learning_history(limit)}

@app.get("/learning/assessment-evidence")
async def learning_assessment_evidence(limit: int = 100, x_user_id: str|None=Header(None), x_internal_token: str|None=Header(None)):
    auth_user(x_user_id,x_internal_token)
    return {"evidence": companion.graph.assessment_evidence(limit)}

@app.get("/learning/mastery-updates")
async def learning_mastery_updates(limit: int = 100, x_user_id: str|None=Header(None), x_internal_token: str|None=Header(None)):
    auth_user(x_user_id,x_internal_token)
    return {"updates": companion.graph.mastery_history(limit)}

@app.get("/learning/relationships")
async def learning_relationships(x_user_id: str|None=Header(None), x_internal_token: str|None=Header(None)):
    auth_user(x_user_id,x_internal_token)
    return {"relationships": companion.graph.learner_snapshot()["relationships"]}

@app.get("/learning/state")
async def learning_state(x_user_id: str|None=Header(None), x_internal_token: str|None=Header(None)):
    auth_user(x_user_id,x_internal_token)
    return companion.graph.learner_snapshot()

@app.get("/graph")
async def graph(x_user_id: str|None=Header(None), x_internal_token: str|None=Header(None)):
    auth_user(x_user_id,x_internal_token)
    return companion.graph.snapshot()

@app.get("/graph/{mode}")
async def graph_mode(mode: str, x_user_id: str|None=Header(None), x_internal_token: str|None=Header(None)):
    auth_user(x_user_id,x_internal_token)
    return companion.graph.by_mode(mode)

@app.get("/gaps")
async def gaps(x_user_id: str|None=Header(None), x_internal_token: str|None=Header(None)):
    auth_user(x_user_id,x_internal_token)
    return {"gaps": companion.graph.learner_gaps()}

@app.get("/compression/source-default")
async def compression_source_default():
    return {"url": DEFAULT_SOURCE}

class CompressionRequest(BaseModel):
    text: str = ""
    sourceUrl: str | None = None
    model: str | None = None

@app.post("/compression/load-source")
async def compression_load_source(req: CompressionRequest):
    url = (req.sourceUrl or DEFAULT_SOURCE).strip()
    try:
        return await load_source(url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post("/compression/compress")
async def compression_compress(req: CompressionRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Input text is empty")
    return await compress_input(req.text, model=req.model, source_url=req.sourceUrl)

@app.post("/compression/decompress")
async def compression_decompress(payload: dict):
    import base64, binascii
    value = payload.get("payload_b64") if isinstance(payload, dict) else None
    if not isinstance(value, str) or not value:
        raise HTTPException(status_code=400, detail="payload_b64 is required")
    try:
        packed = base64.b64decode(value, validate=True)
        raw = decompress_lossless(packed)
        text = raw.decode("utf-8")
    except (binascii.Error, ValueError, UnicodeDecodeError, EOFError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid lossless payload: {exc}") from exc
    return {"text": text, "bytes": len(raw)}

@app.post("/source/cache")
async def source_cache_put(req: CompressionRequest, x_user_id: str|None=Header(None), x_internal_token: str|None=Header(None)):
    auth_user(x_user_id,x_internal_token)
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Input text is empty")
    meta = source_cache.put(req.text, req.sourceUrl)
    return {"ok": True, **meta}



class SourceUploadRequest(BaseModel):
    filename: str
    contentBase64: str
    mimeType: str | None = None
    sourceUrl: str | None = None

@app.post("/source/upload")
async def source_upload(req: SourceUploadRequest, x_user_id: str|None=Header(None), x_internal_token: str|None=Header(None)):
    auth_user(x_user_id,x_internal_token)
    try:
        raw = base64.b64decode(req.contentBase64, validate=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid base64 file: {exc}") from exc
    name = req.filename.lower()
    mime = (req.mimeType or "").lower()
    try:
        if name.endswith(".pdf") or "application/pdf" in mime:
            text = load_pdf_bytes(raw)
            kind = "pdf"
        else:
            text = raw.decode("utf-8", errors="replace")
            kind = "text"
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read file: {exc}") from exc
    if not text.strip():
        raise HTTPException(status_code=400, detail="The file contains no extractable text")
    meta = source_cache.put(text, req.sourceUrl or f"file://{req.filename}", req.filename)
    meta["compression_ratio"] = meta.get("original_bytes", 0) / meta.get("compressed_bytes", 1) if meta.get("compressed_bytes") else 1.0
    return {"ok": True, "kind": kind, "filename": req.filename, "textLength": len(text), **meta}

@app.get("/source/cache")
async def source_cache_list(x_user_id: str|None=Header(None), x_internal_token: str|None=Header(None)):
    auth_user(x_user_id,x_internal_token)
    return {"sources": source_cache.list_metadata()}

@app.get("/source/cache/{source_id}")
async def source_cache_meta(source_id: str, x_user_id: str|None=Header(None), x_internal_token: str|None=Header(None)):
    auth_user(x_user_id,x_internal_token)
    try:
        return source_cache.metadata(source_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Source cache entry not found") from exc

@app.post("/source/cache/{source_id}/search")
async def source_cache_search(source_id: str, payload: dict, x_user_id: str|None=Header(None), x_internal_token: str|None=Header(None)):
    auth_user(x_user_id,x_internal_token)
    query = str(payload.get("query", "")).strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    return {"source_id": source_id, "results": source_cache.search(source_id, query, int(payload.get("limit", 4)))}

@app.get("/source/cache/{source_id}/text")
async def source_cache_text(source_id: str, x_user_id: str|None=Header(None), x_internal_token: str|None=Header(None)):
    auth_user(x_user_id,x_internal_token)
    text = source_cache.get(source_id)
    if text is None:
        raise HTTPException(status_code=404, detail="Source cache entry not found")
    return {"source_id": source_id, "text": text}

@app.post("/internal/chat")
async def chat(req: ChatRequest, x_user_id: str|None=Header(None), x_internal_token: str|None=Header(None)):
    uid=auth_user(x_user_id,x_internal_token)
    ids = list(dict.fromkeys([x for x in ([req.sourceId] if req.sourceId else []) + req.sourceIds if isinstance(x, str) and x]))
    return await companion.respond(
        req.message, uid, req.conversationId, req.goal, req.learnerContext, req.mode, req.history, req.topicHint, req.sourceId, ids
    )
