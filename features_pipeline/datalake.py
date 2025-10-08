"""Abstractions for interacting with the MongoDB datalake."""
import logging
import pymongo

from features_pipeline.document_manager import BabylonDocumentManager

DEFAULT_EMBEDDING_MODEL = 'all-MiniLM-L6-v2'

DATALAKE = 'babylonDataLake'

COLLECTION_NAME_PREFIX = 'chase-data-'

logging.basicConfig(level='DEBUG')
_LOGGER = logging.getLogger(__name__)


class Datalake:
    def __init__(
        self,
        host: str,
        port: str,
        username: str,
        password: str,
        datalake_name: str = DATALAKE
    ):
        _mongo_uri = f'mongodb://{host}:{port}'
        self._datalake_name = datalake_name
        self._collection_name_prefix = COLLECTION_NAME_PREFIX
        self._client = pymongo.MongoClient(
            _mongo_uri,
            username=username,
            password=password
        )

        # Fetch the DB we need.
        self._db = self._client[self._datalake_name]


    def _build_documents(self, collection: str) -> list:
        """
        Build a list of documents from a collection.

        :param collection: The target collection.
        :return: The documents.
        """
        _LOGGER.debug(f'Fetching documnets from collection {collection}')
        documents = collection.find({})
        parsed_docs = []
        for doc in documents:
            doc_id = doc.pop('_id', None)
            _LOGGER.debug(f'Looking at document with ID: {doc_id}')
            langchain_doc = BabylonDocumentManager(
                collection=collection,
                datalake_document=doc
            ).build_langchain_document()

            parsed_docs.append(langchain_doc)
        return parsed_docs

    def _list_collections(
        self,
        start_prefix: str | None = None,
        end_prefix: str | None = None
    ) -> list[str]:
        """
        Return a list of all collections in the data lake.

        :param start_prefix: ISO start for collection prefix.
        :param end_prefix: ISO end for collection prefix.
        :return: List of collection names.
        """
        all_collection_names: list = self._db.list_collection_names()
        _LOGGER.debug(f'Found {len(all_collection_names)} collections')

        _LOGGER.info(f'Filtering out all collections with the prefix {self._collection_name_prefix}')

        # todo: also filter by start/end prefix
        return list(
            filter(
                lambda name: name.startswith(self._collection_name_prefix),
                all_collection_names
            )
        )

    def __exit__(self, exc_type, exc_val, exc_tb):
        _LOGGER.debug('Closing Mongo Client')
        self._client.close()

