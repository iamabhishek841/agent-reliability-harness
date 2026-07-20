CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS policy_documents (
    document_id UUID PRIMARY KEY,
    document_key TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    body_markdown TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    effective_at TIMESTAMPTZ NOT NULL,
    retired_at TIMESTAMPTZ,
    synced_at TIMESTAMPTZ NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS policy_chunks (
    chunk_id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES policy_documents(document_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(384) NOT NULL,
    source_version TEXT NOT NULL,
    effective_at TIMESTAMPTZ NOT NULL,
    synced_at TIMESTAMPTZ NOT NULL,
    UNIQUE(document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS ix_policy_chunks_embedding ON policy_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS ix_policy_documents_key ON policy_documents(document_key);

