import abc
from datetime import datetime

from features.domain.base.vector import BabylonVectorBasedDocument
from features.domain.data_category import DataCategory


class CleanedDocument(BabylonVectorBasedDocument, abc.ABC):
    # todo: figure out what the cleaned fields should be.
    transaction_date: datetime
    transaction_amount: float
    transaction_description: str
    derived_transaction_category: str
    derived_transaction_type: str

class CleanedTransactionDocument(CleanedDocument):
    account: str

    class Config:
        name = "cleaned_transactions"
        category = DataCategory.TRANSACTIONS
        use_vector_index = False
