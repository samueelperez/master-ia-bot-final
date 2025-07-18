import os
from sqlalchemy import create_engine, text
# usa la versión community si tienes instalada langchain-community
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.schema import Document

DB_URL = os.getenv("DB_URL")
if not DB_URL:
    raise RuntimeError("Falta DB_URL en .env")

engine = create_engine(DB_URL, pool_pre_ping=True)
with engine.connect() as conn:
    rows = conn.execute(text(
        "SELECT id, params->>'description' AS description FROM strategies"
    )).all()

docs = [
    Document(page_content=row.description or "", metadata={"strategy_id": row.id})
    for row in rows
]

# Instancia tu embedding
emb = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Construye y guarda el índice usando el parámetro correcto
vector_store = FAISS.from_documents(docs, embedding=emb)
vector_store.save_local("faiss_index")

print(f"✔️ Indexado {len(docs)} estrategias en ./faiss_index")
