import uuid
from datetime import datetime as dt
from zoneinfo import ZoneInfo

def get_now(timezone: str | None = 'UTC'):
    """
    Return the current server timestamp.

    :param timezone: Optional timezone string ID.
    """
    return dt.now(ZoneInfo(timezone))

def generate_random_uuid() -> str:
    """Generate a random UUID in hex format."""
    return uuid.uuid4().hex
