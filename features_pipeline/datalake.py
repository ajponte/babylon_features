"""Abstractions for interacting with the MongoDB datalake."""

from pymongo import MongoClient

from features_pipeline.error import DatalakeError
from features_pipeline.logger import get_logger

DATALAKE = "babylonDataLake"
COLLECTION_NAME_PREFIX = "chase-data-"

_LOGGER = get_logger(__name__)


class Datalake:
    """Driver for the data lake."""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        *,
        host: str,
        port: int | str,
        username: str,
        password: str,
        datalake_name: str = DATALAKE,
        connection_timeout_seconds: int = 10,
    ):
        """
        Constructor.

        :param host: MongoDB host.
        :param port: MongoDB port.
        :param username: MongoDB username.
        :param password: MongoDB password.
        :param datalake_name: Datalake name.
        :param connection_timeout_seconds: Max timeout seconds.
        """
        self._mongo_uri = f"mongodb://{host}:{port}"
        self._datalake_name = datalake_name
        self._collection_name_prefix = COLLECTION_NAME_PREFIX
        self._client = None
        self._db = None

        try:
            self._client = MongoClient(
                self._mongo_uri,
                username=username,
                password=password,
                connectTimeoutMS=connection_timeout_seconds * 1000,
                serverSelectionTimeoutMS=connection_timeout_seconds * 1000,
            )
            self._client.admin.command("ping")  # type: ignore
            self._db = self._client[self._datalake_name]  # type: ignore
            _LOGGER.debug(
                f"Connected to datalake '{self._datalake_name}' at {self._mongo_uri}"
            )
        except Exception as e:
            raise DatalakeError(
                message="Failed to connect to MongoDB datalake", cause=e
            ) from e

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """Attempt to close the DB client."""
        if self._client is not None:
            try:
                self._client.close()
                _LOGGER.debug("MongoDB client connection closed.")
            finally:
                self._client = None
                self._db = None

    def find(self, criteria: dict, collection: str):
        """Return a cursor to iterate through the collection for the given criteria."""
        if self._db is None:
            raise DatalakeError(message="Database connection not initialized.")
        try:
            cursor = self._db[collection].find(criteria)
            return cursor
        except Exception as e:
            raise DatalakeError(
                message=f"Failed to query collection '{collection}'", cause=e
            ) from e

    def list_collections(
        self,
        start_prefix: str | None = None,
        end_prefix: str | None = None,
    ) -> list[str]:
        """
        Return a list of all collections in the data lake.

        :param start_prefix: ISO start for collection prefix.
        :param end_prefix: ISO end for collection prefix.
        :return: List of collection names.
        """
        if self._db is None:
            raise DatalakeError(message="Database connection not initialized.")

        try:
            all_collection_names: list[str] = self._db.list_collection_names()
        except Exception as e:
            raise DatalakeError(
                message="Failed to list collection names", cause=e
            ) from e

        _LOGGER.debug(f"Found {len(all_collection_names)} total collections.")
        _LOGGER.info(
            f"Filtering collections with prefix '{self._collection_name_prefix}'"
        )

        filtered = [
            name
            for name in all_collection_names
            if name.startswith(self._collection_name_prefix)
        ]

        if start_prefix or end_prefix:
            filtered = [
                name
                for name in filtered
                if (not start_prefix or name >= start_prefix)
                and (not end_prefix or name <= end_prefix)
            ]

        _LOGGER.debug(f"Returning {len(filtered)} filtered collections.")
        return filtered
