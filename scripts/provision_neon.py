"""Provision and verify both Neon databases without exposing connection secrets."""

from __future__ import annotations

import os
import runpy
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]


def required_url(name: str) -> str:
    value = os.getenv(name, "")
    if not value.startswith(("postgresql://", "postgres://")):
        raise RuntimeError(f"{name} must be a PostgreSQL connection URL")
    return value


def apply_schema(database_url: str, path: Path) -> None:
    statements = [statement.strip() for statement in path.read_text(encoding="utf-8").split(";") if statement.strip()]
    with psycopg.connect(database_url, autocommit=True) as connection:
        for statement in statements:
            connection.execute(statement)


def scalar(database_url: str, query: str) -> int:
    with psycopg.connect(database_url) as connection:
        row = connection.execute(query).fetchone()
    if row is None:
        raise RuntimeError("Verification query returned no rows")
    return int(row[0])


def main() -> None:
    legacy_url = required_url("LEGACY_DATABASE_URL")
    knowledge_url = required_url("KNOWLEDGE_DATABASE_URL")

    apply_schema(legacy_url, ROOT / "db" / "legacy_crm" / "schema.sql")
    apply_schema(knowledge_url, ROOT / "db" / "knowledge_platform" / "schema.sql")

    legacy_module = runpy.run_path(str(ROOT / "db" / "legacy_crm" / "seed_data.py"))
    knowledge_module = runpy.run_path(str(ROOT / "db" / "knowledge_platform" / "ingest.py"))
    seeded = legacy_module["seed"](reset=False)
    documents, chunks = knowledge_module["ingest"]()

    verified = {
        "customers": scalar(legacy_url, "SELECT count(*) FROM customers"),
        "orders": scalar(legacy_url, "SELECT count(*) FROM orders"),
        "refunds": scalar(legacy_url, "SELECT count(*) FROM refund_requests"),
        "policy_documents": scalar(knowledge_url, "SELECT count(*) FROM policy_documents"),
        "policy_chunks": scalar(knowledge_url, "SELECT count(*) FROM policy_chunks"),
        "embedding_dimensions": scalar(knowledge_url, "SELECT vector_dims(embedding) FROM policy_chunks LIMIT 1"),
    }
    expected = {
        "customers": 122,
        "orders": 140,
        "refunds": 45,
        "policy_documents": 12,
        "embedding_dimensions": 384,
    }
    mismatches = {
        name: (expected_value, verified.get(name))
        for name, expected_value in expected.items()
        if verified.get(name) != expected_value
    }
    if verified["policy_chunks"] < verified["policy_documents"] or mismatches:
        raise RuntimeError(f"Provisioning verification failed: mismatches={mismatches}, counts={verified}")

    print({"seeded": seeded, "ingested_documents": documents, "ingested_chunks": chunks, "verified": verified})


if __name__ == "__main__":
    main()
