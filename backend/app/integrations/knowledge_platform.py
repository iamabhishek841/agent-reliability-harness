import os
from functools import lru_cache
from typing import Any

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

from backend.app.integrations.faults import IntegrationUnavailable, apply_faults


@lru_cache(maxsize=2)
def _embedding_model(model_name: str):
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=model_name, cache_dir=os.getenv("FASTEMBED_CACHE_PATH"))


class KnowledgePlatformClient:
    def __init__(self, database_url: str, embedding_model: str, timeout_seconds: float = 4.0):
        self.database_url = database_url
        self.embedding_model = embedding_model
        self.timeout_seconds = timeout_seconds

    def search(self, query: str, limit: int = 4) -> list[dict[str, Any]]:
        stale_hours = apply_faults("knowledge_platform", self.timeout_seconds)
        try:
            embedding = next(iter(_embedding_model(self.embedding_model).embed([query]))).tolist()
            with psycopg.connect(self.database_url, connect_timeout=max(1, int(self.timeout_seconds)), row_factory=dict_row) as connection:
                register_vector(connection)
                rows = connection.execute(
                    """
                    SELECT pc.chunk_id, pd.document_key, pd.title, pc.content,
                           pc.source_version, pc.effective_at, pc.synced_at,
                           1 - (pc.embedding <=> %s) AS similarity
                    FROM policy_chunks pc
                    JOIN policy_documents pd ON pd.document_id = pc.document_id
                    WHERE pc.effective_at <= now() - (%s * interval '1 hour')
                      AND (pd.retired_at IS NULL OR pd.retired_at > now() - (%s * interval '1 hour'))
                    ORDER BY pc.embedding <=> %s
                    LIMIT %s
                    """,
                    (embedding, stale_hours, stale_hours, embedding, limit),
                ).fetchall()
        except psycopg.Error as exc:
            raise IntegrationUnavailable("knowledge_platform", "database_error", str(exc)) from exc
        except Exception as exc:
            raise IntegrationUnavailable("knowledge_platform", "embedding_error", str(exc)) from exc
        return [{**dict(row), "similarity": round(float(row["similarity"]), 4), "stale_hours": stale_hours} for row in rows]

    def health(self) -> bool:
        try:
            with psycopg.connect(self.database_url, connect_timeout=2) as connection:
                return connection.execute("SELECT 1").fetchone() == (1,)
        except psycopg.Error:
            return False
