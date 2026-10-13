from __future__ import annotations

import os

from app.models.base import ModelResponse


class OpenAIModel:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("OPENAI_MODEL", "gpt-5")
        self.web_search = (
            os.getenv("OPENAI_WEB_SEARCH", "false").lower() == "true"
        )

    async def generate(self, system, messages):
        if not self.api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not configured. "
                "Check your .env file."
            )

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key)

        kwargs = {
            "model": self.model,
            "instructions": system,
            "input": messages,
        }

        if self.web_search:
            kwargs["tools"] = [{"type": "web_search_preview"}]

        response = await client.responses.create(**kwargs)

        return ModelResponse(
            response.output_text or "",
            self.model,
            "openai",
        )