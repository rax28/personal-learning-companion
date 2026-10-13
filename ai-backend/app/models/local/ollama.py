from __future__ import annotations

import os
import httpx

from app.models.base import ModelResponse


class OllamaModel:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        self.model = os.getenv("LOCAL_MODEL", "llama3.2")

    async def generate(self, system: str, messages: list[dict]) -> ModelResponse:
        # Use Ollama's native chat API so roles stay roles. The old implementation
        # flattened everything into `User:` / `Companion:` text, which encouraged
        # small local models to echo those labels back into the answer.
        chat_messages = [{"role": "system", "content": system}]
        for message in messages:
            role = message.get("role", "").lower()
            content = message.get("content", "").strip()
            if role in {"user", "assistant"} and content:
                chat_messages.append({"role": role, "content": content})

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": chat_messages,
                    "stream": False,
                    "options": {"temperature": 0.45},
                },
            )
            response.raise_for_status()
            data = response.json()

        text = (data.get("message") or {}).get("content", "").strip()
        return ModelResponse(text, self.model, "ollama")
