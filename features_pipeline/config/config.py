"""Application-level configs."""

from typing import Any

from features_pipeline.config.configuration_loaders import (
    required,
    required_secret,
    optional,
    to_int,
    Loader,
)
from features_pipeline.config.hashicorp import BaoSecretsManager

DEFAULT_CONNECTION_TIMEOUT_SECONDS = "30"

CONFIG_LOADERS: list[Loader] = [
    # These are optional for now. Later decide which should be required.
    required(key="BAO_ADDR"),
    required(key="OPENBAO_SECRETS_PATH"),
    # required(key="SQLALCHEMY_DATABASE_URL"),
    required(key="MONGO_DATA_LAKE_NAME"),
    required(key="EMBEDDINGS_COLLECTION_CHROMA"),
    # The default timeout value to use for various connections (if not overridden).
    optional(key="DEFAULT_TIMEOUT_SECONDS", default_val="30", converter=to_int),
    optional(
        key="MONGO_CONNECTION_TIMEOUT_SECONDS",
        default_val=DEFAULT_CONNECTION_TIMEOUT_SECONDS,
        converter=to_int,
    ),
    optional(key="LOG_TYPE", default_val="stdout"),
    optional(key="LOG_LEVEL", default_val="DEBUG"),
    # Default embedding model for local runs. Should be overridden
    # on a system with greater resources.
    # See https://huggingface.co/BAAI/bge-small-en-v1.5
    optional(key="EMBEDDING_MODEL", default_val="BAAI/bge-small-en-v1.5"),
    optional(key="CHROMA_SQLITE_DIR", default_val="./chromadb"),
]

SECRETS_LOADERS: list[Loader] = [
    required_secret(
        key="MONGO_DB_HOST", path="test", secrets_manager=BaoSecretsManager()
    ),
    required_secret(
        key="MONGO_DB_PORT", path="test", secrets_manager=BaoSecretsManager()
    ),
    required_secret(
        key="MONGO_DB_USER", path="test", secrets_manager=BaoSecretsManager()
    ),
    required_secret(
        key="MONGO_DB_PASSWORD", path="test", secrets_manager=BaoSecretsManager()
    ),
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

    update_config_from_secrets(config)
