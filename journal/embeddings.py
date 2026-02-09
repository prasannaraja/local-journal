import chromadb

from journal.config import CHROMA_DIR, CHROMA_COLLECTION, DATA_DIR
from journal.llm import embed


_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None


def _get_collection() -> chromadb.Collection:
    global _client, _collection
    if _collection is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = _client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def store_entry(entry_id: int, text: str, metadata: dict):
    """Embed and store a journal entry."""
    col = _get_collection()
    embedding = embed(text)
    col.upsert(
        ids=[str(entry_id)],
        embeddings=[embedding],
        documents=[text],
        metadatas=[metadata],
    )


def search_entries(query: str, n_results: int = 5) -> list[dict]:
    """Search for similar entries. Returns list of {id, document, metadata, distance}."""
    col = _get_collection()
    if col.count() == 0:
        return []
    query_embedding = embed(query)
    results = col.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, col.count()),
    )
    entries = []
    for i in range(len(results["ids"][0])):
        entries.append({
            "id": int(results["ids"][0][i]),
            "document": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return entries


def delete_entry(entry_id: int):
    """Remove an entry from the vector store."""
    col = _get_collection()
    try:
        col.delete(ids=[str(entry_id)])
    except Exception:
        pass
