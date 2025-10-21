"""Loads config values into a running environment."""

import os
from typing import Any, Union, Callable

from features_pipeline.config.hashicorp import BaoSecretsManager

# Generic function to convert a string key to another type.
type Converter = Callable[[str], Any]

# Generic callable takes as input a function
# of no arguments, and return a tuple.
type Loader = Callable[[], tuple[str, Any]]


# Custom domain-level exceptions.
class ConfigError(Exception):
    """Raise this error when there's an issue with loading a config value."""

    def __init__(self, message: str, cause: Exception | None = None):
        """
        Constructor.

        :param message: Error message.
        :param cause: Optional throwable cause.
        """
        self._message = message
        self._cause = cause

    @property
    def message(self) -> str:
        """
        Return the error message.

        :return: The message.
        """
        return self._message

    @property
    def cause(self) -> Exception | None:
        """
        Return the cause.

        :return: The cause.
        """
        return self._cause


class MissingEnvironmentValueError(ConfigError):
    """Raise this error when there should be a value for a specific key
    in the environment."""

    def __init__(self, key: str):
        """
        Constructor.

        :param key: The key for which no value is present.
        """
        super().__init__(f"Missing Environment variable for key: {key}")


class MissingSecretsKey(ConfigError):
    """Raise this error when there's no secret key found for a path."""

    def __init__(self, path: str, key: str):
        """
        Constructor.

        :param path: The path for which the key is not present.
        :param key: The key for which no value is present.
        """
        super().__init__(f"Missing Secret Key {key} at path {path}")


def get_environment_variable(
    *,
    key: str,
    default: Any | None = None,
    required_key: bool = False,
    converter: Converter | None = None,
) -> Any:
    """
    Return any environment variable which matches the key.

    :param key: The key to search for.
    :param default: Any default value to return. If `required_key` is True, we
                    ignore any default and instead raise an error.
    :param converter: If present, attempt to convert the key to the desired type.
    :param required_key: If True, raise an error if the key is not found in the environment.
    :return: The environment variable which matches the key.
    :raise: MissingEnvironmentValueError - If the key is required, and it does not exist.
    :raise: InvalidEnvironmentVariableError - Upon any error while converting the value.
    """
    if key not in os.environ:
        if required_key:
            raise MissingEnvironmentValueError(key)
        # Return (and convert) the default value
        return converter(default) if converter else default  # type: ignore

    # Fetch and convert the environment value.
    val = os.environ[key]
    return converter(val) if converter else val


def get_secret_value(
    path: str,
    key: str,
    secrets_manager: BaoSecretsManager,
    converter: Converter | None = None,
) -> Any:
    """
    Return the secret value for the key at the path.

    :param path: The path the secret is stored under.
    :param key: The key to fetch.
    :param converter: Optional converter.
    :param secrets_manager: Points to an instantiated secrets manager instance.
    :return: The secret value.
    """
    secrets: dict = secrets_manager.get_secret(path=path, key=key)
    if key not in secrets.values():
        raise MissingSecretsKey(path=path, key=key)
    return converter(secrets["val"]) if converter else secrets["val"]


def load_config(*, key: str, value: str) -> str:
    """
    Loads the key/value pair into the environment.

    :param key: The key to load. Since we're loading OS configs,
                this is a string in all UPPER-CASE.
    :param value: The value to load. Since we're loading OS configs,
                  this is a string.
    :return: The value as it exists in the OS config.
    """
    try:
        os.environ[key.upper()] = value
        return value
    except Exception as e:
        raise ConfigError(f"Error setting config key {key} in the environment") from e


def required(*, key: str, converter: Converter | None = None) -> Loader:
    """
    Fetch a value from the environment and return is (as converted if needed).

    :param key: The key to search for.
    :param converter: The optional converter.
    :return: A loader which will lazily-load the value. We do this by returning
             the loader as a higher-order function, which when invoked will
             return the key, value pair as a Tuple.
    """

    def loader() -> tuple[str, Any]:
        return key, get_environment_variable(
            key=key, converter=converter, required_key=True
        )

    return loader


def required_secret(
    *,
    key: str,
    path: str | None = None,
    converter: Converter | None = None,
) -> Loader:
    """
    Fetch a required secret from the secrets manager (as converted if needed).

    :param key: The key to search for.
    :param path: The path the secret is stored under. If not path is supplied a default
                 is assumed, whose value exists in the environment.
    :param converter: The optional converter.
    :return: A loader which will lazily-load the value. We do this by returning
             the loader as a higher-order function, which when invoked will
             return the key, value pair as a Tuple.
    """
    path = path or os.environ["OPENBAO_SECRETS_PATH"]

    secrets_manager = BaoSecretsManager()
    def loader() -> tuple[str, Any]:
        return key, get_secret_value(
            key=key, path=path, converter=converter, secrets_manager=secrets_manager
        )

    return loader


def optional(
    *, key: str, default_val: str | None, converter: Converter | None = None
) -> Loader:
    """
    Assuming the key/value pair is optional, loads the pair from the environment.

    :param key: The key to load.
    :param default_val: The value to assign by default (since it's not required).
    :param converter: An optional converter for the value in the environment.
    :return: A higher order function, which when invoked will return the key,value pair as a tuple.
    """

    def loader() -> tuple[str, Any]:
        return key, get_environment_variable(
            key=key, converter=converter, default=default_val
        )

    return loader


# Our first converter.
def to_bool(val: Union[str, bool]) -> bool:
    """
    Converts a value to a boolean.

    :param val: The value to convert (case-insensitive).
    """
    # Simple case
    if isinstance(val, bool):
        return val
    if val.casefold() == "false".casefold():
        return False
    if val.casefold() == "true".casefold():
        return True
    raise ValueError(f"{val!r} could not be converted to a boolean type.")


def to_int(val: Union[str, int, float]) -> int:
    """Convert the value to an integer."""
    try:
        # The value is assumed to be in integer.
        return int(val)
    except Exception as e:
        raise ValueError(f"{val!r} could not be converted to a integer type.") from e
