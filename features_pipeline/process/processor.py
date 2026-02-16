"""Process data lake records."""
from langchain_core.documents import Document

from datalake.repository import BaseRepository
from features_pipeline.logger import get_logger
from features_pipeline.process.datalake import DataLakeProcessor
from features_pipeline.rag.documents.document_builder import build_langchain_document

_LOGGER = get_logger()


class Mongo(DataLakeProcessor):
    """
    A processor which will consume records from a mongo collection in
    the data lake and store embeddings in the vector store.
    """

    def process(self, mongo_repository: BaseRepository) -> int:
        """
        Process data in the mongo repo, embed the data,
        and persist in the vector store.

        :param mongo_repository: TransactionRepository.
        :return: The number of documents processed.
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
        return len(documents)

    def __update_batch_number(self) -> None:
        """Update the current batch number."""
        _LOGGER.info(f"Bumping up batch number to {self._batch_number}")
        self._batch_number += 1
