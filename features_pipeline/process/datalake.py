from abc import ABC, abstractmethod

from datalake.repository import BaseRepository
from features_pipeline.vectorstore import VectorStore


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
