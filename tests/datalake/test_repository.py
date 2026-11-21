# pylint: disable=redefined-outer-name
"""
Unit tests for datalake repository and TransactionDto.
"""

from datetime import date
from typing import Any
from unittest.mock import MagicMock
import pytest

from features.datalake.repository import (
    BaseRepository,
    TransactionDto,
    TransactionRepository,
)
from features.error import RAGError


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


def test_repository_get_all_with_limit(mock_collection: MagicMock) -> None:
    """Verify get_all with limit delegates limit parameter to cursor."""
    mapper = MagicMock()
    repo = BaseRepository(collection=mock_collection, mapper=mapper)

    repo.get_all(limit=10)

    mock_collection.find.assert_called_once_with({})
    mock_collection.find.return_value.limit.assert_called_once_with(10)


def test_repository_get_all_without_limit(mock_collection: MagicMock) -> None:
    """Verify get_all without limit does not call cursor limit."""
    mapper = MagicMock()
    repo = BaseRepository(collection=mock_collection, mapper=mapper)

    repo.get_all()

    mock_collection.find.assert_called_once_with({})
    mock_collection.find.return_value.limit.assert_not_called()


def test_repository_get_by_filter_with_limit(mock_collection: MagicMock) -> None:
    """Verify get_by_filter with limit delegates filter and limit to collection and cursor."""
    mapper = MagicMock()
    repo = BaseRepository(collection=mock_collection, mapper=mapper)
    criteria = {"transaction_type": "DEBIT"}

    repo.get_by_filter(criteria, limit=5)

    mock_collection.find.assert_called_once_with(criteria)
    mock_collection.find.return_value.limit.assert_called_once_with(5)


def test_transaction_repository_get_by_filter_with_limit(
    mock_collection: MagicMock,
) -> None:
    """Verify TransactionRepository get_by_filter passes filter and limit to cursor."""
    repo = TransactionRepository(collection=mock_collection)
    criteria = {"transaction_type": "DEBIT"}

    repo.get_by_filter(criteria, limit=5)

    mock_collection.find.assert_called_once_with(criteria)
    mock_collection.find.return_value.limit.assert_called_once_with(5)


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
