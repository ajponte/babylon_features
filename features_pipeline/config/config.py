"""Application-level configs."""

from typing import Any

from features_pipeline.config.configuration_loaders import (
    Loader,
    required,
    required_secret,
    optional,
    to_int,
)
from features_pipeline.config.hashicorp import SecretsManagerException, BaoSecretsManager

DEFAULT_CONNECTION_TIMEOUT_SECONDS = "30"

CONFIG_LOADERS: list[Loader] = [
    # These are optional for now. Later decide which should be required.
    required(key="BAO_ADDR"),
    required(key="OPENBAO_SECRETS_PATH"),
    # required(key="SQLALCHEMY_DATABASE_URL"),
    required(key="MONGO_DATA_LAKE_NAME"),
    required(key="EMBEDDINGS_COLLECTION_CHROMA"),
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
    # A way to mark only a specific subset of collections to process for the daemon.
    optional(key='DATALAKE_COLLECTION_PREFIX', default_val='chase-data-')
]

SECRETS_LOADERS: list[Loader] = [
    required_secret(key="MONGO_DB_HOST"),
    required_secret(key="MONGO_DB_PORT"),
    required_secret(key="MONGO_DB_USER"),
    required_secret(key="MONGO_DB_PASSWORD"),
]


def update_config(config: dict[str, Any]) -> None:
    import pdb; pdb.set_trace()
    update_config_from_environment(config)
    update_config_from_secrets(config)

def update_config_from_environment(config: dict[str, Any]) -> None:
    """
    Return an updated config dict whose values are from the OS environment.

    :param config: The dict to update.
    """
    import pdb; pdb.set_trace()
    config.update(dict(loader() for loader in CONFIG_LOADERS))

def update_config_from_secrets(config: dict[str, Any]) -> None:
    """
    Update an existing config with values from the secrets store.
    """
    config.update(dict(loader() for loader in SECRETS_LOADERS))
