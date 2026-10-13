from __future__ import annotations

import math
from typing import Sequence

import httpx


class OllamaPredictor:
    def __init__(
        self,
        model: str = "llama3.2:latest",
        base_url: str = "http://127.0.0.1:11434",
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def predict(self, prompt: str) -> list[float]:
        """
        Return the probability distribution for the next token.

        This currently uses Ollama's OpenAI-compatible completion endpoint.
        """
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.base_url}/v1/completions",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "max_tokens": 1,
                    "temperature": 0,
                    "logprobs": True,
                    "top_logprobs": 5,
                    "stream": False,
                },
            )

        response.raise_for_status()
        data = response.json()

        choice = data["choices"][0]
        logprobs = choice.get("logprobs")

        if not logprobs:
            raise RuntimeError("Ollama did not return logprobs")

        # This endpoint currently gives us the selected token and
        # top alternatives, not the complete vocabulary distribution.
        raise RuntimeError(
            "Top-token logprobs are insufficient for arithmetic coding. "
            "We need the complete next-token distribution."
        )
