"""Process data lake records."""

from abc import ABC, abstractmethod

from langchain_core.documents import Document

from datalake.repository import TransactionRepository, BaseRepository, TransactionDto
from features_pipeline.logger import get_logger
from features_pipeline.rag.documents.document_builder import build_langchain_document
from features_pipeline.rag.vectorstore import VectorStore

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
        # The langchain docs we want to vectorize.
        documents: list[Document] = []
        for transaction in transactions:
            try:
                documents.extend(
                    [
                        build_langchain_document(
                            source=transaction, collection=collection_name
                        )
                    ]
                )
            except Exception as e:
                message = f"Error while building langchain document for record {transaction.id}"
                _LOGGER.info(message)
                _LOGGER.debug(f"Error: {e}")
                continue

        self._vector_store.add_documents(documents)

    def __update_batch_number(self) -> None:
        """Update the current batch number."""
        _LOGGER.info(f"Bumping up batch number to {self._batch_number}")
        self._batch_number += 1
