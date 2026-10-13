
from __future__ import annotations

import os

from openai import AsyncOpenAI
from app.models.base import ModelResponse
from app.models.online.openai_model import OpenAIModel
from app.models.online.gemini import GeminiModel


PROVIDERS = {
    "groq": {
        "key": "GROQ_API_KEY",
        "url": "https://api.groq.com/openai/v1",
        "model_key": "GROQ_MODEL",
        "default_model": "llama-3.3-70b-versatile",
    },
    "openrouter": {
        "key": "OPENROUTER_API_KEY",
        "url": "https://openrouter.ai/api/v1",
        "model_key": "OPENROUTER_MODEL",
        "default_model": "",
    },
    "nvidia": {
        "key": "NVIDIA_API_KEY",
        "url": "https://integrate.api.nvidia.com/v1",
        "model_key": "NVIDIA_MODEL",
        "default_model": "meta/llama-3.3-70b-instruct",
    },
    "mistral": {
        "key": "MISTRAL_API_KEY",
        "url": "https://api.mistral.ai/v1",
        "model_key": "MISTRAL_MODEL",
        "default_model": "mistral-small-latest",
    },
    "deepseek": {
        "key": "DEEPSEEK_API_KEY",
        "url": "https://api.deepseek.com",
        "model_key": "DEEPSEEK_MODEL",
        "default_model": "deepseek-chat",
    },
    "huggingface": {
        "key": "HUGGINGFACE_TOKEN",
        "url": "https://router.huggingface.co/v1",
        "model_key": "HUGGINGFACE_MODEL",
        "default_model": "openai/gpt-oss-120b:fastest",
    },
}


class ModelRouter:
    def __init__(self):
        self.provider = os.getenv("ONLINE_PROVIDER", "groq").lower()
        self.model = None
        self.client = None
        self.model_name = ""

        if self.provider == "gemini":
            self.model = GeminiModel()
        elif self.provider == "openai":
            self.model = OpenAIModel()
        elif self.provider in PROVIDERS:
            config = PROVIDERS[self.provider]
            api_key = os.getenv(config["key"], "")
            if not api_key:
                raise RuntimeError(
                    f'{config["key"]} is not configured in Railway'
                )

            self.model_name = os.getenv(
                config["model_key"], config["default_model"]
            )
            if not self.model_name:
                raise RuntimeError(
                    f'{config["model_key"]} must be configured'
                )

            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url=config["url"],
                timeout=90,
                max_retries=1,
            )
        else:
            raise ValueError(
                f"Unsupported ONLINE_PROVIDER: {self.provider}"
            )

    async def generate(self, system, messages):
        if self.model is not None:
            return await self.model.generate(system, messages)

        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system},
                *[
                    {"role": m["role"], "content": m["content"].strip()}
                    for m in messages
                    if m.get("role") in {"user", "assistant"}
                    and m.get("content", "").strip()
                ],
            ],
            temperature=0.45,
        )

        text = response.choices[0].message.content or ""
        return ModelResponse(text, self.model_name, self.provider)
