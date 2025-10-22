from typing import Any

from pymongo import MongoClient

class MongoClientFactory:
    _client = None

    @classmethod
    def get_client(
        cls,
        **kwargs
    ) -> MongoClient:
        """
        Return the `MongoClient` this factory points to.

        :param kwargs: Configuration mapping.
        :return: The `MongoClient` this factory points to.
        """
        if cls._client is None:
            dl_config: dict[str, Any] | None = kwargs.get('config', None)
            if not dl_config:
                raise ValueError('Config mapping not provided')
            cls._client = _configure_mongo_client(dl_config)
        return cls._client

    @classmethod
    def get_collection(cls, db_name: str, coll_name: str):
        """
        Return an iterator to all items in the collection.

        :param db_name: DL DB name.
        :param coll_name: DL collection.
        :return: Collection iterator.
        """
        client = cls.get_client()
        return client[db_name][coll_name]

    @classmethod
    def list_collections(cls, db_name: str, prefix: str | None = None) -> Any:
        client = cls.get_client()
        collections = client[db_name].list_collections()
        if not prefix:
            return [col['name'] for col in collections]

        filtered = [
            col['name']
            for col in collections
            if col['name'].startswith(prefix)
        ]
        return filtered


def _configure_mongo_client(config: dict):
    """Return a configured `MongoClient`."""
    host: str = config['MONGO_DB_HOST']
    port: int = config['MONGO_DB_PORT']
    user: str = config['MONGO_DB_USER']
    passwd: str = config['MONGO_DB_PASSWORD']
    connection_timeout_seconds: int = config['MONGO_CONNECTION_TIMEOUT_SECONDS']
    uri = f'{host}:{port}'
    return MongoClient(
        uri,
        username=user,
        password=passwd,
        connectTimeoutMS=connection_timeout_seconds * 1000,
        serverSelectionTimeoutMS=connection_timeout_seconds * 1000,
    )
