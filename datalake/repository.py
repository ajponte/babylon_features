"""
Datalake records repository pattern
"""
from datetime import date

from pymongo.collection import Collection
from bson import ObjectId

from features_pipeline.utils import convert_string_to_date, convert_date_to_string

DEFAULT_DATE_STRING_FORMAT = "%d/%m/%Y"

class TransactionDto:
    def __init__(
        self,
        record_id: str,
        amount: float,
        posting_date: date,
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
    def posting_date(self) -> date:
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
    def __init__(self, collection: Collection, mapper):
        self._collection = collection
        self._mapper = mapper

    def get_by_id(self, _id: str) -> object | None:
        doc = self._collection.find_one({"_id": ObjectId(_id)})
        return self._mapper.to_domain(doc) if doc else None

    def get_all(self) -> list[object]:
        return [self._mapper.to_domain(doc) for doc in self._collection.find({})]

    def get_by_filter(self, filter_criteria: dict) -> list[object]:
        return [self._mapper.to_domain(doc) for doc in self._collection.find(filter_criteria)]


class TransactionRepository(BaseRepository):
    def __init__(self, collection: Collection):
        super().__init__(collection=collection, mapper=TransactionMapper)

    @property
    def collection(self):
        return self._collection

    def get_by_id(self, transaction_id: str) -> dict | None:
        return self._collection.find_one({"_id": ObjectId(transaction_id)})

    def get_by_filter(self, filter_criteria: dict) -> list[TransactionDto]:
        return [self._mapper.to_domain(doc) for doc in self._collection.find(filter_criteria)]

class TransactionMapper:
    @staticmethod
    def to_domain(
        doc: dict,
        date_string_format: str | None = DEFAULT_DATE_STRING_FORMAT
    ) -> TransactionDto:
        return TransactionDto(
            record_id=str(doc["_id"]),
            amount=doc["Amount"],
            posting_date=convert_string_to_date(
                date_string=doc['PostingDate'],
                format_string=date_string_format
            ),
            description=doc["Description"],
            details=doc['Details'],
            tx_type=doc['Type'],
            check_num=doc['CheckOrSlipNum']
        )

    @staticmethod
    def to_document(
            transaction: TransactionDto,
            date_string_format: str | None = DEFAULT_DATE_STRING_FORMAT
    ) -> dict:
        return {
            "_id": ObjectId(transaction.id),
            "Amount": transaction.amount,
            "PostingDate": convert_date_to_string(
                date_obj=transaction.posting_date,
                format_string=date_string_format
            ),
            "Description": transaction.description,
            "Details": transaction.details,
            "Type": transaction.transaction_type,
            "CheckOrSlipNum": transaction.check_num
        }
