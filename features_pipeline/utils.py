"""Shared utils."""
from datetime import datetime, date

import uuid


def create_random_uuid_hex() -> str:
    """Returns a randomly generated UUID in hex format."""
    return uuid.uuid4().hex

def convert_string_to_date(date_string: str, format_string: str) -> date:
    """
    Converts a date string into a Python date object given a specific format.

    :param date_string: The string representation of the date (e.g., "2025-10-22").
    :param format_string: The format code matching the date_string (e.g., "%Y-%m-%d").

    Returns:
        A Python date object.
    """
    try:
        # Parse the string into a datetime object
        datetime_obj = datetime.strptime(date_string, format_string)
        # Return just the date part
        return datetime_obj.date()
    except ValueError as e:
        print(f"Error: Could not parse date string '{date_string}' with format '{format_string}'.")
        print(f"Details: {e}")
        return None


def convert_date_to_string(date_obj: date, format_string: str) -> str:
    return date_obj.strftime(format=format_string)
