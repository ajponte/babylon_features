# pylint: disable=redefined-outer-name
"""Unit tests for standalone vectorize CLI tool."""

from datetime import date
from typing import Any
from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from features.datalake.repository import TransactionDto
from features.tools.vectorize import (
    COLLECTIONS,
    VectorizeSummary,
    build_store,
    main,
    resolve_collections,
    resolve_repositories,
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
    mock_build_store: MagicMock,
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
    mock_build_store.assert_not_called()


@patch("features.tools.vectorize.build_store")
@patch("features.tools.vectorize.resolve_repositories")
def test_vectorize_single_collection(
    mock_resolve_repos: MagicMock,
    mock_build_store: MagicMock,
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
    mock_build_store.assert_not_called()


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
    mock_build_store: MagicMock,
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
    mock_build_store.assert_not_called()


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


@patch("features.tools.vectorize.build_store")
@patch("features.tools.vectorize.resolve_repositories")
def test_vectorize_all_collections_aggregation(
    mock_resolve_repositories: MagicMock,
    mock_build_store: MagicMock,
) -> None:
    """Verify --collection all queries each collection and aggregates totals."""
    mock_repo_chase = MagicMock()
    mock_repo_chase.get_by_filter.return_value = [
        new_test_dto(record_id="507f1f77bcf86cd799439011"),
        new_test_dto(record_id="507f1f77bcf86cd799439012"),
    ]
    mock_repo_synth = MagicMock()
    mock_repo_synth.get_by_filter.return_value = [
        new_test_dto(record_id="507f1f77bcf86cd799439013"),
    ]
    mock_resolve_repositories.return_value = [
        ("transactions_chase", mock_repo_chase),
        ("transactions_synthetic", mock_repo_synth),
    ]

    runner = CliRunner()
    result = runner.invoke(main, ["--collection", "all", "--dry-run"])

    assert result.exit_code == 0
    assert mock_repo_chase.get_by_filter.called
    assert mock_repo_synth.get_by_filter.called
    assert (
        "Target Collection(s) : transactions_chase, transactions_synthetic"
        in result.output
    )
    assert "Documents Fetched    : 3" in result.output
    assert "Chunks Generated     : 3" in result.output
    mock_build_store.assert_not_called()


@pytest.mark.parametrize(
    ("size", "overlap", "expected_match"),
    [
        (0, 0, "chunk_size must be a positive integer"),
        (-5, 0, "chunk_size must be a positive integer"),
        (100, -1, "chunk_overlap must be a non-negative integer"),
        (100, 100, "must be strictly less than chunk_size"),
        (100, 150, "must be strictly less than chunk_size"),
        (True, 0, "chunk_size must be a positive integer"),
        (100, False, "chunk_overlap must be a non-negative integer"),
    ],
)
def test_validate_chunking_boundaries(
    size: Any, overlap: Any, expected_match: str
) -> None:
    """Verify validate_chunking raises BadParameter with accurate message."""
    with pytest.raises(click.BadParameter, match=expected_match):
        validate_chunking(size, overlap)


@pytest.mark.parametrize(
    ("args", "expected_msg"),
    [
        (["--limit", "0"], "0 is not in the range x>=1"),
        (["--limit", "-1"], "-1 is not in the range x>=1"),
        (["--chunk-size", "0"], "0 is not in the range x>=1"),
        (["--chunk-overlap", "-1"], "-1 is not in the range x>=0"),
    ],
)
def test_vectorize_cli_option_range_rejection(
    args: list[str], expected_msg: str
) -> None:
    """Verify Click rejects out-of-range option values with exit code 2."""
    runner = CliRunner()
    result = runner.invoke(main, args)
    assert result.exit_code == 2
    assert expected_msg in result.output


def test_vectorize_summary_render_permutations() -> None:
    """Verify VectorizeSummary.render branches for backends, limits, and dry-run."""
    summary_chroma = VectorizeSummary(
        collections=["col1"],
        limit=None,
        documents_fetched=10,
        chunks_generated=20,
        vector_db="chroma",
        dry_run=True,
        elapsed_seconds=1.23,
    )
    rendered = summary_chroma.render()
    assert "Target Collection(s) : col1" in rendered
    assert "Record Limit Applied : None (All)" in rendered
    assert "Vector Store Backend : ChromaDB (Persistent)" in rendered
    assert "Dry Run Mode         : True (No writes performed)" in rendered
    assert "Elapsed Time         : 1.23s" in rendered

    summary_qdrant = VectorizeSummary(
        collections=["col1", "col2"],
        limit=50,
        documents_fetched=50,
        chunks_generated=100,
        vector_db="qdrant",
        dry_run=False,
        elapsed_seconds=5.67,
    )
    rendered_q = summary_qdrant.render()
    assert "Target Collection(s) : col1, col2" in rendered_q
    assert "Record Limit Applied : 50" in rendered_q
    assert "Vector Store Backend : Qdrant (Cluster)" in rendered_q
    assert "Dry Run Mode         : False (Persisted successfully)" in rendered_q

    summary_custom = VectorizeSummary(
        collections=["col1"],
        limit=10,
        documents_fetched=10,
        chunks_generated=10,
        vector_db="custom_db",
        dry_run=False,
        elapsed_seconds=2.00,
    )
    assert "Vector Store Backend : custom_db" in summary_custom.render()


@patch("features.tools.vectorize.resolve_repositories")
def test_vectorize_extraction_failure_raises_click_exception(
    mock_resolve_repositories: MagicMock,
) -> None:
    """Verify extraction failure raises a clean click.ClickException."""
    mock_resolve_repositories.side_effect = RuntimeError("Database timeout")

    runner = CliRunner()
    result = runner.invoke(main, ["--dry-run"])

    assert result.exit_code != 0
    assert "Datalake extraction failed: Database timeout" in result.output


def test_resolve_collections_casing() -> None:
    """Verify resolve_collections handles 'all' case-insensitively and collections strictly."""
    assert resolve_collections("all") == list(COLLECTIONS)
    assert resolve_collections("ALL") == list(COLLECTIONS)
    assert resolve_collections("All") == list(COLLECTIONS)
    assert resolve_collections("transactions_chase") == ["transactions_chase"]

    with pytest.raises(ValueError, match="Unknown collection 'TRANSACTIONS_CHASE'"):
        resolve_collections("TRANSACTIONS_CHASE")


@patch("features.tools.vectorize.vector_store_factory")
def test_build_store_factory_routing(mock_factory: MagicMock) -> None:
    """Verify build_store sets VECTOR_DB_TYPE and delegates to factory."""
    build_store("chroma")
    assert mock_factory.call_args[0][0]["VECTOR_DB_TYPE"] == "chroma"

    build_store("Qdrant")
    assert mock_factory.call_args[0][0]["VECTOR_DB_TYPE"] == "qdrant"


@patch("features.tools.vectorize.MongoClientFactory.get_collection")
@patch("features.tools.vectorize.MongoClientFactory.get_client")
def test_resolve_repositories_wiring(
    mock_get_client: MagicMock,
    mock_get_coll: MagicMock,
) -> None:
    """Verify resolve_repositories resolves collections with client and db."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_coll = MagicMock()
    mock_get_coll.return_value = mock_coll

    repos = resolve_repositories(["transactions_chase"])
    assert len(repos) == 1
    assert repos[0][0] == "transactions_chase"
    mock_get_coll.assert_called_once()
