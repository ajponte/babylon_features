# pylint: disable=redefined-outer-name
"""
Unit tests for datalake repository and TransactionDto.
"""

from datetime import date, datetime
from typing import Any
from unittest.mock import MagicMock
from bson import ObjectId
import pytest

from features.datalake.repository import (
    BaseRepository,
    TransactionDto,
    TransactionMapper,
    TransactionRepository,
    _apply_limit,
    coerce_amount,
    coerce_date,
)
from features.error import RAGError

VALID_OBJECT_ID = "507f1f77bcf86cd799439011"


def new_valid_dto(**overrides: Any) -> TransactionDto:
    """Domain builder for valid TransactionDto instances with test defaults."""
    payload: dict[str, Any] = {
        "record_id": "tx-12345",
        "amount": 42.50,
        "posting_date": date(2023, 1, 15),
        "details": "grocery purchase",
        "tx_type": "DEBIT",
        "description": "Supermarket Store #42",
        "check_num": "001",
    }
    payload.update(overrides)
    return TransactionDto(**payload)


def new_raw_doc(**overrides: Any) -> dict[str, Any]:
    """Domain builder for valid MongoDB raw transaction document dicts."""
    doc: dict[str, Any] = {
        "_id": ObjectId(VALID_OBJECT_ID),
        "Amount": 42.50,
        "PostingDate": "01/15/2023",
        "Description": "Supermarket Store #42",
        "Details": "grocery purchase",
        "Type": "DEBIT",
        "CheckOrSlipNum": "001",
    }
    doc.update(overrides)
    return doc


@pytest.fixture
def mock_collection() -> MagicMock:
    """Return a mock pymongo Collection with chainable find cursor."""
    collection = MagicMock()
    cursor = MagicMock()
    cursor.__iter__.return_value = []
    cursor.limit.return_value = cursor
    collection.find.return_value = cursor
    return collection


@pytest.mark.parametrize(
    ("overrides", "should_succeed"),
    [
        ({}, True),
        ({"details": ""}, True),
        ({"details": None}, True),
        ({"check_num": ""}, True),
        ({"check_num": None}, True),
        ({"record_id": ""}, False),
        ({"posting_date": None}, False),
        ({"description": ""}, False),
    ],
)
def test_transaction_dto_creation_and_validation(
    overrides: dict[str, Any], should_succeed: bool
) -> None:
    """Verify DTO validation rules for presence and optionality of fields."""
    if should_succeed:
        dto = new_valid_dto(**overrides)
        assert dto.id is not None
    else:
        with pytest.raises(RAGError):
            new_valid_dto(**overrides)


def test_transaction_dto_details_none_normalized() -> None:
    """Verify details=None is normalized to an empty string."""
    dto = new_valid_dto(details=None)
    assert dto.details == ""


def test_transaction_dto_str_is_well_formed() -> None:
    """Verify str(dto) returns a well-formed string representation without error."""
    dto = new_valid_dto()
    result = str(dto)

    assert isinstance(result, str)
    assert dto.id in result
    assert str(dto.amount) in result
    assert str(dto.posting_date) in result
    assert dto.description in result
    assert dto.transaction_type in result
    assert str(dto.check_num) in result

    expected = (
        f"TransactionDto(id='{dto.id}', amount={dto.amount}, "
        f"posting_date={dto.posting_date}, description='{dto.description}', "
        f"type='{dto.transaction_type}', check_num='{dto.check_num}')"
    )
    assert result == expected


def test_apply_limit_null_cursor() -> None:
    """Verify _apply_limit returns an empty list when cursor is None."""
    assert _apply_limit(None, None) == []
    assert _apply_limit(None, 10) == []


def test_apply_limit_passthrough_when_limit_is_none() -> None:
    """Verify _apply_limit returns the unchanged cursor when limit is None."""
    cursor = MagicMock()
    assert _apply_limit(cursor, None) is cursor
    cursor.limit.assert_not_called()


def test_apply_limit_boundary_one() -> None:
    """Verify _apply_limit correctly delegates limit=1 to cursor."""
    cursor = MagicMock()
    cursor.limit.return_value = cursor
    result = _apply_limit(cursor, 1)

    assert result is cursor
    cursor.limit.assert_called_once_with(1)


@pytest.mark.parametrize("invalid_limit", [True, False, 1.5, "10", []])
def test_repository_limit_rejects_invalid_types(
    mock_collection: MagicMock, invalid_limit: Any
) -> None:
    """Verify non-integer or boolean limit values raise TypeError."""
    mapper = MagicMock()
    repo = BaseRepository(collection=mock_collection, mapper=mapper)
    expected_type = type(invalid_limit).__name__
    expected_message = f"Limit must be an integer, got: {expected_type}"

    with pytest.raises(TypeError, match=expected_message):
        repo.get_all(limit=invalid_limit)

    with pytest.raises(TypeError, match=expected_message):
        repo.get_by_filter({}, limit=invalid_limit)

    with pytest.raises(TypeError, match=expected_message):
        _apply_limit(MagicMock(), limit=invalid_limit)


@pytest.mark.parametrize("limit", [0, -1])
def test_repository_limit_rejects_non_positive(
    mock_collection: MagicMock, limit: int
) -> None:
    """Verify non-positive limit values raise ValueError with descriptive message."""
    mapper = MagicMock()
    repo = BaseRepository(collection=mock_collection, mapper=mapper)
    expected_message = f"Limit must be a positive integer, got: {limit}"

    with pytest.raises(ValueError, match=expected_message):
        repo.get_all(limit=limit)

    with pytest.raises(ValueError, match=expected_message):
        repo.get_by_filter({}, limit=limit)

    with pytest.raises(ValueError, match=expected_message):
        _apply_limit(MagicMock(), limit=limit)


def test_repository_get_all_with_limit(mock_collection: MagicMock) -> None:
    """Verify get_all with limit delegates limit parameter and filters out None."""
    dto = new_valid_dto()
    mapper = MagicMock()
    mapper.to_domain.side_effect = [dto, None]
    mock_collection.find.return_value.__iter__.return_value = [
        {"_id": "1"},
        {"_id": "2"},
    ]
    repo = BaseRepository(collection=mock_collection, mapper=mapper)

    results = repo.get_all(limit=10)

    mock_collection.find.assert_called_once_with({})
    mock_collection.find.return_value.limit.assert_called_once_with(10)
    assert results == [dto]


def test_repository_get_all_without_limit(mock_collection: MagicMock) -> None:
    """Verify get_all without limit does not call cursor limit and returns mapped results."""
    dto = new_valid_dto()
    mapper = MagicMock()
    mapper.to_domain.side_effect = [dto, None]
    mock_collection.find.return_value.__iter__.return_value = [
        {"_id": "1"},
        {"_id": "2"},
    ]
    repo = BaseRepository(collection=mock_collection, mapper=mapper)

    results = repo.get_all()

    mock_collection.find.assert_called_once_with({})
    mock_collection.find.return_value.limit.assert_not_called()
    assert results == [dto]


def test_repository_get_all_null_cursor(mock_collection: MagicMock) -> None:
    """Verify get_all safely handles null cursor without error."""
    mock_collection.find.return_value = None
    mapper = MagicMock()
    repo = BaseRepository(collection=mock_collection, mapper=mapper)

    results = repo.get_all()

    assert results == []


def test_repository_get_by_filter_with_limit(mock_collection: MagicMock) -> None:
    """Verify get_by_filter with limit delegates filter and limit and filters None."""
    dto = new_valid_dto()
    mapper = MagicMock()
    mapper.to_domain.side_effect = [dto, None]
    mock_collection.find.return_value.__iter__.return_value = [
        {"_id": "1"},
        {"_id": "2"},
    ]
    repo = BaseRepository(collection=mock_collection, mapper=mapper)
    criteria = {"transaction_type": "DEBIT"}

    results = repo.get_by_filter(criteria, limit=5)

    mock_collection.find.assert_called_once_with(criteria)
    mock_collection.find.return_value.limit.assert_called_once_with(5)
    assert results == [dto]


def test_repository_get_by_filter_without_limit(mock_collection: MagicMock) -> None:
    """Verify get_by_filter without limit does not call cursor limit and returns mapped results."""
    dto = new_valid_dto()
    mapper = MagicMock()
    mapper.to_domain.side_effect = [dto]
    mock_collection.find.return_value.__iter__.return_value = [{"_id": "1"}]
    repo = BaseRepository(collection=mock_collection, mapper=mapper)
    criteria = {"transaction_type": "DEBIT"}

    results = repo.get_by_filter(criteria)

    mock_collection.find.assert_called_once_with(criteria)
    mock_collection.find.return_value.limit.assert_not_called()
    assert results == [dto]


def test_repository_get_by_filter_null_cursor(mock_collection: MagicMock) -> None:
    """Verify get_by_filter safely handles null cursor without error."""
    mock_collection.find.return_value = None
    mapper = MagicMock()
    repo = BaseRepository(collection=mock_collection, mapper=mapper)

    results = repo.get_by_filter({"key": "val"})

    assert results == []


def test_repository_collection_property(mock_collection: MagicMock) -> None:
    """Verify collection property returns underlying Mongo collection."""
    repo = BaseRepository(collection=mock_collection, mapper=MagicMock())
    assert repo.collection is mock_collection


def test_transaction_repository_get_all(mock_collection: MagicMock) -> None:
    """Verify TransactionRepository get_all passes limit and maps documents to DTOs."""
    doc = new_raw_doc()
    mock_collection.find.return_value.__iter__.return_value = [doc, {"corrupt": True}]
    repo = TransactionRepository(collection=mock_collection)

    results = repo.get_all(limit=10)

    mock_collection.find.assert_called_once_with({})
    mock_collection.find.return_value.limit.assert_called_once_with(10)
    assert len(results) == 1
    assert results[0].id == VALID_OBJECT_ID
    assert results[0].amount == 42.50


def test_transaction_repository_get_by_filter(mock_collection: MagicMock) -> None:
    """Verify TransactionRepository get_by_filter delegates filter and limit."""
    doc = new_raw_doc()
    mock_collection.find.return_value.__iter__.return_value = [doc]
    repo = TransactionRepository(collection=mock_collection)
    criteria = {"Type": "DEBIT"}

    results = repo.get_by_filter(criteria, limit=None)

    mock_collection.find.assert_called_once_with(criteria)
    mock_collection.find.return_value.limit.assert_not_called()
    assert len(results) == 1
    assert results[0].id == VALID_OBJECT_ID


def test_repository_get_by_id_valid_found(mock_collection: MagicMock) -> None:
    """Verify get_by_id returns mapped DTO when document exists."""
    doc = new_raw_doc()
    mock_collection.find_one.return_value = doc
    repo = TransactionRepository(collection=mock_collection)

    result = repo.get_by_id(VALID_OBJECT_ID)

    mock_collection.find_one.assert_called_once_with({"_id": ObjectId(VALID_OBJECT_ID)})
    assert result is not None
    assert result.id == VALID_OBJECT_ID


def test_repository_get_by_id_valid_not_found(mock_collection: MagicMock) -> None:
    """Verify get_by_id returns None when document is not found."""
    mock_collection.find_one.return_value = None
    repo = TransactionRepository(collection=mock_collection)

    result = repo.get_by_id(VALID_OBJECT_ID)

    mock_collection.find_one.assert_called_once_with({"_id": ObjectId(VALID_OBJECT_ID)})
    assert result is None


@pytest.mark.parametrize("invalid_id", ["", "invalid-object-id", "12345", "not_an_id!"])
def test_repository_get_by_id_invalid_id_returns_none(
    mock_collection: MagicMock, invalid_id: str
) -> None:
    """Verify get_by_id returns None for empty or malformed ObjectId string without calling DB."""
    repo = TransactionRepository(collection=mock_collection)

    result = repo.get_by_id(invalid_id)

    assert result is None
    mock_collection.find_one.assert_not_called()


def test_transaction_mapper_camel_case_chase() -> None:
    """Verify canonical Chase doc with datetime postingDate and camelCase keys maps to valid DTO."""
    doc = {
        "_id": ObjectId(VALID_OBJECT_ID),
        "amount": 42.50,
        "postingDate": datetime(2025, 10, 22, 14, 0),
        "description": "Supermarket Store #42",
        "details": "grocery purchase",
        "transactionType": "DEBIT",
        "checkOrSlipNum": "001",
    }
    dto = TransactionMapper.to_domain(doc)

    assert dto is not None
    assert dto.id == VALID_OBJECT_ID
    assert dto.amount == 42.50
    assert dto.posting_date == date(2025, 10, 22)
    assert dto.description == "Supermarket Store #42"
    assert dto.details == "grocery purchase"
    assert dto.transaction_type == "DEBIT"
    assert dto.check_num == "001"


def test_transaction_mapper_pascal_case_legacy() -> None:
    """Verify legacy doc with string MM/DD/YYYY PostingDate and PascalCase keys maps identically."""
    doc = new_raw_doc()
    dto = TransactionMapper.to_domain(doc)

    assert dto is not None
    assert dto.id == VALID_OBJECT_ID
    assert dto.amount == 42.50
    assert dto.posting_date == date(2023, 1, 15)
    assert dto.description == "Supermarket Store #42"
    assert dto.details == "grocery purchase"
    assert dto.transaction_type == "DEBIT"
    assert dto.check_num == "001"


@pytest.mark.parametrize(
    ("date_input", "expected_date"),
    [
        (datetime(2025, 10, 22, 14, 0), date(2025, 10, 22)),
        (date(2025, 10, 22), date(2025, 10, 22)),
        ("2025-10-22", date(2025, 10, 22)),
        ("10/22/2025", date(2025, 10, 22)),
        ("2025-10-22T14:00:00Z", date(2025, 10, 22)),
        ("unparseable-date", None),
    ],
)
def test_transaction_mapper_date_coercion_matrix(
    date_input: Any, expected_date: date | None
) -> None:
    """Verify date coercion matrix supports datetime, date, ISO string, US format, and rejects invalid strings."""
    doc = new_raw_doc(PostingDate=date_input)
    dto = TransactionMapper.to_domain(doc)

    if expected_date is None:
        assert dto is None
    else:
        assert dto is not None
        assert dto.posting_date == expected_date


@pytest.mark.parametrize(
    ("amount_input", "expected_amount"),
    [
        (42, 42.0),
        (42.50, 42.5),
        ("$1,234.56", 1234.56),
        (0, 0.0),
    ],
)
def test_transaction_mapper_amount_coercion(
    amount_input: Any, expected_amount: float
) -> None:
    """Verify amount coercion handles int, float, currency strings, and zero without fallback."""
    doc = new_raw_doc(Amount=amount_input)
    dto = TransactionMapper.to_domain(doc)

    assert dto is not None
    assert dto.amount == expected_amount


def test_transaction_mapper_missing_optional_fields() -> None:
    """Verify doc without details, checkOrSlipNum, or transactionType maps with safe defaults."""
    doc = {
        "_id": ObjectId(VALID_OBJECT_ID),
        "amount": 50.0,
        "postingDate": date(2025, 5, 1),
        "description": "Minimal Transaction",
    }
    dto = TransactionMapper.to_domain(doc)

    assert dto is not None
    assert dto.id == VALID_OBJECT_ID
    assert dto.amount == 50.0
    assert dto.posting_date == date(2025, 5, 1)
    assert dto.description == "Minimal Transaction"
    assert dto.details == ""
    assert dto.transaction_type == "UNKNOWN"
    assert dto.check_num == ""


@pytest.mark.parametrize(
    "corrupt_doc",
    [
        {"_id": ObjectId(VALID_OBJECT_ID), "Amount": 10.0, "PostingDate": "01/15/2023"},
        {
            "_id": ObjectId(VALID_OBJECT_ID),
            "Amount": 10.0,
            "PostingDate": "01/15/2023",
            "Description": "",
        },
        {
            "_id": ObjectId(VALID_OBJECT_ID),
            "Amount": 10.0,
            "PostingDate": "unparseable-date",
            "Description": "Test",
        },
        {
            "_id": ObjectId(VALID_OBJECT_ID),
            "Amount": "not-an-amount",
            "PostingDate": "01/15/2023",
            "Description": "Test",
        },
        {
            "_id": ObjectId(VALID_OBJECT_ID),
            "Amount": True,
            "PostingDate": "01/15/2023",
            "Description": "Test",
        },
    ],
)
def test_transaction_mapper_invalid_record_returns_none(
    corrupt_doc: dict[str, Any],
) -> None:
    """Verify mapper returns None for missing description, unparseable date, or invalid amount."""
    assert TransactionMapper.to_domain(corrupt_doc) is None


@pytest.mark.parametrize(
    "invalid_value",
    [
        None,
        True,
        False,
        "not-a-number",
        "$not-a-number",
        "",
        [],
    ],
)
def test_coerce_amount_rejects_unsupported_type(invalid_value: Any) -> None:
    """Verify coerce_amount raises ValueError for None, booleans, and invalid strings."""
    with pytest.raises(ValueError):
        coerce_amount(invalid_value)


def test_to_document_snapshot() -> None:
    """Verify to_document output remains strictly backward-compatible with legacy schema."""
    dto = new_valid_dto(
        record_id=VALID_OBJECT_ID,
        amount=42.50,
        posting_date=date(2023, 1, 15),
        description="Supermarket Store #42",
        details="grocery purchase",
        tx_type="DEBIT",
        check_num="001",
    )
    doc = TransactionMapper.to_document(dto)

    expected = {
        "_id": ObjectId(VALID_OBJECT_ID),
        "Amount": 42.50,
        "PostingDate": "01/15/2023",
        "Description": "Supermarket Store #42",
        "Details": "grocery purchase",
        "Type": "DEBIT",
        "CheckOrSlipNum": "001",
    }
    assert doc == expected
