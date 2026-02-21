# pylint: disable=too-few-public-methods
"""Representations for the cleaned documents generated from the pipeline."""

import abc
from datetime import datetime

from features.domain.base.vector import BabylonVectorBasedDocument
from features.domain.data_category import DataCategory


class CleanedDocument(BabylonVectorBasedDocument, abc.ABC):
    """Represents a cleaned vectorized document."""

    # todo: figure out what the cleaned fields should be.
    transaction_date: datetime
    transaction_amount: float
    transaction_description: str
    derived_transaction_category: str
    derived_transaction_type: str


class CleanedTransactionDocument(CleanedDocument):
    """Represents a cleaned transaction document."""

    account: str

    class Config:
        """Cleaned transaction document configuration."""

        name = "cleaned_transactions"
        category = DataCategory.TRANSACTIONS
        use_vector_index = False
