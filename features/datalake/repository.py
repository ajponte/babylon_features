# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments
"""
Datalake records repository pattern
"""

from datetime import date
from pymongo.collection import Collection
from bson import ObjectId

from features.error import RAGError
from features.utils import convert_string_to_date, convert_date_to_string

DEFAULT_DATE_STRING_FORMAT = "%m/%d/%Y"


class TransactionDto:
    """Transaction mapped DTO."""
    def __init__(
        self,
        record_id: str,
        amount: float,
        posting_date: date,
        details: str,
        tx_type: str,
        description: str,
        check_num: str | None = "",
    ):
        self._record_id = record_id
        self._amount = amount
        self._posting_date = posting_date
        self._details = details
        self._tx_type = tx_type
        self._description = description
        self._check_num = check_num

        # Quick validation
        self.__check_required_fields()

    @property
    def id(self) -> str:
        """Return the ID of the datalake document."""
        return self._record_id

    @property
    def amount(self) -> float:
        """Return the dollar amount of the datalake transaction document."""
        return self._amount

    @property
    def posting_date(self) -> date:
        """Return the posting date of the datalake transaction document."""
        return self._posting_date

    @property
    def description(self) -> str:
        """Return the description of the datalake transaction document."""
        return self._description

    @property
    def details(self) -> str:
        """Return the details of the datalake transaction document."""
        return self._details

    @property
    def transaction_type(self) -> str:
        """Return the transaction type of the datalake transaction document."""
        return self._tx_type

    @property
    def check_num(self) -> str | None:
        """Return the check number of the datalake transaction document."""
        return self._check_num

    # todo: fix string interpolation error.
    # pylint:disable=invalid-str-returned
    def __str__(self):
        return str(
            f"(id, {self.id}, ",
            f"(amount, {self.amount}), ",
            f"(posting_date, {self.posting_date})",
        )

    def __check_required_fields(self) -> None:
        """Ensure that all required fields are present.

        :raise RAGError: If a required field is not present.
        """
        if not all([self.id, self.posting_date, self.description, self.details]):
            message = "Not all required fields are present for DTO"
            raise RAGError(message)


class BaseRepository:
    """Represents a Mongo Repository Collection."""
    def __init__(self, collection: Collection, mapper):
        """Constructor.

        :param collection: The mongo collection.
        :param mapper: Data domain mapper.
        """
        self._collection = collection
        self._mapper = mapper

    def get_by_id(self, _id: str) -> TransactionDto | None:
        """Return a document from the collection by document ID."""
        doc = self._collection.find_one({"_id": ObjectId(_id)})
        return self._mapper.to_domain(doc) if doc else None

    def get_all(self) -> list[TransactionDto]:
        """Return all documents from the collection."""
        results = [self._mapper.to_domain(doc) for doc in self._collection.find({})]
        return [r for r in results if r is not None]

    def get_by_filter(self, filter_criteria: dict) -> list[TransactionDto]:
        """Apply a filter and return matching documents from the collection."""
        results = [
            self._mapper.to_domain(doc)
            for doc in self._collection.find(filter_criteria)
        ]
        return [r for r in results if r is not None]

    @property
    def collection(self):
        """Return the Mongo Collection this Repository points to."""
        return self._collection


class TransactionRepository(BaseRepository):
    """Represents the transactions collection."""
    def __init__(self, collection: Collection):
        super().__init__(collection=collection, mapper=TransactionMapper)

    def get_by_id(self, transaction_id: str) -> TransactionDto | None:
        """Return a transaction by document ID."""
        doc = self._collection.find_one({"_id": ObjectId(transaction_id)})
        return self._mapper.to_domain(doc) if doc else None

    def get_by_filter(self, filter_criteria: dict) -> list[TransactionDto]:
        """Apply a filter and return matching documents from the collection."""
        docs: list[dict] = list(self._collection.find(filter_criteria) or [])
        results = [self._mapper.to_domain(doc) for doc in docs]
        return [r for r in results if r is not None]


class TransactionMapper:
    """Holds static methods for document conversion."""
    @staticmethod
    def to_domain(
        doc: dict, date_string_format: str | None = DEFAULT_DATE_STRING_FORMAT
    ) -> TransactionDto | None:
        """Convert a mongo doc, represented by key/value pairs, into a transaction DTO."""
        try:
            return TransactionDto(
                record_id=str(doc["_id"]),
                amount=doc["Amount"],
                posting_date=convert_string_to_date(
                    date_string=doc["PostingDate"],  # type: ignore
                    format_string=date_string_format,  # type: ignore
                ),
                description=doc["Description"],
                details=doc["Details"],
                tx_type=doc["Type"],
                # Optional
                check_num=doc.get("CheckOrSlipNum", None),
            )
        except Exception:
            # Skip invalid records.
            return None

    @staticmethod
    def to_document(
        transaction: TransactionDto,
        date_string_format: str | None = DEFAULT_DATE_STRING_FORMAT,
    ) -> dict:
        """Convert a Transaction DTO to a key/value pair."""
        return {
            "_id": ObjectId(transaction.id),
            "Amount": transaction.amount,
            "PostingDate": convert_date_to_string(
                date_obj=transaction.posting_date,
                format_string=date_string_format,  # type: ignore
            ),
            "Description": transaction.description,
            "Details": transaction.details,
            "Type": transaction.transaction_type,
            "CheckOrSlipNum": transaction.check_num,
        }
