from pytest import fixture
import os
from unittest.mock import patch

from features_pipeline.config.hashicorp import OpenBaoApiClient

# The following environment variables are set here so they are
# available for all fixtures, including session-scoped ones.
MOCK_ENV_VARS = {
    'BAO_ADDR': 'http://localhost:8200',
    'BAO_TOKEN': 'dev-token',
    'OPENBAO_SECRETS_PATH': 'test',
    'MONGO_DB_HOST': 'localhost',
    'MONGO_DB_PORT': '12345',
    'MONGO_DB_USER': 'dummy-user',
    'MONGO_DB_PASSWORD': 'dummy-pass'
}

# Use os.environ.update() to set the environment variables globally for the test session.
os.environ.update(MOCK_ENV_VARS)

MOCK_SECRETS = {
    'DB_HOST': 'https://mock-host.com',
    'DB_PORT': '5432',
    'DB_USERNAME': 'dummy',
    'DB_PASSWORD': 'dummy'
}

MOCK_HVAC_RESPONSE = {
    'data': {
        'data': MOCK_SECRETS,
        'metadata': {
            'version': 1
        }
    }
}

@fixture(scope='session', autouse=True)
def hvac_client():
    """
    Changed the scope to 'session' to match mock_bao_client.
    The patch is automatically started and stopped by pytest.
    """
    with patch('features_pipeline.config.hashicorp.hvac.Client') as mock_client:
        yield mock_client

@fixture(scope='session')
def mock_bao_client(hvac_client):
    """
    Changed the scope to 'session' to match flask_app.
    A fixture to mock the OpenBao client for tests that require a secrets manager.
    """
    hvac_client.return_value.is_authenticated.return_value = True
    hvac_client.return_value.secrets.kv.read_secret_version.return_value = MOCK_HVAC_RESPONSE
    open_bao_api_client = OpenBaoApiClient()
    return open_bao_api_client
