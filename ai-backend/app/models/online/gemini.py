
from __future__ import annotations
import os
from app.models.base import ModelResponse

class GeminiModel:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    async def generate(self, system, messages):
        if not self.api_key:
            from app.models.local.ollama import OllamaModel
            return await OllamaModel().generate(system, messages)

        from google import genai
        client = genai.Client(api_key=self.api_key)
        contents = [
            {"role": m["role"], "parts": [{"text": m["content"]}]}
            for m in messages
        ]
        response = await client.aio.models.generate_content(
            model=self.model, contents=contents,
            config={"system_instruction": system},
        )
        return ModelResponse(response.text or "", self.model, "gemini")
