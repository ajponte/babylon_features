"""
Datalake records repository pattern
"""
from datetime import datetime

from typing import Any
from pymongo.collection import Collection
from bson import ObjectId

class TransactionDto:
    def __init__(
        self,
        record_id: str,
        amount: float,
        posting_date: datetime,
        details: str,
        tx_type: str,
        description: str,
        check_num: str | None = ""
    ):
        self._record_id = record_id
        self._amount = amount
        self._posting_date = posting_date
        self._details = details
        self._tx_type = tx_type
        self._description = description
        self._check_num = check_num

    @property
    def id(self) -> str:
        return self._record_id

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def posting_date(self) -> datetime:
        return self._posting_date

    @property
    def description(self) -> str:
        return self._description

    @property
    def details(self) -> str:
        return self._details

    @property
    def transaction_type(self) -> str:
        return self._tx_type

    @property
    def check_num(self) -> str:
        return self._check_num

class BaseRepository:
    def __init__(self, collection, mapper):
        self._collection = collection
        self._mapper = mapper

    def get_by_id(self, _id: str) -> object | None:
        doc = self._collection.find_one({"_id": ObjectId(_id)})
        return self._mapper.to_domain(doc) if doc else None

    def get_all(self) -> list[object]:
        return [self._mapper.to_domain(doc) for doc in self._collection.find({})]



class TransactionRepository(BaseRepository):
    def __init__(self, collection: Collection):
        super().__init__(collection=collection, mapper=TransactionMapper)

    def get_by_id(self, transaction_id: str) -> dict | None:
        return self._collection.find_one({"_id": ObjectId(transaction_id)})

    def get_all(self) -> list[dict]:
        return list(self._collection.find({}))

class TransactionMapper:
    @staticmethod
    def to_domain(doc: dict) -> TransactionDto:
        return TransactionDto(
            record_id=str(doc["_id"]),
            amount=doc["Amount"],
            posting_date=_date_from_record(doc['PostingDate']),
            description=doc["Description"],
            details=doc['Details'],
            tx_type=doc['Type'],
            check_num=doc['CheckOrSlipNum']
        )

    @staticmethod
    def to_document(transaction: TransactionDto) -> dict:
        return {
            "_id": ObjectId(transaction.id),
            "Amount": transaction.amount,
            "PostingDate": _from_datetime(transaction.posting_date),
            "Description": transaction.description,
            "Details": transaction.details,
            "Type": transaction.transaction_type,
            "CheckOrSlipNum": transaction.check_num
        }

def _date_from_record(date_str: str) -> datetime:
    """
    Return a python datetime format from the input string.

    :param date_str: The date string iso-formatted.
    :return: Python dt object.
    """
    return datetime.fromisoformat(date_str)

def _from_datetime(date_obj: datetime) -> str:
    """
    Convert a python datetime object to a string in the format
    which the data lake record understands.

    :param date_obj: dt object.
    :return: Date formatted as a string.
    """
    return date_obj.strftime("%d/%m/%Y")

