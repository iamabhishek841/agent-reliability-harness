"""Chunk, embed, and idempotently ingest the policy corpus."""

import os
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from fastembed import TextEmbedding
from pgvector.psycopg import register_vector
from psycopg.types.json import Jsonb

DOCS = Path(__file__).with_name("policy_docs")
DSN = os.getenv("KNOWLEDGE_DATABASE_URL", "postgresql://knowledge:knowledge@localhost:5434/knowledge_platform")
MODEL_NAME = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
NAMESPACE = uuid.UUID("8177d9cc-4ecf-4936-b4bf-c04ad9fe39f5")


def chunks(text: str, target_words: int = 375, overlap: int = 50) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    result: list[str] = []
    current: list[str] = []
    count = 0
    for paragraph in paragraphs:
        words = paragraph.split()
        if current and count + len(words) > target_words:
            result.append("\n\n".join(current))
            tail = " ".join(" ".join(current).split()[-overlap:])
            current = [tail] if tail else []
            count = len(tail.split())
        current.append(paragraph)
        count += len(words)
    if current:
        result.append("\n\n".join(current))
    return result


def ingest() -> tuple[int, int]:
    model = TextEmbedding(model_name=MODEL_NAME, cache_dir=os.getenv("FASTEMBED_CACHE_PATH"))
    synced = datetime.now(UTC).replace(microsecond=0)
    document_count = chunk_count = 0
    with psycopg.connect(DSN) as connection:
        register_vector(connection)
        for path in sorted(DOCS.glob("*.md")):
            body = path.read_text(encoding="utf-8")
            title = next((line[2:].strip() for line in body.splitlines() if line.startswith("# ")), path.stem)
            key = path.stem
            document_id = uuid.uuid5(NAMESPACE, key)
            parts = chunks(body)
            embeddings = [embedding.tolist() for embedding in model.embed(parts)]
            connection.execute("""
                INSERT INTO policy_documents (document_id,document_key,title,body_markdown,policy_version,effective_at,synced_at,metadata)
                VALUES (%s,%s,%s,%s,'2025.1','2025-01-01T00:00:00Z',%s,%s)
                ON CONFLICT (document_key) DO UPDATE SET title=excluded.title,body_markdown=excluded.body_markdown,policy_version=excluded.policy_version,synced_at=excluded.synced_at,metadata=excluded.metadata
            """, (document_id, key, title, body, synced, Jsonb({"filename": path.name, "embedding_model": MODEL_NAME})))
            connection.execute("DELETE FROM policy_chunks WHERE document_id=%s", (document_id,))
            for index, (part, embedding) in enumerate(zip(parts, embeddings, strict=True)):
                connection.execute("INSERT INTO policy_chunks (chunk_id,document_id,chunk_index,content,embedding,source_version,effective_at,synced_at) VALUES (%s,%s,%s,%s,%s,'2025.1','2025-01-01T00:00:00Z',%s)", (uuid.uuid5(NAMESPACE, f"{key}:{index}"), document_id, index, part, embedding, synced))
                chunk_count += 1
            document_count += 1
    return document_count, chunk_count


if __name__ == "__main__":
    docs, pieces = ingest()
    print({"documents": docs, "chunks": pieces, "model": MODEL_NAME})
