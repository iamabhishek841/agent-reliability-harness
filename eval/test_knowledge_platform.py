from pgvector import Vector

from backend.app.integrations.knowledge_platform import _database_vector


def test_query_embedding_uses_pgvector_adapter() -> None:
    embedding = _database_vector([0.0] * 384)

    assert isinstance(embedding, Vector)
    assert embedding.dimensions() == 384
