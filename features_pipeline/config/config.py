
"""Application-level configs."""

from typing import Any

from features_pipeline.config.confload import (
    Loader,
    required,
    required_secret,
    optional,
    to_int,
    to_bool,
)


DEFAULT_CONNECTION_TIMEOUT_SECONDS = "30"

CONFIG_LOADERS: list[Loader] = [
    # These are optional for now. Later decide which should be required.
    required(key="BAO_ADDR"),
    required(key="OPENBAO_SECRETS_PATH"),
    # required(key="SQLALCHEMY_DATABASE_URL"),
    required(key="MONGO_DATA_LAKE_NAME"),
    optional(
        key='MONGO_CONNECTION_TIMEOUT_SECONDS',
        default_val=DEFAULT_CONNECTION_TIMEOUT_SECONDS,
        converter=to_int
    ),
    optional(key="LOG_TYPE", default_val="stdout"),
    optional(key="LOG_LEVEL", default_val="DEBUG"),
]

SECRETS_LOADERS: list[Loader] = [
    required_secret(key="MONGO_DB_HOST", path="test"),
    required_secret(key="MONGO_DB_PORT", path="test"),
    required_secret(key="MONGO_DB_USERNAME", path="test"),
    required_secret(key="MONGO_DB_PASSWORD", path="test"),
]


def update_config_from_environment(config: dict[str, Any]) -> None:
    """
    Return an updated config dict whose values are from the OS environment.

    :param config: The dict to update.
    """
    config.update(dict(loader() for loader in CONFIG_LOADERS))


def update_config_from_secrets(config: dict[str, Any]) -> None:
    """
    Update an existing config with values from the secrets store.

    :param config: The config dict to update.
    """
    config.update(dict(loader() for loader in SECRETS_LOADERS))
