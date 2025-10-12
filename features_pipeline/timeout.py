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


def timeout_decorator(attribute_name='_timeout_seconds', default_seconds=10):
    """
    A decorator for class methods that raises a TimeoutException if execution
    exceeds the duration specified by an instance member variable.

    Args:
        attribute_name (str): The name of the instance attribute (e.g., '_timeout_seconds')
                              that holds the timeout duration (in seconds).
        default_seconds (int): Fallback timeout if the attribute is not found.
    """

    def decorator(func):

        # 1. Platform Check: Signal-based timeout is Unix-only.
        if platform.system() == "Windows":
            # Raise an error early if the platform is not supported.
            raise NotImplementedError(
                "Signal-based timeout decorator is not supported on Windows."
            )

        # 2. Signal Handler: Executed when SIGALRM is received.
        def signal_handler(signum, frame):
            # The handler simply raises the custom exception
            raise TimeoutException(
                f"Method execution timed out after reading duration from '{attribute_name}'."
            )

        @functools.wraps(func)
        def wrapper(*args, **kwargs):

            # --- ACCESSING THE INSTANCE AND ATTRIBUTE ---
            if not args:
                # Should not happen for a properly called instance method
                _LOGGER.error("Decorator expected 'self' as the first argument but received none.")
                return func(*args, **kwargs)

            # The first argument is the instance ('self')
            instance = args[0]
            timeout_duration = default_seconds

            # Attempt to read the timeout value from the instance attribute
            try:
                # Use getattr to safely access the attribute by its name string
                timeout_duration = getattr(instance, attribute_name)
                if not isinstance(timeout_duration, (int, float)) or timeout_duration <= 0:
                    raise ValueError("Timeout duration must be a positive number.")
            except AttributeError:
                # If the attribute is not found, use the decorator's default
                _LOGGER.warning(
                    f"Attribute '{attribute_name}' not found on instance. Using default: {default_seconds}s."
                )
            except ValueError as e:
                _LOGGER.error(f"Invalid timeout value in '{attribute_name}': {e}. Using default: {default_seconds}s.")

            # --- EXECUTION WITH TIMEOUT ---

            _LOGGER.info(
                f"[{func.__name__}] Setting method timeout to {timeout_duration} seconds."
            )

            # Set the alarm handler and the alarm duration
            signal.signal(signal.SIGALRM, signal_handler)
            signal.alarm(int(timeout_duration))  # alarm expects an integer

            try:
                # Execute the decorated function, passing 'self' and all other arguments
                result = func(*args, **kwargs)
            finally:
                # IMPORTANT: Cancel the alarm to prevent it from affecting other code
                signal.alarm(0)

            return result

        return wrapper

    return decorator


# --- Example Class Implementation ---

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

    @timeout_decorator('_timeout_seconds')  # Pass the attribute name
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
