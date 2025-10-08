"""Chroma DB vector store wrapper."""
from typing import Any
from langchain_chroma import Chroma

from features_pipeline.vectorstore import VectorStore


class ChromaVectorStore(VectorStore):
    def __init__(self, collection_name: str):
        import chromadb
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add_vector(self, vector_id: str, vector: list[float], metadata: dict[str, Any] = None):
        self.collection.add(ids=[vector_id], embeddings=[vector], metadatas=[metadata or {}])

    def query(self, vector: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        return self.collection.query(query_embeddings=[vector], n_results=top_k)
