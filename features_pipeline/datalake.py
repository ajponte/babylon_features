"""Abstractions for interacting with the MongoDB datalake."""
import logging
import pymongo
from pymongo import MongoClient

from features_pipeline.error import DatalakeError

DEFAULT_EMBEDDING_MODEL = 'all-MiniLM-L6-v2'

DATALAKE = 'babylonDataLake'

COLLECTION_NAME_PREFIX = 'chase-data-'


logging.basicConfig(level='DEBUG')
_LOGGER = logging.getLogger(__name__)

class Datalake:
    def __init__(
        self,
        *,
        host: str,
        port: str,
        username: str,
        password: str,
        datalake_name: str = DATALAKE,
        connection_timeout_seconds: int
    ):
        _mongo_uri = f'mongodb://{host}:{port}'
        self._datalake_name = datalake_name
        self._collection_name_prefix = COLLECTION_NAME_PREFIX
        # Setup through ctx manager
        with MongoClient(
            _mongo_uri,
            username=username,
            password=password,
            connectTimeoutMS=(connection_timeout_seconds*10000)
        ) as pymongo_client:
            self._client = pymongo_client

        # Fetch the DB we need.
        self._db = self._client[self._datalake_name]


    def find(self, criteria: dict, collection: str):
        """Return a cursor to iterate through the collection for the criteria."""
        # todo: checks, etc
        cursor = self._db[collection].find(criteria)
        return cursor

    def list_collections(
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
        try:
            all_collection_names: list = self._db.list_collection_names()
        except Exception as e:
            raise DatalakeError(message='Failed to list collection names', cause=e) from e
        _LOGGER.debug(f'Found {len(all_collection_names)} collections')

        _LOGGER.info(f'Filtering out all collections with the prefix {self._collection_name_prefix}')

        # todo: also filter by start/end prefix
        return list(
            filter(
                lambda name: name.startswith(self._collection_name_prefix),
                all_collection_names
            )
        )
