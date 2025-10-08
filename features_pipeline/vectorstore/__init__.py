from abc import abstractmethod, ABC
from enum import Enum


class VectorStoreType(str, Enum):
    CHROMA = 'CHROMA'
    QDRANT = 'QDRANT'

class VectorStore(ABC):
    """Abstract base class for a vector store."""
    @abstractmethod
    def add_vector(self, vector_id: str, vector: list[float], metadata: dict[str, Any] = None):
        pass

    @abstractmethod
    def query(self, vector: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        pass
