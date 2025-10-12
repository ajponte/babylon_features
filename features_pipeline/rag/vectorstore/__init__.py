# no-op
# Currently a no-op. Intent to build generic interface for interoperable vector stores.
import uuid
from abc import abstractmethod, ABC
from enum import Enum
from typing import Any


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

def create_random_uuid_hex() -> str:
    """Returns a randomly generated UUID in hex format."""
    return uuid.uuid4().hex
