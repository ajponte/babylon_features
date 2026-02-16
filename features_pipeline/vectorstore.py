"""
Vector Store.

A vector store is a specialized database which stores vectors
of high dimensionality.

"""

from abc import ABC, abstractmethod
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
import os

from features_pipeline.error import VectorDBError
from features_pipeline.logger import get_logger

DEFAULT_TOP_K = 5

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
    def add_documents(self, documents: list[Document]) -> None:
        """
        Add documents to the vector store.

        :param: Documents to add.
        """


class ChromaVectorStore(VectorStore):
    """
    Chroma Vector Store. This vector store uses sqlite
    as its persistence layer.
    """

    def __init__(
        self,
        model: str,
        collection: str,
        sqlite_dir: str | None = None,
        host: str | None = None,
        port: int | None = None,
    ):
        """
        Constructor.

        :param model: Target model.
        """
        super().__init__(model)
        self._chroma_api_client, self._chroma_native_client = self.__configure_chroma(
            sqlite_dir=sqlite_dir, collection_name=collection, host=host, port=port
        )

    @property
    def db_client(self) -> Chroma:
        """
        Return Langchain Chroma DB client.

        :return: Langchain Chroma DB client.
        """
        return self._chroma_api_client

    @property
    def native_client(self) -> chromadb.Client:
        """
        Return the native chromadb client.

        :return: The native chromadb client.
        """
        return self._chroma_native_client
        
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

    def __configure_chroma(
        self,
        sqlite_dir: str | None,
        collection_name: str,
        host: str | None,
        port: int | None,
    ) -> tuple[Chroma, chromadb.Client]:
        """
        Return a newly configured Chroma client and the underlying native client.

        :return: A tuple of (Chroma, chromadb.Client).
        """
        _LOGGER.info(f"Attempting to connect to Chroma with sqlite_dir='{sqlite_dir}', host='{host}', port='{port}'")
        try:
            if sqlite_dir:
                _LOGGER.info(f"Connecting to Chroma using persist_directory: {sqlite_dir}")
                chroma_langchain = Chroma(
                    collection_name=collection_name,
                    embedding_function=self.model,
                    persist_directory=sqlite_dir,
                )
                return chroma_langchain, chroma_langchain._client
            elif host and port:
                _LOGGER.info(f"Connecting to remote Chroma server at {host}:{port} using chromadb.Client with Settings")
                settings = Settings(
                    chroma_server_host=host,
                    chroma_server_http_port=str(port),
                )
                chroma_native_client = chromadb.Client(settings=settings)
                chroma_langchain = Chroma(
                    collection_name=collection_name,
                    embedding_function=self.model,
                    client=chroma_native_client,
                )
                return chroma_langchain, chroma_native_client
            else:
                _LOGGER.warning("No sqlite_dir or host/port provided. Connecting to in-memory Chroma.")
                # For in-memory, a native client is not explicitly created first,
                # but the Langchain Chroma object creates one internally.
                chroma_langchain = Chroma(
                    collection_name=collection_name,
                    embedding_function=self.model,
                )
                return chroma_langchain, chroma_langchain._client
        except Exception as e:
            message = "Failed to connect to Chroma"
            _LOGGER.exception(message)
            raise VectorDBError(message, cause=e) from e


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
            # Check if TOKENIZERS_PARALLELISM is set, if not, set it to false to avoid warnings
            if os.environ.get("TOKENIZERS_PARALLELISM") is None:
                _LOGGER.warning("TOKENIZERS_PARALLELISM not set, setting to 'false' to suppress warnings.")
                os.environ["TOKENIZERS_PARALLELISM"] = "false"
            embedding_model = HuggingFaceEmbeddings(
                model_name=model,
                model_kwargs={"device": device},
                encode_kwargs={"normalize_embeddings": True},
            )
            return embedding_model
        case _:
            raise ValueError(f"Unknown model: {model}")
