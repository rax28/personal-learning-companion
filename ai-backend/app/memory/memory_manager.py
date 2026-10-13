
from __future__ import annotations

import os

import httpx

from app import db


class MemoryManager:
    def __init__(self):
        self.cloudflare_account_id = os.getenv(
            "CLOUDFLARE_ACCOUNT_ID", ""
        ).strip()
        self.cloudflare_api_token = os.getenv(
            "CLOUDFLARE_API_TOKEN", ""
        ).strip()
        self.embedding_model = os.getenv(
            "EMBEDDING_MODEL",
            "@cf/baai/bge-base-en-v1.5",
        )
        self.embedding_dimensions = 768

    async def embed(self, text: str) -> list[float]:
        """Generate embeddings using Cloudflare Workers AI."""
        if not self.cloudflare_account_id or not self.cloudflare_api_token:
            raise RuntimeError(
                "CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN "
                "must be configured in Railway."
            )

        url = (
            "https://api.cloudflare.com/client/v4/accounts/"
            f"{self.cloudflare_account_id}/ai/run/"
            f"{self.embedding_model}"
        )

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.cloudflare_api_token}",
                    "Content-Type": "application/json",
                },
                json={"text": [text]},
            )
            response.raise_for_status()
            data = response.json()

        if not data.get("success", False):
            raise RuntimeError(
                f"Cloudflare embedding request failed: "
                f"{data.get('errors', 'Unknown error')}"
            )

        result = data.get("result") or {}
        vectors = result.get("data") or result.get("embeddings") or []

        if not vectors:
            raise RuntimeError(
                "Cloudflare returned no embedding vectors."
            )

        vector = vectors[0]

        if len(vector) != self.embedding_dimensions:
            raise ValueError(
                f"Expected {self.embedding_dimensions} dimensions from "
                f"{self.embedding_model}, received {len(vector)}."
            )

        return [float(value) for value in vector]

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
