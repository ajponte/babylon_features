
import features_pipeline.config.hashicorp as MUT
from pytest import fixture
from unittest.mock import ANY

# Mock secrets to be used in tests
MOCK_SECRETS = {
    'k1': 's1',
    'k2': 's2'
}


def test_open_bao_api_client_read_secrets(hvac_client):
    """
    Tests reading secrets from the OpenBaoApiClient by mocking the underlying
    hvac.Client and its methods.
    """
    # Configure the mock instance's methods to return the expected values
    hvac_client.return_value.is_authenticated.return_value = True
    hvac_client.return_value.secrets.kv.read_secret_version.return_value = {
        'data': {
            'data': MOCK_SECRETS,
            'metadata': {'version': 1}
        }
    }

    # Instantiate the client, which will use our mocked hvac client
    api_client = MUT.OpenBaoApiClient()

    # Call the method under test
    secrets = api_client.read_secret_values(path=ANY)

    # Assert the method was called correctly on the mock client
    hvac_client.return_value.secrets.kv.read_secret_version.assert_called_with(
        path=ANY,
        raise_on_deleted_version=False
    )

    # Assert the returned data matches the mock secrets
    assert secrets == MOCK_SECRETS


def test_open_bao_api_client_add_secret(hvac_client):
    """
    Tests adding a secret using the OpenBaoApiClient.
    """
    mock_add_response = {'data': {'foo': 'bar'}}

    # Configure the mock for the add method
    hvac_client.return_value.is_authenticated.return_value = True
    hvac_client.return_value.secrets.kv.v2.create_or_update_secret.return_value = mock_add_response

    # Instantiate the client
    api_client = MUT.OpenBaoApiClient()

    secret_to_add = {'foo': 'bar'}
    path = 'test_add_path'

    # Call the method under test
    response = api_client.add_secret_value(path=path, secret=secret_to_add)

    # Assert the method was called correctly
    hvac_client.return_value.secrets.kv.v2.create_or_update_secret.assert_called_with(
        path=path,
        secret=secret_to_add
    )

    # Assert the response matches the mocked response
    assert response == mock_add_response
