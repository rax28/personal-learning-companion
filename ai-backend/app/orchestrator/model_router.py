
from __future__ import annotations
import os
from app.models.online.openai_model import OpenAIModel
from app.models.online.gemini import GeminiModel
from app.models.local.ollama import OllamaModel

class ModelRouter:
    def __init__(self):
        provider = os.getenv("ONLINE_PROVIDER", "ollama").lower()
        self.model = {"openai": OpenAIModel, "gemini": GeminiModel}.get(provider, OllamaModel)()

    async def generate(self, system, messages):
        return await self.model.generate(system=system, messages=messages)
