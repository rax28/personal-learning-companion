from fastapi.testclient import TestClient

from app import main
from app.main import app


def test_all_ai_api_routes_and_lossless_roundtrip():
    client = TestClient(app)

    assert client.get("/health").status_code == 200
    assert client.get("/graph").status_code == 200
    assert client.get("/graph/education").status_code == 200
    assert client.get("/gaps").status_code == 200
    assert client.get("/compression/source-default").status_code == 200

    preflight = client.options(
        "/compression/compress",
        headers={
            "Origin": "http://localhost:4000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers.get("access-control-allow-origin") == "http://localhost:4000"

    source = "Understanding is compression. A learner improves by building better internal representations."
    packed = client.post(
        "/compression/compress",
        json={"text": source, "model": "llama3.2"},
    )
    assert packed.status_code == 200
    body = packed.json()
    assert body["original_bytes"] == len(source.encode())
    assert body["payload_b64"]
    assert body["sha256"]

    restored = client.post(
        "/compression/decompress",
        json={"payload_b64": body["payload_b64"]},
    )
    assert restored.status_code == 200
    assert restored.json()["text"] == source


def test_internal_chat_route_without_external_model():
    async def fake_respond(*args, **kwargs):
        return {
            "response": "test response",
            "topic": "Testing",
            "learnerState": {"current": {"topic": "Testing"}},
            "evidence": [],
        }

    original = main.companion.respond
    main.companion.respond = fake_respond
    try:
        response = TestClient(app).post(
            "/internal/chat",
            json={
                "message": "hello",
                "conversationId": "smoke",
                "mode": "education",
                "history": [],
            },
        )
        assert response.status_code == 200
        assert response.json()["response"] == "test response"
    finally:
        main.companion.respond = original
