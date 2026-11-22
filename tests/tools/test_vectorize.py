# pylint: disable=redefined-outer-name
"""Unit tests for standalone vectorize CLI tool."""

from datetime import date
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from features.datalake.repository import TransactionDto
from features.tools.vectorize import (
    COLLECTIONS,
    main,
    resolve_collections,
    validate_chunking,
)

VALID_OBJECT_ID = "507f1f77bcf86cd799439011"


def new_test_dto(**overrides: Any) -> TransactionDto:
    """Domain builder for test TransactionDto instances."""
    payload: dict[str, Any] = {
        "record_id": VALID_OBJECT_ID,
        "amount": 42.50,
        "posting_date": date(2023, 1, 15),
        "details": "grocery purchase",
        "tx_type": "DEBIT",
        "description": "Supermarket Store #42",
        "check_num": "001",
    }
    payload.update(overrides)
    return TransactionDto(**payload)


def test_vectorize_help() -> None:
    """Verify --help exits 0 and displays all documented CLI flags."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "--collection" in result.output
    assert "--limit" in result.output
    assert "--vector-db" in result.output
    assert "--dry-run" in result.output
    assert "--chunk-size" in result.output
    assert "--chunk-overlap" in result.output


@patch("features.tools.vectorize.build_store")
@patch("features.tools.vectorize.resolve_repositories")
def test_vectorize_dry_run_success(
    mock_resolve_repos: MagicMock,
    mock_build_store: MagicMock,
) -> None:
    """Verify dry-run mode chunks records and prints summary without store calls (P2-D4)."""
    mock_repo = MagicMock()
    mock_repo.get_by_filter.return_value = [new_test_dto()]
    mock_resolve_repos.return_value = [("transactions_chase", mock_repo)]

    runner = CliRunner()
    result = runner.invoke(main, ["--dry-run"])

    assert result.exit_code == 0
    assert "Chunks Generated     : 1" in result.output
    assert "Dry Run Mode         : True (No writes performed)" in result.output
    mock_build_store.assert_not_called()


@patch("features.tools.vectorize.build_store")
@patch("features.tools.vectorize.resolve_repositories")
def test_vectorize_persists_to_chroma(
    mock_resolve_repos: MagicMock,
    mock_build_store: MagicMock,
) -> None:
    """Verify --vector-db chroma constructs ChromaVectorStore and persists chunks."""
    mock_repo = MagicMock()
    mock_repo.get_by_filter.return_value = [new_test_dto()]
    mock_resolve_repos.return_value = [("transactions_chase", mock_repo)]

    mock_store = MagicMock()
    mock_build_store.return_value = mock_store

    runner = CliRunner()
    result = runner.invoke(main, ["--vector-db", "chroma"])

    assert result.exit_code == 0
    mock_build_store.assert_called_once_with("chroma")
    assert mock_store.add_documents.called
    added_chunks = mock_store.add_documents.call_args[0][0]
    assert len(added_chunks) == 1
    assert "Dry Run Mode         : False (Persisted successfully)" in result.output


@patch("features.tools.vectorize.build_store")
@patch("features.tools.vectorize.resolve_repositories")
def test_vectorize_persists_to_qdrant(
    mock_resolve_repos: MagicMock,
    mock_build_store: MagicMock,
) -> None:
    """Verify --vector-db qdrant constructs QdrantVectorStore and persists chunks."""
    mock_repo = MagicMock()
    mock_repo.get_by_filter.return_value = [new_test_dto()]
    mock_resolve_repos.return_value = [("transactions_chase", mock_repo)]

    mock_store = MagicMock()
    mock_build_store.return_value = mock_store

    runner = CliRunner()
    result = runner.invoke(main, ["--vector-db", "qdrant"])

    assert result.exit_code == 0
    mock_build_store.assert_called_once_with("qdrant")
    assert mock_store.add_documents.called
    added_chunks = mock_store.add_documents.call_args[0][0]
    assert len(added_chunks) == 1


@patch("features.tools.vectorize.build_store")
@patch("features.tools.vectorize.resolve_repositories")
def test_vectorize_with_limit(
    mock_resolve_repos: MagicMock,
    _mock_build_store: MagicMock,
) -> None:
    """Verify --limit parameter is forwarded to repository query."""
    mock_repo = MagicMock()
    mock_repo.get_by_filter.return_value = [new_test_dto()]
    mock_resolve_repos.return_value = [("transactions_chase", mock_repo)]

    runner = CliRunner()
    result = runner.invoke(main, ["--limit", "10", "--dry-run"])

    assert result.exit_code == 0
    mock_repo.get_by_filter.assert_called_once_with({}, limit=10)
    assert "Record Limit Applied : 10" in result.output


@patch("features.tools.vectorize.build_store")
@patch("features.tools.vectorize.resolve_repositories")
def test_vectorize_single_collection(
    mock_resolve_repos: MagicMock,
    _mock_build_store: MagicMock,
) -> None:
    """Verify targeting a single collection resolves only the requested repository."""
    mock_repo = MagicMock()
    mock_repo.get_by_filter.return_value = []
    mock_resolve_repos.return_value = [("transactions_chase", mock_repo)]

    runner = CliRunner()
    result = runner.invoke(main, ["--collection", "transactions_chase", "--dry-run"])

    assert result.exit_code == 0
    mock_resolve_repos.assert_called_once_with(["transactions_chase"])
    assert "Target Collection(s) : transactions_chase" in result.output


def test_vectorize_invalid_collection() -> None:
    """Verify unknown collection exits non-zero and lists available choices."""
    runner = CliRunner()
    result = runner.invoke(main, ["--collection", "non_existent_collection"])

    assert result.exit_code != 0
    assert "Unknown collection 'non_existent_collection'" in result.output
    assert (
        "Available collections: transactions_chase, transactions_synthetic"
        in result.output
    )


@patch("features.tools.vectorize.chunk_transactions")
@patch("features.tools.vectorize.build_store")
@patch("features.tools.vectorize.resolve_repositories")
def test_vectorize_custom_chunking(
    mock_resolve_repos: MagicMock,
    _mock_build_store: MagicMock,
    mock_chunk_tx: MagicMock,
) -> None:
    """Verify custom chunk_size and chunk_overlap are passed to chunk_transactions."""
    mock_repo = MagicMock()
    mock_records = [new_test_dto()]
    mock_repo.get_by_filter.return_value = mock_records
    mock_resolve_repos.return_value = [("transactions_chase", mock_repo)]
    mock_chunk_tx.return_value = []

    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--chunk-size", "500", "--chunk-overlap", "50", "--dry-run"],
    )

    assert result.exit_code == 0
    mock_chunk_tx.assert_called_once_with(
        mock_records,
        collection_name="transactions_chase",
        chunk_size=500,
        chunk_overlap=50,
    )


@pytest.mark.parametrize(
    ("chunk_size", "chunk_overlap"),
    [
        ("100", "100"),
        ("50", "100"),
    ],
)
def test_vectorize_overlap_not_less_than_size(
    chunk_size: str, chunk_overlap: str
) -> None:
    """Verify chunk_overlap >= chunk_size exits non-zero with BadParameter message (P2-D5)."""
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--chunk-size", chunk_size, "--chunk-overlap", chunk_overlap],
    )

    assert result.exit_code != 0
    assert "chunk_overlap" in result.output
    assert "must be strictly less than chunk_size" in result.output


@patch("features.tools.vectorize.build_store")
@patch("features.tools.vectorize.resolve_repositories")
def test_vectorize_empty_collection(
    mock_resolve_repos: MagicMock,
    mock_build_store: MagicMock,
) -> None:
    """Verify empty collection produces 0 chunks and exits 0 without store calls."""
    mock_repo = MagicMock()
    mock_repo.get_by_filter.return_value = []
    mock_resolve_repos.return_value = [("transactions_chase", mock_repo)]

    runner = CliRunner()
    result = runner.invoke(main, ["--vector-db", "chroma"])

    assert result.exit_code == 0
    mock_build_store.assert_not_called()
    assert "Documents Fetched    : 0" in result.output
    assert "Chunks Generated     : 0" in result.output


def test_resolve_collections_all() -> None:
    """Verify 'all' (case-insensitive) returns all configured collections."""
    assert resolve_collections("all") == list(COLLECTIONS)
    assert resolve_collections("ALL") == list(COLLECTIONS)


def test_validate_chunking_positive_size() -> None:
    """Verify validate_chunking rejects non-positive size and negative overlap."""
    with pytest.raises(Exception):
        validate_chunking(0, 0)
    with pytest.raises(Exception):
        validate_chunking(100, -1)
