import os
import sys
from datalake.mongo_factory import MongoClientFactory
from pymongo.errors import ConnectionFailure, OperationFailure

# Configuration for testing a remote MongoDB instance
# Defaults derived from docker-compose.yml and daemon.py
MONGO_DB_HOST = os.getenv("MONGO_DB_HOST", "localhost")
MONGO_DB_PORT = int(os.getenv("MONGO_DB_PORT", 27017))
MONGO_DB_USER = os.getenv("MONGO_DB_USER", "babylon")
MONGO_DB_PASSWORD = os.getenv("MONGO_DB_PASSWORD", "babylonpass")
MONGO_DATA_LAKE_NAME = os.getenv("MONGO_DATA_LAKE_NAME", "datalake")
MONGO_CONNECTION_TIMEOUT_SECONDS = int(os.getenv("MONGO_CONNECTION_TIMEOUT_SECONDS", 30))


def check_mongo_connection():
    """
    Attempts to connect to a remote MongoDB server.
    Exits with code 0 on success, 1 on failure.
    """
    print(f"Attempting to connect to MongoDB at {MONGO_DB_HOST}:{MONGO_DB_PORT}")
    print(f"Using user: {MONGO_DB_USER}, database: {MONGO_DATA_LAKE_NAME}")
    
    config = {
        "MONGO_DB_HOST": MONGO_DB_HOST,
        "MONGO_DB_PORT": MONGO_DB_PORT,
        "MONGO_DB_USER": MONGO_DB_USER,
        "MONGO_DB_PASSWORD": MONGO_DB_PASSWORD,
        "MONGO_CONNECTION_TIMEOUT_SECONDS": MONGO_CONNECTION_TIMEOUT_SECONDS,
    }

    try:
        client = MongoClientFactory.get_client(config=config)
        
        # The ismaster command is cheap and does not require auth.
        # It's a good way to check if the server is alive.
        client.admin.command('ismaster') 

        # Attempt to list collection names to ensure authentication works if required
        # and that the database is accessible.
        # This will fail if authentication is required but credentials are bad,
        # or if the database name is wrong for the given user.
        db = client[MONGO_DATA_LAKE_NAME]
        _ = db.list_collection_names()
        
        print(f"Successfully connected to MongoDB at {MONGO_DB_HOST}:{MONGO_DB_PORT}")
        sys.exit(0)

    except ConnectionFailure as e:
        print(f"ERROR: Failed to connect to MongoDB server: {e}.")
        print(f"Please ensure the MongoDB Docker service is running and accessible at {MONGO_DB_HOST}:{MONGO_DB_PORT}.")
        sys.exit(1)
    except OperationFailure as e:
        print(f"ERROR: MongoDB Operation Failure: {e}.")
        print(f"This might indicate incorrect username/password or insufficient permissions for database '{MONGO_DATA_LAKE_NAME}'.")
        sys.exit(1)
    except Exception as e:
        print(f"AN UNEXPECTED ERROR OCCURRED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Reset the MongoClientFactory's internal client for this standalone script
    # to ensure it uses the config provided by this script and not a potentially
    # cached client from another run.
    MongoClientFactory._client = None 
    check_mongo_connection()

