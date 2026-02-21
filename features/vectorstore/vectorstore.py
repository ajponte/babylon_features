"""
Vector Store.

A vector store is a specialized database which stores vectors
of high dimensionality.

"""

from abc import ABC, abstractmethod
from typing import Any
from langchain_chroma import Chroma
from langchain_qdrant import QdrantVectorStore as LangchainQdrant
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from features.error import VectorDBError
from features.logger import get_logger

# Top K results from cosine similarity search.
DEFAULT_TOP_K = 5

# The max number of vectors to return per query.
DEFAULT_MAX_VECTORS_SEARCH = 10000

_LOGGER = get_logger()


# A `SimilarEmbeddingRecord` is the return type of
# Vector DB similarity search. It is a 2 element tuple
# of a document from the search and its "score".
#
# WLOG, a "score" of a document is the distance/magnitude
# of an input query and the document, as embedded by a given model.
SimilarEmbeddingRecord = tuple[Document, float]


class VectorStore(ABC):
    """
    A Generic Vector Store. A `VectorStore` uses an embedding model
    to encode unstructured text from the data lake.
    """

    def __init__(self, model: str):
        self._model = embeddings(model)

    @property
    def model(self):
        """
        Return this VectorStore's embedding model instance.

        :return: Embedding model instance.
        """
        return self._model

    @abstractmethod
    def similarity_search(
        self, query_text, top_k: int = DEFAULT_TOP_K
    ) -> list[SimilarEmbeddingRecord]:
        """
        Perform a similarity search using the top-k method, which selects the
        top `k` most probable (wrt similarity) tokens.

        :param query_text: Unstructured text to search.
        :param top_k: Top K.
        :return: Top k similar embeddings.
        """

    @abstractmethod
    def bulk_find(
        self, collection_name: str, limit: int, offset: int | str | None, **kwargs
    ) -> Any:
        """
        Bulk-search the collection, starting at a specific `offset`.

        :param collection_name: Collection name.
        :param limit: Search limit.
        :param offset: Search offset.
        """

    @abstractmethod
    def search_collection(
        self, collection_name: str, query_vector: list, limit: int, **kwargs
    ) -> list:
        """
        Search a Vectorstore collection.

        :param collection_name: Collection Name.
        :param query_vector: Query vector to match.
        :param limit: Max vectors to search.
        :return: List of vectors.
        """

    @abstractmethod
    def add_documents(self, documents: list[Document]) -> None:
        """
        Add documents to the vector store.

        :param: Documents to add.
        """

    @abstractmethod
    def get_all(self, limit: int) -> dict[str, list]:
        """
        Return all embeddings, documents, and metadata from the store.

        :return: A dictionary containing 'embeddings', 'documents', and 'metadatas'.
        """


class ChromaVectorStore(VectorStore):
    """
    Chroma Vector Store. This vector store uses sqlite
    as its persistence layer.
    """

    def __init__(self, model: str, sqlite_dir: str, collection: str):
        """
        Constructor.

        :param model: Target model.
        """
        super().__init__(model)
        self._chroma_api_client: Chroma = self.__configure_chroma(
            sqlite_dir=sqlite_dir, collection_name=collection
        )

    @property
    def db_client(self) -> Chroma:
        """
        Return Chroma DB client.

        :return: Chroma DB client.
        """
        return self._chroma_api_client

    def add_documents(self, documents: list[Document]) -> None:
        """Add langchain documents to chroma."""
        _LOGGER.info("Adding documents to vector DB")
        try:
            self._chroma_api_client.add_documents(documents)
        except Exception as e:
            message = "Error while adding documents to Chroma"
            _LOGGER.info(message)
            raise VectorDBError(message=message, cause=e) from e

    def similarity_search(
        self, query_text, top_k: int = DEFAULT_TOP_K
    ) -> list[SimilarEmbeddingRecord]:
        """
        Perform similarity search on Chroma.

        :param query_text: Query text.
        :param top_k: Top-k.
        :return: List of langchain `Document` results from Chroma.
        """
        _LOGGER.info(
            f"Running similarity search for query: '{query_text}', (k={top_k})"
        )
        try:
            results = self._chroma_api_client.similarity_search_with_score(
                query_text, k=top_k
            )
            _LOGGER.info("Successfully searched vector db embeddings for query.")
            _LOGGER.debug(f"results: {len(results)}")
            return results
        except Exception as e:
            message = "failed to fetch results from vector db"
            _LOGGER.info(message)
            _LOGGER.debug(f"Failed query: {query_text}")
            raise VectorDBError(message=message, cause=e) from e

    def search_collection(
        self, collection_name: str, query_vector: list, limit: int, **kwargs
    ) -> list:
        raise NotImplementedError("Not implemented for Chroma.")

    def bulk_find(
        self, collection_name: str, limit: int, offset: int | str | None, **kwargs
    ) -> Any:
        raise NotImplementedError("Not implemented for Chroma")

    def get_all(self, limit: int = DEFAULT_MAX_VECTORS_SEARCH) -> dict[str, list]:
        """
        Fetch all data from Chroma. Only for testing.
        """
        try:
            # Fetches all data and includes all necessary fields
            results = self._chroma_api_client.get(
                include=["embeddings", "documents", "metadatas"], limit=limit
            )
            return {
                "embeddings": results.get("embeddings", []),
                "documents": results.get("documents", []),
                "metadatas": results.get("metadatas", []),
            }
        except Exception as e:
            message = "Failed to fetch all records from Chroma"
            _LOGGER.exception(message)
            raise VectorDBError(message, cause=e) from e

    def __configure_chroma(self, sqlite_dir: str, collection_name: str) -> Chroma:
        """
        Return a newly configured Chroma.

        :return: Chroma.
        """

        try:
            return Chroma(
                collection_name=collection_name,
                embedding_function=self.model,
                persist_directory=sqlite_dir,
            )
        except Exception as e:
            message = "Failed to connect to Chroma on disk"
            _LOGGER.exception("Failed to connect to Chroma on disk")
            raise VectorDBError(message, cause=e) from e


class QdrantVectorStore(VectorStore):
    """
    Qdrant Vector Store.
    """

    def __init__(
        self,
        model: str,
        host: str,
        port: int,
        collection: str,
    ):
        """
        Constructor.

        :param model: Target model.
        :param host: Qdrant host.
        :param port: Qdrant port.
        :param collection: Qdrant collection name.
        """
        super().__init__(model)
        self._qdrant_client = self.__configure_qdrant(
            host=host,
            port=port,
            collection_name=collection,
        )

    def add_documents(self, documents: list[Document]) -> None:
        """Add langchain documents to Qdrant."""
        _LOGGER.info("Adding documents to Qdrant")
        try:
            self._qdrant_client.add_documents(documents)
        except Exception as e:
            message = "Error while adding documents to Qdrant"
            _LOGGER.info(message)
            raise VectorDBError(message=message, cause=e) from e

    def similarity_search(
        self, query_text, top_k: int = DEFAULT_TOP_K
    ) -> list[SimilarEmbeddingRecord]:
        """
        Perform similarity search on Qdrant.

        :param query_text: Query text.
        :param top_k: Top-k.
        :return: List of langchain `Document` results from Qdrant.
        """
        _LOGGER.info(
            f"Running similarity search for query: '{query_text}', (k={top_k})"
        )
        try:
            results = self._qdrant_client.similarity_search_with_score(
                query_text, k=top_k
            )
            _LOGGER.info("Successfully searched Qdrant embeddings for query.")
            return results
        except Exception as e:
            message = "failed to fetch results from Qdrant"
            _LOGGER.info(message)
            raise VectorDBError(message=message, cause=e) from e

    def bulk_find(
        self, collection_name: str, limit: int, offset: int | str | None, **kwargs
    ) -> tuple[list, str]:
        with_payload = kwargs.pop("with_payload", True)
        with_vectors = kwargs.pop("with_vectors", False)

        records, next_offset = self._qdrant_client.client.scroll(
            collection_name=collection_name,
            limit=limit,
            with_payload=with_payload,
            with_vectors=with_vectors,
            offset=offset,
            **kwargs,
        )

        return records, next_offset  # type: ignore

    def search_collection(
        self,
        collection_name: str,
        query_vector: list,
        limit: int = DEFAULT_MAX_VECTORS_SEARCH,
        **kwargs,
    ) -> list:
        with_payload = kwargs.pop("with_payload", True)
        with_vectors = kwargs.pop("with_vectors", False)
        try:
            records = self._qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                with_payload=with_payload,
                with_vectors=with_vectors,
                **kwargs,
            )
        except Exception as e:
            msg = f"Error while searching Qdrant. Error: {e}"
            raise VectorDBError(message=msg, cause=e) from e

        return records

    def get_all(self, limit: int = DEFAULT_MAX_VECTORS_SEARCH) -> dict[str, list]:
        """
        Fetch all data from Qdrant.
        """
        try:
            # We use the underlying qdrant client to scroll through all points.
            # For simplicity in visualization, we might limit this or implement pagination if huge.
            # Using a large limit for now as visualize.py seems to expect everything.
            points, _ = self._qdrant_client.client.scroll(
                collection_name=self._qdrant_client.collection_name,
                limit=10000,
                with_payload=True,
                with_vectors=True,
            )

            embeddings_list = []
            documents = []
            metadatas = []

            for point in points:
                if point.vector:
                    embeddings_list.append(point.vector)
                    # Langchain Qdrant stores page_content in payload['page_content']
                    page_content = ""
                    metadata = {}
                    if point.payload:
                        page_content = point.payload.get("page_content", "")
                        metadata = point.payload.get("metadata", {})
                    documents.append(page_content)
                    metadatas.append(metadata)

            return {
                "embeddings": embeddings_list,
                "documents": documents,
                "metadatas": metadatas,
            }
        except Exception as e:
            message = "Failed to fetch all records from Qdrant"
            _LOGGER.exception(message)
            raise VectorDBError(message, cause=e) from e

    def __configure_qdrant(
        self,
        host: str,
        port: int,
        collection_name: str,
    ) -> LangchainQdrant:
        """
        Return a newly configured Qdrant client.

        :return: LangchainQdrant client if `langchain` is enabled, otherwise `Qdrant`.
        """
        try:
            client = QdrantClient(url=f"http://{host}:{port}")
            # Ensure collection exists
            if not client.collection_exists(collection_name):
                _LOGGER.info(f"Creating Qdrant collection: {collection_name}")
                # bge-small-en-v1.5 has 384 dimensions
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=384, distance=qmodels.Distance.COSINE
                    ),
                )
            return LangchainQdrant(
                client=client,
                collection_name=collection_name,
                embedding=self.model,
            )
        except Exception as e:
            message = f"Failed to connect to Qdrant at {host}:{port}"
            _LOGGER.exception(message)
            raise VectorDBError(message, cause=e) from e


def vector_store_factory(config: dict[str, Any]) -> VectorStore:
    """
    Return a VectorStore instance based on the configuration.

    :param config: Configuration dictionary.
    :return: VectorStore instance.
    """
    vector_db_type = config.get("VECTOR_DB_TYPE", "chroma").lower()
    model = config["EMBEDDING_MODEL"]

    match vector_db_type:
        case "chroma":
            return ChromaVectorStore(
                model=model,
                sqlite_dir=config["CHROMA_SQLITE_DIR"],
                collection=config["EMBEDDINGS_COLLECTION_CHROMA"],
            )
        case "qdrant":
            return QdrantVectorStore(
                model=model,
                host=config["QDRANT_HOST"],
                port=config["QDRANT_PORT"],
                collection=config["QDRANT_COLLECTION"],
            )
        case _:
            raise ValueError(f"Unknown Vector DB type: {vector_db_type}")


def embeddings(model: str, device: str = "cpu") -> HuggingFaceEmbeddings:
    """
    Return an instantiated model.

    :param model: Model name.
    :param device: (Optional) Target device type.
    :return: Instantiated `HuggingFaceEmbeddings` object with given model.
    """
    match model:
        case "BAAI/bge-small-en-v1.5":
            _LOGGER.info(f"Instantiating HuggingFaceEmbeddings with model {model}")
            embedding_model = HuggingFaceEmbeddings(
                model_name=model,
                model_kwargs={"device": device},
                encode_kwargs={"normalize_embeddings": True},
            )
            return embedding_model
        case _:
            raise ValueError(f"Unknown model: {model}")
