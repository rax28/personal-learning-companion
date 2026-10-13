
from __future__ import annotations

import os
import logging

from openai import AsyncOpenAI
from openai import (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    InternalServerError,
    APIStatusError,
)

from app.models.base import ModelResponse
from app.models.online.openai_model import OpenAIModel
from app.models.online.gemini import GeminiModel

logger = logging.getLogger(__name__)

PROVIDERS = {
    "groq": {
        "key": "GROQ_API_KEY",
        "url": "https://api.groq.com/openai/v1",
        "model_key": "GROQ_MODEL",
        "default": "llama-3.3-70b-versatile",
    },
    "openrouter": {
        "key": "OPENROUTER_API_KEY",
        "url": "https://openrouter.ai/api/v1",
        "model_key": "OPENROUTER_MODEL",
        "default": "meta-llama/llama-3.2-3b-instruct:free",
    },
    "nvidia": {
        "key": "NVIDIA_API_KEY",
        "url": "https://integrate.api.nvidia.com/v1",
        "model_key": "NVIDIA_MODEL",
        "default": "meta/llama-3.3-70b-instruct",
    },
    "mistral": {
        "key": "MISTRAL_API_KEY",
        "url": "https://api.mistral.ai/v1",
        "model_key": "MISTRAL_MODEL",
        "default": "mistral-small-latest",
    },
    "deepseek": {
        "key": "DEEPSEEK_API_KEY",
        "url": "https://api.deepseek.com",
        "model_key": "DEEPSEEK_MODEL",
        "default": "deepseek-chat",
    },
    "huggingface": {
        "key": "HUGGINGFACE_TOKEN",
        "url": "https://router.huggingface.co/v1",
        "model_key": "HUGGINGFACE_MODEL",
        "default": "openai/gpt-oss-120b:fastest",
    },
}


def should_fallback(exc: Exception) -> bool:
    if isinstance(
        exc,
        (APIConnectionError, APITimeoutError, RateLimitError,
         InternalServerError),
    ):
        return True

    if isinstance(exc, APIStatusError):
        return exc.status_code in (408, 409, 429) or exc.status_code >= 500

    return False


class ModelRouter:
    def __init__(self):
        # Groq is always tried first.
        self.order = [
            "groq", "openrouter", "gemini", "openai",
            "nvidia", "mistral", "deepseek", "huggingface",
        ]

    async def _generate_provider(self, provider, system, messages):
        if provider == "gemini":
            return await GeminiModel().generate(system, messages)

        if provider == "openai":
            return await OpenAIModel().generate(system, messages)

        config = PROVIDERS[provider]
        api_key = os.getenv(config["key"], "").strip()
        if not api_key:
            raise ValueError(f"Missing {config['key']}")

        model_name = os.getenv(
            config["model_key"], config["default"]
        ).strip()
        if not model_name:
            raise ValueError(f"Missing {config['model_key']}")

        client = AsyncOpenAI(
            api_key=api_key,
            base_url=config["url"],
            timeout=45,
            max_retries=0,
        )

        try:
            response = await client.chat.completions.create(
                model=model_name,
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
            if not text.strip():
                raise RuntimeError(f"{provider} returned an empty response")
            return ModelResponse(text, model_name, provider)
        finally:
            await client.close()

    async def generate(self, system, messages):
        errors = []

        for provider in self.order:
            # Skip unconfigured providers without exposing secrets.
            if provider in PROVIDERS:
                if not os.getenv(PROVIDERS[provider]["key"], "").strip():
                    continue
            elif provider == "gemini":
                if not os.getenv("GEMINI_API_KEY", "").strip():
                    continue
            elif provider == "openai":
                if not os.getenv("OPENAI_API_KEY", "").strip():
                    continue

            try:
                result = await self._generate_provider(
                    provider, system, messages
                )
                if provider != self.order[0]:
                    logger.warning("AI fallback succeeded using %s", provider)
                return result

            except Exception as exc:
                errors.append(f"{provider}: {type(exc).__name__}")
                logger.warning(
                    "AI provider %s failed (%s)",
                    provider, type(exc).__name__,
                )

                # Don't cycle through providers for permanent configuration
                # or request errors. Continue only for transient failures.
                if isinstance(exc, ValueError):
                    continue
                if not should_fallback(exc):
                    raise

        raise RuntimeError(
            "All configured AI providers failed or were unavailable: "
            + "; ".join(errors)
        )
