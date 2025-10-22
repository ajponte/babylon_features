"""Shared utils."""

from datetime import datetime, date

import uuid

from features_pipeline.logger import get_logger


_LOGGER = get_logger()


def create_random_uuid_hex() -> str:
    """Returns a randomly generated UUID in hex format."""
    return uuid.uuid4().hex


def convert_string_to_date(date_string: str, format_string: str) -> date | None:
    """
    Converts a date string into a Python date object given a specific format.

    :param date_string: The string representation of the date (e.g., "2025-10-22").
    :param format_string: The format code matching the date_string (e.g., "%Y-%m-%d").

    :return: A Python date object.
    """
    try:
        # Parse the string into a datetime object
        datetime_obj = datetime.strptime(date_string, format_string)
        # Return just the date part
        return datetime_obj.date()
    except ValueError as e:
        _LOGGER.exception(
            f"Error: Could not parse date string '{date_string}' with format '{format_string}'."
        )
        _LOGGER.debug(f"Details: {e}")
        return None


def convert_date_to_string(date_obj: date, format_string: str) -> str:
    """
    Convert a python date object to a string in the target format.

    :param date_obj: Python date object.
    :param format_string: Target format.
    :return: Formatted date string.
    """
    return date_obj.strftime(format=format_string)
