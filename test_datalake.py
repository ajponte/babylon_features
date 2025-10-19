"""Test datalake client."""
from features_pipeline.datalake import Datalake

MONGO_DB_DATALAKE_NAME = "babylonDataLake"

DEFAULT_MONGO_DB_HOST = "localhost"
DEFAULT_MONGO_DB_PORT = 27017
DEFAULT_MONGO_DB_USER = "admin"
DEFAULT_MONGO_DB_PASS = "password"
DEFAULT_DATA_LAKE_MAX_RECORDS = 500
DEFAULT_MONGO_CONNECTION_TIMEOUT_SECONDS = 30

def main():
    config = {
        'MONGO_DATA_LAKE_NAME': MONGO_DB_DATALAKE_NAME,
        'MONGO_DB_HOST': DEFAULT_MONGO_DB_HOST,
        'MONGO_DB_PORT': DEFAULT_MONGO_DB_PORT,
        'MONGO_DB_USER': DEFAULT_MONGO_DB_USER,
        'MONGO_DB_PASSWORD': DEFAULT_MONGO_DB_PASS,
        'DATA_LAKE_MAX_RECORDS': DEFAULT_DATA_LAKE_MAX_RECORDS,
        'MONGO_CONNECTION_TIMEOUT_SECONDS': DEFAULT_MONGO_CONNECTION_TIMEOUT_SECONDS
    }
    datalake = Datalake(
        datalake_db_name=config['MONGO_DATA_LAKE_NAME'],
        host=config["MONGO_DB_HOST"],
        port=config["MONGO_DB_PORT"],
        username=config["MONGO_DB_USER"],
        password=config["MONGO_DB_PASSWORD"],
        connection_timeout_seconds=config["MONGO_CONNECTION_TIMEOUT_SECONDS"],
    )

    collections = datalake.all_collections()
    print(f'Found {len(collections)} in the datalake')

    print(f'collections: {collections}')

if __name__ == '__main__':
    main()
