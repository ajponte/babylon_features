from pymongo import MongoClient

class MongoClientFactory:
    _client = None

    @classmethod
    def get_client(cls, uri: str = "mongodb://localhost:27017"):
        if cls._client is None:
            cls._client = MongoClient(uri)
        return cls._client

    @classmethod
    def get_collection(cls, db_name: str, coll_name: str):
        client = cls.get_client()
        return client[db_name][coll_name]
