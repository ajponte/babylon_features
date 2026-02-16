"""
Daemon script. This script, upon a defined interval, will:
1) Scan the data lake for desired collections of records.
2) For each record, embed the data, and store in the data lake.
"""
from typing import Any

import time

from datalake.mongo_factory import MongoClientFactory
from datalake.repository import TransactionRepository
from datalake.uow import UnitOfWork
from features_pipeline.logger import get_logger
from features_pipeline.process.processor import Mongo as MongoProcessor
from features_pipeline.stats import Stats
from features_pipeline.vectorstore import ChromaVectorStore


_LOGGER = get_logger()

# Config vars for testing
DEFAULT_BAO_ADDR = "http://127.0.0.1:8200"
DEFAULT_BAO_VAULT_TOKEN = "dev-only-token"
DEFAULT_OPENBAO_SECRETS_PATH = "test"
DEFAULT_MONGO_DATA_LAKE_NAME = "datalake"
DEFAULT_EMBEDDINGS_COLLECTION_CHROMA = "babylon_vectors"
# 5 minutes
DEFAULT_MIN_LOOP_SECONDS = 300
DEFAULT_DATALAKE_COLLECTION_PREFIX = "transactions"
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_CHROMA_SQLITE_DIR = ""

DEFAULT_DATALAKE_HOST = 'localhost'
DEFAULT_DATALAKE_PORT = 27017
DEFAULT_DALAKE_USER = 'babylon'
DEFAULT_DATALAKE_PASS = 'babylonpass'
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_CHROMA_HOST = 'localhost'
DEFAULT_CHROMA_PORT = 8003

class Daemon:
    """
    A simple daemon class that runs a processor in a loop.

    It ensures that each loop iteration (including processing time)
    takes at least 'min_loop_seconds'.
    """

    def __init__(self, daemon_config: dict[str, Any]):
        self._processor = MongoProcessor(
            ChromaVectorStore(
                model=str(daemon_config['EMBEDDING_MODEL']),
                collection=str(daemon_config['EMBEDDINGS_COLLECTION_CHROMA']),
                sqlite_dir=str(daemon_config['CHROMA_SQLITE_DIR']) if daemon_config['CHROMA_SQLITE_DIR'] else None,
                host=str(daemon_config['CHROMA_HOST']) if daemon_config['CHROMA_HOST'] else None,
                port=int(daemon_config['CHROMA_PORT']) if daemon_config['CHROMA_PORT'] else None,
            )
        )
        self._mongo_client = MongoClientFactory.get_client(config=daemon_config)
        self._mongo_db_name = daemon_config['MONGO_DATA_LAKE_NAME']
        self._collection_prefix = daemon_config['DATALAKE_COLLECTION_PREFIX']
        self._min_loop_seconds: int = daemon_config['MIN_LOOP_SECONDS']
        self._running = True  # Flag to control the loop
        self._stats = Stats()

    def run(self):
        """
        Starts the daemon's main processing loop.
        """
        _LOGGER.info(f"Daemon starting. Minimum loop time: {self._min_loop_seconds}s")
        while self._running:
            # Record the start time of the loop
            start_time = time.time()

            try:
                self.__process()
            except Exception as e:
                # Catch exceptions from the processor so the daemon doesn't crash
                _LOGGER.error(f"Error in processor: {e}", exc_info=True)
                _LOGGER.info(f'Skipping processing for batch {self._processor.batch_number}')

            # Calculate how long the processing took
            end_time = time.time()
            duration = end_time - start_time

            # Calculate how long we need to sleep to meet the minimum loop time
            sleep_time = self._min_loop_seconds - duration

            if sleep_time > 0:
                # If the processor finished faster than the min loop time, sleep
                _LOGGER.debug(f"Process took {duration:.2f}s. Sleeping for {sleep_time:.2f}s.")
                time.sleep(sleep_time)
            else:
                # The processor took longer than the minimum loop time.
                # Don't sleep, just log it and continue to the next loop.
                _LOGGER.warning(f"Loop overrun: Process took {duration:.2f}s, which is > {self._min_loop_seconds}s.")

        _LOGGER.info("Daemon shutting down.")

    def stop(self):
        """
        Signals the daemon to stop its loop.
        """
        _LOGGER.info("Stop signal received.")
        self._running = False

    def __process(self) -> None:
        """Open a DB connection and process."""
        self._stats.reset()
        with UnitOfWork(self._mongo_client):
            # Get all collections by optional prefix.
            _LOGGER.info(f'Listing mongo collections for DB {self._mongo_db_name}.')
            collections = MongoClientFactory.list_collections(
                db_name=self._mongo_db_name,
                prefix=self._collection_prefix
            )
            _LOGGER.debug(f'Found {len(collections)} collections')
            for collection in collections:
                _LOGGER.debug(f"Processing collection {collection}")
                self.__process_datalake_collection(collection)
            _LOGGER.info(f"Finished processing batch. Stats: {self._stats}")

    def __process_datalake_collection(self, collection: str) -> None:
        """Process datalake collection by identifier (this is assumed to be the name."""
        _LOGGER.debug(f"Invoking processor for {collection}")
        transactions_collection = MongoClientFactory.get_collection(
            db_name=self._mongo_db_name,
            coll_name=collection
        )
        documents_processed = self._processor.process(
            # Create a new TransactionRepository record for each collection we found.
            mongo_repository=TransactionRepository(transactions_collection)
        )
        self._stats.documents_processed += documents_processed
        self._stats.collections_processed += 1
        _LOGGER.debug(f'Finished invoking processor for {collection}')

if __name__ == "__main__":
    # todo: load from environment.
    # Holding off until https://github.com/ajponte/babylon/issues/36
    config = {
        "BAO_ADDR": DEFAULT_BAO_ADDR,
        "BAO_VAULT_TOKEN": DEFAULT_BAO_VAULT_TOKEN,
        "OPENBAO_SECRETS_PATH": DEFAULT_OPENBAO_SECRETS_PATH,
        "MONGO_DATA_LAKE_NAME": DEFAULT_MONGO_DATA_LAKE_NAME,
        "EMBEDDINGS_COLLECTION_CHROMA": DEFAULT_EMBEDDINGS_COLLECTION_CHROMA,
        "MIN_LOOP_SECONDS": DEFAULT_MIN_LOOP_SECONDS,
        "MONGO_DB_HOST": DEFAULT_DATALAKE_HOST,
        "MONGO_DB_PORT": DEFAULT_DATALAKE_PORT,
        "MONGO_DB_USER": DEFAULT_DALAKE_USER,
        "MONGO_DB_PASSWORD": DEFAULT_DATALAKE_PASS,
        "MONGO_CONNECTION_TIMEOUT_SECONDS": DEFAULT_TIMEOUT_SECONDS,
        'DATALAKE_COLLECTION_PREFIX': DEFAULT_DATALAKE_COLLECTION_PREFIX,
        'EMBEDDING_MODEL': DEFAULT_EMBEDDING_MODEL,
        'CHROMA_SQLITE_DIR': DEFAULT_CHROMA_SQLITE_DIR,
        'CHROMA_HOST': DEFAULT_CHROMA_HOST,
        'CHROMA_PORT': DEFAULT_CHROMA_PORT
    }

    _daemon = Daemon(config)

    # 3. Run the daemon
    # This will block the main thread until you press Ctrl+C
    try:
        _daemon.run()
    except KeyboardInterrupt:
        _LOGGER.info("Caught KeyboardInterrupt, stopping daemon...")
        _daemon.stop()
        # The loop will finish its current iteration and then exit
