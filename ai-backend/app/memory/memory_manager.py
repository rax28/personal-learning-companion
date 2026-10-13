
from __future__ import annotations

import os
import httpx

from app import db


class MemoryManager:
    def __init__(self):
        self.ollama_url = os.getenv(
            "OLLAMA_BASE_URL",
            "http://127.0.0.1:11434",
        ).rstrip("/")
        self.embedding_model = os.getenv(
            "EMBEDDING_MODEL",
            "bge-m3:latest",
        )
        self.embedding_dimensions = 1024

    async def embed(self, text: str) -> list[float]:
        """Convert text into a BGE-M3 embedding."""
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.ollama_url}/api/embed",
                json={
                    "model": self.embedding_model,
                    "input": text,
                },
            )
            response.raise_for_status()
            data = response.json()

        embeddings = data.get("embeddings", [])
        if not embeddings:
            raise RuntimeError("Ollama returned no embedding")

        vector = embeddings[0]

        if len(vector) != self.embedding_dimensions:
            raise ValueError(
                f"Expected {self.embedding_dimensions} dimensions, "
                f"received {len(vector)}"
            )

        return vector

    @staticmethod
    def _vector_literal(vector: list[float]) -> str:
        """Format a vector for PostgreSQL's vector type."""
        return "[" + ",".join(str(float(x)) for x in vector) + "]"

    async def store(
        self,
        content: str,
        kind: str = "conversation",
        importance: float = 0.5,
    ) -> None:
        """Save a memory and its embedding for the current user."""
        content = content.strip()
        if not content:
            return

        embedding = await self.embed(content)
        vector_text = self._vector_literal(embedding)
        uid = db.user_id()

        db.execute(
            """
            INSERT INTO memories
                (id, user_id, kind, content, importance, embedding)
            VALUES
                (gen_random_uuid(), %s::uuid, %s, %s, %s, %s::vector)
            """,
            (uid, kind, content, importance, vector_text),
        )

    async def relevant(
        self,
        query: str,
        limit: int = 3,
    ) -> list[dict]:
        """Retrieve semantically similar memories for the current user."""
        uid = db.user_id()

        # Avoid calling the embedding model if this user has no memories.
        result = db.fetchone(
            """
            SELECT EXISTS (
                SELECT 1
                FROM memories
                WHERE user_id = %s::uuid
                  AND embedding IS NOT NULL
            ) AS has_memories
            """,
            (uid,),
        )

        if not result or not result["has_memories"]:
            return []

        embedding = await self.embed(query)
        vector_text = self._vector_literal(embedding)

        return db.fetchall(
            """
            SELECT content, kind, importance,
                   embedding <=> %s::vector AS distance
            FROM memories
            WHERE user_id = %s::uuid
              AND embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (vector_text, uid, vector_text, max(1, min(limit, 10))),
        )
