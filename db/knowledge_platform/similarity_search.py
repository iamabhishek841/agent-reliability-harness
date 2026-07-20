import os
import sys

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from sentence_transformers import SentenceTransformer

query = " ".join(sys.argv[1:]) or "Can I refund a delivered order after ten days?"
dsn = os.getenv("KNOWLEDGE_DATABASE_URL", "postgresql://knowledge:knowledge@localhost:5434/knowledge_platform")
model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
embedding = SentenceTransformer(model_name).encode(query, normalize_embeddings=True).tolist()
with psycopg.connect(dsn, row_factory=dict_row) as connection:
    register_vector(connection)
    rows = connection.execute("SELECT pd.document_key,pd.title,pc.content,1-(pc.embedding <=> %s) similarity FROM policy_chunks pc JOIN policy_documents pd USING(document_id) ORDER BY pc.embedding <=> %s LIMIT 5", (embedding, embedding)).fetchall()
    for row in rows:
        print(f"{row['similarity']:.3f} {row['document_key']}: {row['title']}")

