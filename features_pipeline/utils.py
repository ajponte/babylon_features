import uuid


def create_random_uuid_hex() -> str:
    """Returns a randomly generated UUID in hex format."""
    return uuid.uuid4().hex
