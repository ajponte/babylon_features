"""Vector Store factory creational pattern."""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from features_pipeline.vectorstore import VectorStore, VectorStoreType
from features_pipeline.vectorstore.chroma import ChromaVectorStore


class VectorStoreFactory:
    """Factory for generating unique vector stores."""
    @staticmethod
    def create(store_type: VectorStoreType, **kwargs) -> VectorStore:
        if store_type == VectorStoreType.CHROMA:
            return ChromaVectorStore(**kwargs)
        if store_type == VectorStoreType.QDRANT:
            raise NotImplementedError(f'{store_type} not yet implemented.')

        raise ValueError(f'Unknown store type: {store_type}')
