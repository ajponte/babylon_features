import signal
import functools
import platform
import time
import logging

# Set up basic logging for demonstration purposes
_LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


# Define a custom exception for clarity
class TimeoutException(Exception):
    """Custom exception raised when a timeout occurs."""
    pass


class DocumentBuilder:
    """
    Simulates a process that builds documents, with a configurable timeout.
    """
    # 1. The member variable used by the decorator
    _timeout_seconds = 3

    def __init__(self, collection_name, timeout_duration=None):
        self._collection = collection_name
        # Override the class default if a duration is passed to the constructor
        if timeout_duration is not None:
            self._timeout_seconds = timeout_duration

        _LOGGER.info(
            f"Builder initialized for '{self._collection}' with timeout: {self._timeout_seconds}s"
        )

    def build_documents(self, work_time_s: float) -> list:
        """
        Build a list of RAG documents from a mock collection.
        :param work_time_s: How long the simulated fetch should take.
        :return: The documents.
        """

        _LOGGER.debug(f'Fetching documents from collection {self._collection}. Expected duration: {work_time_s:.2f}s')

        # Simulate the time-consuming process (e.g., Mongo query)
        time.sleep(work_time_s)

        _LOGGER.info("Document fetching completed successfully.")
        return [f"Doc {i}" for i in range(100)]


# --- Demonstration ---

# Scenario A: Success - Task completes before the timeout (3 seconds)
print("=" * 40)
_LOGGER.info("Scenario A: Success (3s timeout vs 2s task)")
builder_a = DocumentBuilder(collection_name="users_v1", timeout_duration=3)
try:
    documents = builder_a.build_documents(work_time_s=2)
    _LOGGER.info(f"Successfully retrieved {len(documents)} documents.")
except TimeoutException as e:
    _LOGGER.error(f"Execution Error: {e}")

# Scenario B: Failure - Task exceeds the timeout (1 second)
print("\n" + "=" * 40)
_LOGGER.info("Scenario B: Failure (1s timeout vs 2s task)")
builder_b = DocumentBuilder(collection_name="logs_v2", timeout_duration=1)
try:
    documents = builder_b.build_documents(work_time_s=2)  # This will take 2 seconds
    _LOGGER.info(f"Successfully retrieved {len(documents)} documents.")
except TimeoutException as e:
    _LOGGER.error(f"Execution Error: {e}")

print("\n" + "=" * 40)
