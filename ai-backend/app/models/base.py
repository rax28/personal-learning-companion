from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

@dataclass
class ModelResponse:
    text: str
    model: str
    provider: str

class Model(Protocol):
    async def generate(self, system: str, messages: list[dict[str, str]]) -> ModelResponse:
        ...
