"""Entry point for processing a datalake collection."""

from typing import Any

from features_pipeline.logger import get_logger
from features_pipeline.rag.documents.document_manager import BabylonDocumentsManager


_LOGGER = get_logger()


# pylint: disable=too-few-public-methods
class Processor:
    """
    A Processor processes a datalake collection and persists
    vector embeddings in a vector store.
    """

    def __init__(self, config: dict[str, Any]):
        """
        Constructor.

        :param config: Processor config.
        """
        self._documents_manager = BabylonDocumentsManager(config)

    def process_collection(self, collection: str):
        """
        Process a collection of datalake records.

        :param collection: Datalake collection name.
        """
        try:
            _LOGGER.info(f"Processing collection {collection}")
            self._documents_manager.build_documents(collection=collection)
            _LOGGER.info(f"Finished processing collection {collection}")
        except Exception as e:
            raise RuntimeError(f"Unknown error: {e}") from e
