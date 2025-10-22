"""Process data lake records."""
from abc import ABC, abstractmethod

import os

from datetime import timezone, datetime
from sympy.multipledispatch.dispatcher import source

from datalake.repository import TransactionRepository, BaseRepository, TransactionDto
from features_pipeline.logger import get_logger
from features_pipeline.rag.documents.document_builder import build_langchain_document
from features_pipeline.rag.documents.document_manager import RagCollection
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
    def process(
            self,
            mongo_repository: BaseRepository
    ) -> None:
        ...

    @property
    def batch_number(self) -> int:
        return self._batch_number

class CollectionProcessor(DataLakeProcessor):
    """
    A processor will consume records from a collection in the data lake
    and store embeddings in the vector store.
    """
    def process(
            self,
            transaction_repository: TransactionRepository
    ) -> None:
        """
        Process data in the mongo repo, embed the data,
        and persist in the vector store.

        :param transaction_repository:
        """
        self.__update_batch_number()
        collection_name = transaction_repository.collection.name
        transactions: list[TransactionDto] = transaction_repository.get_by_filter({})
        rag_collection = self.__build_rag_collection()
        for transaction in transactions:
            _LOGGER.info(
                f"Adding new RAG document to RagCollection {rag_collection.pid}"
            )
            try:
                rag_collection.add_documents(
                    [build_langchain_document(source=transaction, collection=collection_name)]
                )
            except Exception as e:
                message = f'Error while building langchain document for record {transaction.id}'
                _LOGGER.info(message)
                continue

        rag_collection.vectorize(self._vector_store)

    def __build_rag_collection(self) -> RagCollection:
        """
        Return a new `RagCollection` object. This method should be called when a new
        document parsing process is needed. The intention of this interface is to manage
        the start of a new document parsing process, which is compute-intensive. As such,
        The PID and start time as a UTC int is recorded in the instantiation of the object.

        :return: A new `RagCollection`.
        """

        def set_rag_process(
            pid: int, start_ts: float, documents: list
        ) -> RagCollection:
            """
            Set the start time and current PID for a RAG process.


            :param pid: Current python PID.
            :param start_ts: PID ts start.
            :param documents: Documents to vectorize.
            """
            if len(documents) > 0:
                raise ValueError(
                    f"Documents must be empty to create a new RAGCollection: {len(documents)}"
                )

            _LOGGER.debug(f"Starting RAG process: {pid} at {now}")
            return RagCollection(pid=pid, _start_ts=start_ts, documents=documents)

        # Create new `RagCollection` for this python process.
        now = datetime.now().astimezone(timezone.utc)
        return set_rag_process(pid=os.getpid(), start_ts=now.timestamp(), documents=[])

    def __update_batch_number(self) -> None:
        _LOGGER.info(f'Bumping up batch number to {self._batch_number}')
        self._batch_number += 1
