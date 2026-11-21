# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments
"""
Datalake records repository pattern
"""

from datetime import date, datetime
from typing import Any
from bson import ObjectId
from bson.errors import InvalidId
from pymongo.collection import Collection

from features.error import RAGError
from features.utils import convert_date_to_string

DEFAULT_DATE_STRING_FORMAT = "%m/%d/%Y"


class TransactionDto:
    """Transaction mapped DTO."""

    def __init__(
        self,
        record_id: str,
        amount: float,
        posting_date: date,
        details: str | None = None,
        tx_type: str = "",
        description: str = "",
        check_num: str | None = "",
    ):
        self._record_id = record_id
        self._amount = amount
        self._posting_date = posting_date
        self._details = "" if details is None else details
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

    def __str__(self) -> str:
        return (
            f"TransactionDto(id='{self.id}', amount={self.amount}, "
            f"posting_date={self.posting_date}, description='{self.description}', "
            f"type='{self.transaction_type}', check_num='{self.check_num}')"
        )

    def __check_required_fields(self) -> None:
        """Ensure that all required fields are present.

        :raise RAGError: If a required field is not present.
        """
        if not all([self.id, self.posting_date, self.description]):
            message = "Not all required fields are present for DTO"
            raise RAGError(message)


def _apply_limit(cursor: Any, limit: int | None) -> Any:
    """Apply query limit to a PyMongo cursor if specified.

    :param cursor: PyMongo cursor or iterable.
    :param limit: Maximum number of records to return.
    :return: Limited cursor or empty list if cursor is None.
    :raise TypeError: If limit is not an integer or is a boolean.
    :raise ValueError: If limit is less than or equal to 0.
    """
    if limit is not None:
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError(f"Limit must be an integer, got: {type(limit).__name__}")
        if limit <= 0:
            raise ValueError(f"Limit must be a positive integer, got: {limit}")
    if cursor is None:
        return []
    if limit is None:
        return cursor
    return cursor.limit(limit)


class BaseRepository:
    """Represents a Mongo Repository Collection."""

    def __init__(self, collection: Collection, mapper: Any) -> None:
        """Constructor.

        :param collection: The mongo collection.
        :param mapper: Data domain mapper.
        """
        self._collection = collection
        self._mapper = mapper

    def get_by_id(self, _id: str) -> TransactionDto | None:
        """Return a document from the collection by document ID."""
        if not _id or not ObjectId.is_valid(_id):
            return None
        try:
            doc = self._collection.find_one({"_id": ObjectId(_id)})
        except (InvalidId, TypeError):
            return None
        return self._mapper.to_domain(doc) if doc else None

    def get_all(self, limit: int | None = None) -> list[TransactionDto]:
        """Return all documents from the collection."""
        cursor = _apply_limit(self._collection.find({}), limit)
        results = [self._mapper.to_domain(doc) for doc in cursor or []]
        return [r for r in results if r is not None]

    def get_by_filter(
        self, filter_criteria: dict, limit: int | None = None
    ) -> list[TransactionDto]:
        """Apply a filter and return matching documents from the collection."""
        cursor = _apply_limit(self._collection.find(filter_criteria), limit)
        results = [self._mapper.to_domain(doc) for doc in cursor or []]
        return [r for r in results if r is not None]

    @property
    def collection(self) -> Collection:
        """Return the Mongo Collection this Repository points to."""
        return self._collection


def _first_present(doc: dict, *keys: str, default: Any = None) -> Any:
    """Return doc[key] for the first key that exists and is not None; otherwise default.

    :param doc: Dictionary to search for keys.
    :param keys: Ordered candidate keys to check.
    :param default: Fallback value returned if no key is present with a non-None value.
    :return: Value of first present, non-None key, or default.
    """
    for key in keys:
        if key in doc and doc[key] is not None:
            return doc[key]
    return default


def coerce_date(
    value: Any, default_format: str = DEFAULT_DATE_STRING_FORMAT
) -> date | None:
    """Coerce datetime, date, or a formatted string to datetime.date. None if unparseable.

    :param value: Input date value (datetime, date, str, or unsupported type).
    :param default_format: Primary strptime format pattern for string dates.
    :return: Parsed datetime.date object, or None on failure or unsupported type.
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        formats = (default_format, "%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d")
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt).date()
            except (ValueError, TypeError):
                continue
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except (ValueError, TypeError):
            return None
    return None


def coerce_amount(value: Any) -> float:
    """Coerce int, float, or currency string like '$1,234.56' to float.

    Raises ValueError otherwise.

    :param value: Input amount value.
    :return: Float representation of the amount.
    :raise ValueError: If the value cannot be coerced to float or is a bool.
    """
    if isinstance(value, bool):
        raise ValueError("Cannot coerce bool to float")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace("$", "").replace(",", "").strip()
        try:
            return float(cleaned)
        except ValueError as err:
            raise ValueError(f"Cannot coerce string '{value}' to float") from err
    raise ValueError(f"Cannot coerce {type(value).__name__} to float")


class TransactionMapper:
    """Holds static methods for document conversion."""

    @staticmethod
    def to_domain(
        doc: dict, date_string_format: str | None = DEFAULT_DATE_STRING_FORMAT
    ) -> TransactionDto | None:
        """Convert a mongo doc, represented by key/value pairs, into a transaction DTO."""
        try:
            fmt = date_string_format or DEFAULT_DATE_STRING_FORMAT
            posting_date = coerce_date(
                _first_present(doc, "postingDate", "PostingDate"),
                default_format=fmt,
            )
            if posting_date is None:
                return None
            return TransactionDto(
                record_id=str(doc["_id"]),
                amount=coerce_amount(_first_present(doc, "amount", "Amount")),
                posting_date=posting_date,
                description=_first_present(
                    doc, "description", "Description", default=""
                ),
                details=_first_present(doc, "details", "Details", default=""),
                tx_type=_first_present(
                    doc, "transactionType", "type", "Type", default="UNKNOWN"
                ),
                check_num=_first_present(
                    doc,
                    "checkOrSlipNum",
                    "CheckOrSlipNum",
                    "checkSlipNo",
                    "checkNumber",
                    default="",
                ),
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


class TransactionRepository(BaseRepository):
    """Represents the transactions collection."""

    def __init__(self, collection: Collection) -> None:
        super().__init__(collection=collection, mapper=TransactionMapper)
