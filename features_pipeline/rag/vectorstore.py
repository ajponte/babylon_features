"""
Vector Store.

A vector store is a specialized database which stores vectors
of high dimensionality.

"""
from abc import ABC, abstractmethod
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from features_pipeline.error import VectorDBError
from features_pipeline.logger import get_logger

DEFAULT_TOP_K = 5

_LOGGER = get_logger(__name__)


# A `SimilarEmbeddingRecord` is the return type of
# Vector DB similarity search. It is a 2 element tuple
# of a document from the search and its "score".
#
# WLOG, a "score" of a document is the distance/magnitude
# of an input query and the document, as embedded by a given model.
type SimilarEmbeddingRecord = tuple[Document, float]

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
    def similarity_search(self, query_text, top_k: int = DEFAULT_TOP_K) -> SimilarEmbeddingRecord:
        """
        Perform a similarity search using the top-k method, which selects the
        top `k` most probable (wrt similarity) tokens.

        :param query_text: Unstructured text to search.
        :param top_k: Top K.
        :return: Top k similar embeddings.
        """
        pass

class ChromaVectorStore(VectorStore):
    """
    Chroma Vector Store. This vector store uses sqlite
    as its persistence layer.
    """
    def __init__(
        self,
        model: str,
        config: dict
    ):
        """
        Constructor.

        :param model: Target model.
        :param config: Chroma config.
        """
        super().__init__(model)
        self._vector_db = self.__configure_chroma(config)

    def similarity_search(self, query_text, top_k: int = DEFAULT_TOP_K) -> list[SimilarEmbeddingRecord]:
        """
        Perform similarity search on Chroma.

        :param query_text: Query text.
        :param top_k: Top-k.
        :return: List of langchain `Document` results from Chroma.
        """
        _LOGGER.info(f"Running similarity search for query: '{query_text}', (k={top_k})")
        try:
            results = self._vector_db.similarity_search_with_score(query_text, k=top_k)
            _LOGGER.info('Successfully searched vector db embeddings for query.')
            _LOGGER.debug(f'results: {len(results)}')
            return results
        except Exception as e:
            message = 'failed to fetch results from vector db'
            _LOGGER.info(message)
            _LOGGER.debug(f'Failed query: {query_text}')
            raise VectorDBError(message=message, cause=e) from e

    def __configure_chroma(self, config: dict) -> Chroma:
        """
        Return a newly configured Chroma.

        :param config: Config dict.
        :return: Chroma.
        """
        collection_name = config['EMBEDDINGS_COLLECTION_CHROMA']
        sqlite_dir = config['CHROMA_SQLITE_DIR']

        try:
            return Chroma(
                collection_name=collection_name,
                embedding_function=self.model,
                persist_directory=sqlite_dir
            )
        except Exception as e:
            message = "Failed to connect to Chroma on disk"
            _LOGGER.exception("Failed to connect to Chroma on disk")
            raise VectorDBError(message, cause=e) from e


def embeddings(model: str, device: str = 'cpu') -> HuggingFaceEmbeddings:
    """
    Return an instantiated model.

    :param model: Model name.
    :param device: (Optional) Target device type.
    :return: Instantiated `HuggingFaceEmbeddings` object with given model.
    """
    match model:
        case 'BAAI/bge-small-en-v1.5':
            _LOGGER.info(f'Instantiating HuggingFaceEmbeddings with model {model}')
            embedding_model = HuggingFaceEmbeddings(
                model_name=model,
                model_kwargs={'device': device},
                encode_kwargs={'normalize_embeddings': True}
            )
            return embedding_model
        case _:
            raise ValueError(f'Unknown model: {model}')
