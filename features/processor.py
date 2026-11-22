"""Process data lake records."""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

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
        """Constructor.

        :param vector_store: Configured vector store.
        """
        self._batch_number = 0
        self._vector_store = vector_store

    @abstractmethod
    def process(self, mongo_repository: BaseRepository) -> None:
        """Process all records in a target repository.

        :param mongo_repository: Target repository.
        """

    @property
    def batch_number(self) -> int:
        """Return the current batch number.

        :return: The current batch number.
        """
        return self._batch_number


def _validate_chunking_params(
    transactions: Any,
    collection_name: Any,
    chunk_size: Any,
    chunk_overlap: Any,
) -> None:
    """Validate parameter boundaries and types before processing.

    :raise TypeError: If parameters violate expected types or if booleans are supplied.
    :raise ValueError: If parameter values violate range or relationship invariants.
    """
    # Guard against null collections and transactions
    if transactions is None:
        raise TypeError("transactions cannot be None")
    if not isinstance(collection_name, str) or not collection_name.strip():
        raise ValueError("collection_name must be a non-empty string")

    # Strict type guard: reject booleans since bool inherits from int in Python
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

    # Overlap must be strictly less than chunk_size to ensure forward progress
    if chunk_overlap >= chunk_size:
        raise ValueError(
            f"chunk_overlap ({chunk_overlap}) must be strictly less than chunk_size ({chunk_size})"
        )


def _create_text_splitter(
    chunk_size: int,
    chunk_overlap: int,
) -> RecursiveCharacterTextSplitter:
    """Instantiate a RecursiveCharacterTextSplitter with lineage auditing enabled.

    :param chunk_size: Maximum characters per chunk.
    :param chunk_overlap: Character overlap between adjacent chunks.
    :return: Configured RecursiveCharacterTextSplitter.
    """
    # add_start_index captures character offset for lineage provenance
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
    )


def _chunk_single_transaction(
    transaction: TransactionDto,
    collection_name: str,
    text_splitter: RecursiveCharacterTextSplitter,
) -> list[Document]:
    """Build and split a LangChain document for a single transaction record.

    Encapsulates per-record fault containment: skips invalid records and logs diagnostics.

    :param transaction: Source TransactionDto record.
    :param collection_name: Source collection name for metadata.
    :param text_splitter: Configured LangChain text splitter.
    :return: List of generated chunk documents, or empty list on failure.
    """
    try:
        # P2-D3: Build document and split into chunks
        doc = build_langchain_document(source=transaction, collection=collection_name)
        return text_splitter.split_documents([doc])
    except (ValueError, TypeError, KeyError, RAGError) as err:
        record_id = getattr(transaction, "id", None) or "unknown"
        _LOGGER.warning(
            "Error while building/chunking document for record %s: %s",
            record_id,
            err,
        )
        _LOGGER.debug("Data error details for record %s", record_id, exc_info=True)
        return []
    except Exception as err:
        record_id = getattr(transaction, "id", None) or "unknown"
        _LOGGER.error(
            "Unexpected error while building/chunking document for record %s: %s",
            record_id,
            err,
            exc_info=True,
        )
        return []


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
    _validate_chunking_params(transactions, collection_name, chunk_size, chunk_overlap)
    text_splitter = _create_text_splitter(chunk_size, chunk_overlap)

    all_chunks: list[Document] = []
    for transaction in transactions:
        chunks = _chunk_single_transaction(transaction, collection_name, text_splitter)
        all_chunks.extend(chunks)

    return all_chunks


class CollectionProcessor(DataLakeProcessor):
    """A processor that consumes data lake records and stores embeddings in the vector store."""

    def process(self, mongo_repository: BaseRepository) -> None:
        """Process data in the mongo repo, embed the data, and persist in the vector store.

        :param mongo_repository: TransactionRepository.
        :raises TypeError: If mongo_repository is None.
        """
        if mongo_repository is None:
            raise TypeError("mongo_repository cannot be None")

        self._update_batch_number()
        collection_name = mongo_repository.collection.name
        transactions = mongo_repository.get_by_filter({})

        all_chunks = chunk_transactions(transactions, collection_name)

        # Early return guard flattens execution flow
        if not all_chunks:
            _LOGGER.info("No documents to add to vector store")
            return

        _LOGGER.info("Adding %d chunks to vector store", len(all_chunks))
        self._vector_store.add_documents(all_chunks)

    def _update_batch_number(self) -> None:
        """Update the current batch number (protected method for testability)."""
        _LOGGER.info("Bumping up batch number to %d", self._batch_number)
        self._batch_number += 1
