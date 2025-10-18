from typing import Any

from features_pipeline.logger import get_logger
from features_pipeline.rag.documents.document_manager import BabylonDocumentsManager


_LOGGER = get_logger()

class Processor:
    def __init__(self, config: dict[str, Any]):
        self._documents_manager = BabylonDocumentsManager(config)

    def process_collection(self, collection: str):
        _LOGGER.info(f'Processing collection {collection}')
        self._documents_manager.build_documents(collection=collection)
        _LOGGER.info(f'Finished processing collection {collection}')
