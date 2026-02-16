"""
This module provides a simple class for tracking statistics.
"""


class Stats:
    """A simple class for tracking statistics."""

    def __init__(self):
        self.collections_processed = 0
        self.documents_processed = 0

    def reset(self):
        """Reset the statistics."""
        self.collections_processed = 0
        self.documents_processed = 0

    def __str__(self):
        return f"Collections processed: {self.collections_processed}, Documents processed: {self.documents_processed}"
