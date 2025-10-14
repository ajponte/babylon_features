# Note: This script is very much for dev/test purposes only.
"""Utils for interacting with Hashicorp/Openbao."""
from abc import ABC, abstractmethod
from typing import Any
import os
import logging
import hvac

_LOGGER = logging.getLogger()


class SecretsManagerException(Exception):
    """Throw this error for issues with a secrets manager."""

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
        Return the message.

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


class OpenBaoApiClient:
    """API client wrapper for OpenBao."""

    def __init__(self):
        """Constructor."""
        # todo: Add RSA cert
        self._client = hvac.Client(
            # `BAO_ADDR`, `VAULT_TOKEN` are the suggested env var names from Hashicorp.
            url=os.environ.get("BAO_ADDR", None),
            token=os.environ.get("VAULT_TOKEN", None),
        )
        self.__is_authenticated(self._client)
        _LOGGER.info("Hashicorp Secrets client authenticated.")

    # Testing for now. Needs to be removed for a production system.
    def add_secret_value(self, *, path: str, secret: dict) -> dict:
        """
        Writes the secret under `secrets/path`

        :param path: Secrets path.
        :param secret: Secret key/value pair as a dict.
        :return: The response from setting the secret in the vault.
        :raise: SecretsManagerException - Upon error.
        """
        try:
            create_response = self._client.secrets.kv.v2.create_or_update_secret(
                path=path, secret=secret
            )
            _LOGGER.info(f"Set secret value at path {path}")
            return create_response
        except Exception as e:
            message = f"Exception while setting secret value at path {path}"
            _LOGGER.exception(message)
            raise SecretsManagerException(message, cause=e) from e

    def read_secret_values(self, *, path: str) -> dict:
        """
        Reads secrets from the path.

        :param path: The secrets path to read from.
        :return: The read response data.
        :raise: SecretsManagerException - Upon error.
        """
        try:
            # todo: add version checking.
            read_response = self._client.secrets.kv.read_secret_version(
                path=path,
                # See https://github.com/hvac/hvac/pull/907
                raise_on_deleted_version=False,
            )["data"]
            ver = read_response["metadata"]["version"]
            _LOGGER.debug(f"Found secrets version: {ver}")
            _LOGGER.debug(f"Successfully read secrets from path {path}")
            return read_response["data"]
        except Exception as e:
            message = f"Exception while reading secret values at path {path}"
            _LOGGER.exception(message)
            raise SecretsManagerException(message, cause=e) from e

    @classmethod
    def __is_authenticated(cls, client: hvac.Client):
        """Return True only if the Client has been authenticated."""
        assert client.is_authenticated(), "Hashicorp is not authenticated!"


class AbstractSecretsManager(ABC):
    """Abstract implementation for a secrets manager.
    Based on skeletons from
    https://refactoring.guru/design-patterns/singleton/python/example#example-0
    """

    @abstractmethod
    def add_secret(self, path: str, secret: dict) -> bool:
        """
        Add PATH/KEY to the internal secrets store.

        :param path: The path in the secrets store.
        :param self: The secret kv, encoded in a `Secret` data type.
        """

    @abstractmethod
    def get_secret(self, path: str, key: str) -> dict:
        """Fetch the secret value for PATH/KEY from the internal secrets store."""


class BaoSecretsManager(AbstractSecretsManager):
    """OpenBao implementation of `AbstractSecretsManager`."""

    _instance: OpenBaoApiClient | None = None
    _secrets: dict[str, Any] | None = None

    # pylint: disable=unused-argument
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            # Cache this instance.
            cls._instance = super(BaoSecretsManager, cls).__new__(cls)  # type: ignore
            # Cache an openbao API client.
            cls._instance.client = OpenBaoApiClient()
        else:
            _LOGGER.info("Instance already exists. Returning cached.")
        return cls._instance

    def add_secret(self, path: str, secret: dict) -> bool:
        response: dict = self._instance.client.add_secret_value(  # type: ignore
            path=path, secret=secret
        )
        # todo: Add more validations.
        if not response:
            _LOGGER.info("No response from client")
            return False
        if not self._secrets:
            self._secrets = secret
            return True
        self._secrets.update(secret)
        return True

    def get_secret(self, path: str, key: str) -> dict:
        if self._secrets is None:
            _LOGGER.info(f"Secrets under {path} not cached.")
            resp = self._instance.client.read_secret_values(path=path)  # type: ignore
            if not resp:
                raise SecretsManagerException(f"No secrets returned under path {path}")
            self._secrets = resp
        if key not in self._secrets:
            raise SecretsManagerException(f"Secret {path}/{key} not found.")
        # Create a new Secret data type
        return {"key": key, "val": self._secrets[key]}


# def test_bao_api_client():
#     client = OpenBaoApiClient()
#
#     client.add_secret_value(path='test', secret={'foo': 'bar'})
#
#     resp = client.read_secret_values(path='test')
#     print(f'resp: {resp}')
#
# def test_secrets_manager():
#     path = 'test'
#     secrets_manager = BaoSecretsManager()
#     secrets_manager.add_secret(
#         path=path,
#         secret={'foo': 'bar'}
#     )
#
#     secrets_manager.add_secret(
#         path=path,
#         secret={'bazz': 'lazz'}
#     )
#
#     # secrets_manager.add_secret(
#     #     path=path,
#     #     secret={'foo': 'bar'}
#     # )
#     resp = secrets_manager.get_secret(path=path, key='foo')
#
#     assert resp == {'key': 'foo', 'val': 'bar'}
#
#     resp = secrets_manager.get_secret(path=path, key='bazz')
#
#     assert resp == {'key': 'bazz', 'val': 'lazz'}
#
# test_secrets_manager()
# test_bao_api_client()
