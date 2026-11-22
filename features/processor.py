"""Process data lake records."""

from abc import ABC, abstractmethod
from collections.abc import Iterable

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from features.datalake.repository import BaseRepository, TransactionDto
from features.error import RAGError
from features.logger import get_logger
from features.rag.documents.document_builder import build_langchain_document
from features.vectorstore.vectorstore import VectorStore

_LOGGER = get_logger()


class DataLakeProcessor(ABC):
    """
    A DatalakeProcessor processes records from a Data Lake collection.
    To process a record from the Data Lake, the processor will embed
    the data and persist in the vector store.
    """

    def __init__(self, vector_store: VectorStore):
        """
        Constructor.

        :param vector_store: Configured vector store.
        """
        self._batch_number = 0
        self._vector_store = vector_store

    @abstractmethod
    def process(self, mongo_repository: BaseRepository) -> None:
        """
        Process all records in a target repository.

        :param mongo_repository: Target repository.
        """

    @property
    def batch_number(self) -> int:
        """
        Return the current batch number.

        :return: The current batch number.
        """
        return self._batch_number


def chunk_transactions(
    transactions: Iterable[TransactionDto],
    collection_name: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 100,
) -> list[Document]:
    """Build and split one LangChain document per transaction.

    Records that fail to build or split are logged at warning level and skipped (P2-D3).

    :param transactions: An iterable of TransactionDto records.
    :param collection_name: Collection name stored in document metadata.
    :param chunk_size: Maximum characters per chunk (default 1000).
    :param chunk_overlap: Character overlap between chunks (default 100).
    :return: List of chunked LangChain Document objects.
    :raises TypeError: If transactions is None, or chunk_size/chunk_overlap
        is not an int (or is bool).
    :raises ValueError: If collection_name is empty/whitespace, chunk_size <= 0,
        chunk_overlap < 0, or chunk_overlap >= chunk_size.
    """
    if transactions is None:
        raise TypeError("transactions cannot be None")
    if not isinstance(collection_name, str) or not collection_name.strip():
        raise ValueError("collection_name must be a non-empty string")
    if isinstance(chunk_size, bool) or not isinstance(chunk_size, int):
        raise TypeError(
            f"chunk_size must be an integer, got: {type(chunk_size).__name__}"
        )
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be a positive integer, got: {chunk_size}")
    if isinstance(chunk_overlap, bool) or not isinstance(chunk_overlap, int):
        raise TypeError(
            f"chunk_overlap must be an integer, got: {type(chunk_overlap).__name__}"
        )
    if chunk_overlap < 0:
        raise ValueError(f"chunk_overlap must be non-negative, got: {chunk_overlap}")
    if chunk_overlap >= chunk_size:
        raise ValueError(
            f"chunk_overlap ({chunk_overlap}) must be strictly less than chunk_size ({chunk_size})"
        )

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
    )

    all_chunks: list[Document] = []
    for transaction in transactions:
        try:
            doc = build_langchain_document(
                source=transaction, collection=collection_name
            )
            chunks = text_splitter.split_documents([doc])
            all_chunks.extend(chunks)
        except (ValueError, TypeError, KeyError, RAGError) as e:
            record_id = getattr(transaction, "id", None) or "unknown"
            _LOGGER.warning(
                "Error while building/chunking document for record %s: %s",
                record_id,
                e,
            )
            _LOGGER.debug(
                "Data error details for record %s",
                record_id,
                exc_info=True,
            )
            continue
        except Exception as e:
            record_id = getattr(transaction, "id", None) or "unknown"
            _LOGGER.error(
                "Unexpected error while building/chunking document for record %s: %s",
                record_id,
                e,
                exc_info=True,
            )
            continue

    return all_chunks


class CollectionProcessor(DataLakeProcessor):
    """
    A processor will consume records from a collection in the data lake
    and store embeddings in the vector store.
    """

    def process(self, mongo_repository: BaseRepository) -> None:
        """
        Process data in the mongo repo, embed the data,
        and persist in the vector store.

        :param mongo_repository: TransactionRepository.
        """
        self.__update_batch_number()
        collection_name = mongo_repository.collection.name
        transactions = mongo_repository.get_by_filter({})

        all_chunks = chunk_transactions(transactions, collection_name)

        if all_chunks:
            _LOGGER.info("Adding %d chunks to vector store", len(all_chunks))
            self._vector_store.add_documents(all_chunks)
        else:
            _LOGGER.info("No documents to add to vector store")

    def __update_batch_number(self) -> None:
        """Update the current batch number."""
        _LOGGER.info("Bumping up batch number to %d", self._batch_number)
        self._batch_number += 1
