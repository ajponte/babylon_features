# pylint: disable=redefined-outer-name
"""Unit tests for collection processor and chunk_transactions."""

from datetime import date
import logging
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from features.datalake.repository import TransactionDto
from features.processor import CollectionProcessor, _LOGGER, chunk_transactions

VALID_OBJECT_ID = "507f1f77bcf86cd799439011"


@pytest.fixture(autouse=True)
def enable_logger_propagation():
    """Ensure features logger propagates to root logger for caplog capture."""
    original_propagate = _LOGGER.propagate
    _LOGGER.propagate = True
    yield
    _LOGGER.propagate = original_propagate


def new_valid_dto(**overrides: Any) -> TransactionDto:
    """Domain builder for valid TransactionDto instances with test defaults."""
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


@pytest.fixture
def mock_vector_store() -> MagicMock:
    """Fixture returning a mock VectorStore."""
    return MagicMock()


@pytest.fixture
def mock_repository() -> MagicMock:
    """Fixture returning a mock Mongo repository with collection metadata."""
    repo = MagicMock()
    repo.collection.name = "test_collection"
    return repo


def test_collection_processor_batch_number(mock_vector_store: MagicMock) -> None:
    """Verify batch number increments upon each process invocation."""
    processor = CollectionProcessor(mock_vector_store)
    assert processor.batch_number == 0

    repo = MagicMock()
    repo.collection.name = "test"
    repo.get_by_filter.return_value = []

    processor.process(repo)
    assert processor.batch_number == 1

    processor.process(repo)
    assert processor.batch_number == 2


def test_collection_processor_rejects_none_repository(
    mock_vector_store: MagicMock,
) -> None:
    """Verify CollectionProcessor.process raises TypeError when repository is None."""
    processor = CollectionProcessor(mock_vector_store)
    with pytest.raises(TypeError, match="mongo_repository cannot be None"):
        processor.process(None)  # type: ignore[arg-type]


@patch("features.processor.build_langchain_document")
@patch("features.processor.RecursiveCharacterTextSplitter")
def test_collection_processor_process_success(
    mock_splitter_class: MagicMock,
    mock_build_doc: MagicMock,
    mock_vector_store: MagicMock,
    mock_repository: MagicMock,
) -> None:
    """Verify process builds docs, splits chunks, and persists to vector store."""
    processor = CollectionProcessor(mock_vector_store)
    mock_transaction = MagicMock()
    mock_transaction.id = "123"
    mock_repository.get_by_filter.return_value = [mock_transaction]

    mock_doc = Document(page_content="original content")
    mock_build_doc.return_value = mock_doc

    mock_splitter = MagicMock()
    mock_splitter_class.return_value = mock_splitter
    mock_chunk = Document(page_content="chunk content")
    mock_splitter.split_documents.return_value = [mock_chunk]

    processor.process(mock_repository)

    mock_repository.get_by_filter.assert_called_once_with({})
    mock_build_doc.assert_called_once_with(
        source=mock_transaction, collection="test_collection"
    )
    mock_splitter.split_documents.assert_called_once_with([mock_doc])
    mock_vector_store.add_documents.assert_called_once_with([mock_chunk])
    assert processor.batch_number == 1


@patch("features.processor.build_langchain_document")
def test_collection_processor_process_skip_error(
    mock_build_doc: MagicMock,
    mock_vector_store: MagicMock,
    mock_repository: MagicMock,
) -> None:
    """Verify errors on individual records are skipped without aborting remaining records."""
    processor = CollectionProcessor(mock_vector_store)
    mock_transaction_1 = MagicMock()
    mock_transaction_1.id = "1"
    mock_transaction_2 = MagicMock()
    mock_transaction_2.id = "2"
    mock_repository.get_by_filter.return_value = [
        mock_transaction_1,
        mock_transaction_2,
    ]

    mock_build_doc.side_effect = [
        Exception("error"),
        Document(page_content="success"),
    ]

    processor.process(mock_repository)

    assert mock_vector_store.add_documents.called
    added_docs = mock_vector_store.add_documents.call_args[0][0]
    assert len(added_docs) == 1
    assert processor.batch_number == 1


def test_collection_processor_no_docs(
    mock_vector_store: MagicMock, mock_repository: MagicMock
) -> None:
    """Verify empty collection does not invoke vector store add_documents."""
    processor = CollectionProcessor(mock_vector_store)
    mock_repository.get_by_filter.return_value = []

    processor.process(mock_repository)

    mock_vector_store.add_documents.assert_not_called()
    assert processor.batch_number == 1


def test_process_default_chunking_unchanged(
    mock_vector_store: MagicMock, mock_repository: MagicMock
) -> None:
    """Verify CollectionProcessor.process produces chunks with default parameters."""
    dto = new_valid_dto(description="Weekly grocery shopping at local market")
    mock_repository.get_by_filter.return_value = [dto]
    processor = CollectionProcessor(mock_vector_store)

    processor.process(mock_repository)

    assert mock_vector_store.add_documents.called
    added_chunks = mock_vector_store.add_documents.call_args[0][0]
    assert len(added_chunks) == 1
    chunk = added_chunks[0]
    assert "Weekly grocery shopping at local market" in chunk.page_content
    assert chunk.metadata["source_collection"] == "test_collection"
    assert "start_index" in chunk.metadata
    assert processor.batch_number == 1


@pytest.mark.parametrize(
    ("size", "overlap", "expected_err", "match_pattern"),
    [
        (0, 0, ValueError, "chunk_size must be a positive integer"),
        (-10, 0, ValueError, "chunk_size must be a positive integer"),
        (100, -1, ValueError, "chunk_overlap must be non-negative"),
        (100, 100, ValueError, "must be strictly less than chunk_size"),
        (100, 150, ValueError, "must be strictly less than chunk_size"),
        (True, 0, TypeError, "chunk_size must be an integer, got: bool"),
        (100, False, TypeError, "chunk_overlap must be an integer, got: bool"),
        ("100", 10, TypeError, "chunk_size must be an integer, got: str"),
        (100, "10", TypeError, "chunk_overlap must be an integer, got: str"),
    ],
)
def test_chunk_transactions_rejects_invalid_parameters(
    size: Any, overlap: Any, expected_err: type[Exception], match_pattern: str
) -> None:
    """Verify boundary and type violations in chunk_size/chunk_overlap raise errors."""
    with pytest.raises(expected_err, match=match_pattern):
        chunk_transactions(
            [], collection_name="col", chunk_size=size, chunk_overlap=overlap
        )


def test_chunk_transactions_rejects_none_transactions() -> None:
    """Verify passing transactions=None raises TypeError."""
    with pytest.raises(TypeError, match="transactions cannot be None"):
        chunk_transactions(None, collection_name="col")  # type: ignore[arg-type]


@pytest.mark.parametrize("invalid_col", ["", "   ", None])
def test_chunk_transactions_rejects_invalid_collection_name(
    invalid_col: Any,
) -> None:
    """Verify passing empty, whitespace, or non-string collection_name raises ValueError."""
    with pytest.raises(ValueError, match="collection_name must be a non-empty string"):
        chunk_transactions([], collection_name=invalid_col)


def test_chunk_transactions_honors_size_and_overlap() -> None:
    """Verify custom chunk_size and chunk_overlap are respected during splitting."""
    long_desc = "Word " * 300
    dto = new_valid_dto(description=long_desc)

    chunks = chunk_transactions(
        [dto],
        collection_name="test_col",
        chunk_size=500,
        chunk_overlap=50,
    )

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.page_content) <= 500
        assert chunk.metadata["source_collection"] == "test_col"
        assert "start_index" in chunk.metadata


def test_chunk_transactions_adds_start_index() -> None:
    """Verify chunk metadata always contains start_index."""
    dto = new_valid_dto()
    chunks = chunk_transactions([dto], collection_name="test_col")

    assert len(chunks) == 1
    for chunk in chunks:
        assert "start_index" in chunk.metadata
        assert isinstance(chunk.metadata["start_index"], int)


@patch("features.processor.build_langchain_document")
def test_chunk_transactions_skips_failing_record(
    mock_build_doc: MagicMock,
) -> None:
    """Verify failing record is skipped while subsequent valid records are chunked."""
    dto_failing = new_valid_dto(record_id="failing-tx")
    dto_ok = new_valid_dto(record_id="valid-tx")

    mock_doc = Document(
        page_content="Valid transaction content", metadata={"id": "valid-tx"}
    )
    mock_build_doc.side_effect = [ValueError("Document build error"), mock_doc]

    chunks = chunk_transactions([dto_failing, dto_ok], collection_name="test_col")

    assert len(chunks) == 1
    assert "Valid transaction content" in chunks[0].page_content


def test_chunk_transactions_logs_skip_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify expected errors log warning with record ID and continue."""
    dto_failing = new_valid_dto(record_id="failing-tx-999")
    with patch(
        "features.processor.build_langchain_document",
        side_effect=ValueError("Corrupt schema"),
    ):
        with caplog.at_level(logging.WARNING):
            chunks = chunk_transactions([dto_failing], collection_name="test_col")
    assert not chunks
    assert "failing-tx-999" in caplog.text
    assert "Corrupt schema" in caplog.text


def test_chunk_transactions_fallback_record_id_unknown(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify fallback to 'unknown' when record has no id attribute."""
    invalid_record = MagicMock(spec=[])  # Object without 'id' attribute
    with patch(
        "features.processor.build_langchain_document",
        side_effect=ValueError("No ID"),
    ):
        with caplog.at_level(logging.WARNING):
            chunks = chunk_transactions([invalid_record], collection_name="test_col")
    assert not chunks
    assert "unknown" in caplog.text


def test_chunk_transactions_logs_unexpected_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify unexpected exceptions log at ERROR level with exc_info."""
    dto = new_valid_dto(record_id="unexpected-err-tx")
    with patch(
        "features.processor.build_langchain_document",
        side_effect=RuntimeError("Unexpected system failure"),
    ):
        with caplog.at_level(logging.ERROR):
            chunks = chunk_transactions([dto], collection_name="test_col")
    assert not chunks
    assert "unexpected-err-tx" in caplog.text
    assert "Unexpected error while building/chunking" in caplog.text


def test_chunk_transactions_streaming_generator() -> None:
    """Verify chunk_transactions consumes generator iterables correctly."""
    dtos = [new_valid_dto(record_id=VALID_OBJECT_ID) for _ in range(5)]
    generator_input = (d for d in dtos)

    chunks = chunk_transactions(generator_input, collection_name="stream_col")
    assert len(chunks) == 5
    assert all(c.metadata["source_collection"] == "stream_col" for c in chunks)
    assert all(c.metadata["source_document_id"] == VALID_OBJECT_ID for c in chunks)


def test_chunk_transactions_metadata_completeness() -> None:
    """Verify chunk preserves all required metadata fields from TransactionDto."""
    dto = new_valid_dto(
        record_id=VALID_OBJECT_ID,
        amount=99.95,
        posting_date=date(2025, 6, 1),
    )
    chunks = chunk_transactions([dto], collection_name="verified_col")

    assert len(chunks) == 1
    meta = chunks[0].metadata
    assert meta["source_document_id"] == VALID_OBJECT_ID
    assert meta["source_collection"] == "verified_col"
    assert meta["amount"] == 99.95
    assert meta["transaction_date"] == "06/01/2025"
    assert meta["start_index"] == 0


def test_chunk_transactions_text_overlap_continuity() -> None:
    """Verify consecutive chunks share overlapping tokens across split boundaries."""
    text = "Alpha Beta Gamma Delta Epsilon Zeta Eta Theta Iota Kappa Lambda Mu " * 20
    dto = new_valid_dto(description=text)

    chunks = chunk_transactions(
        [dto], collection_name="col", chunk_size=200, chunk_overlap=40
    )
    assert len(chunks) > 1
    for i in range(len(chunks) - 1):
        tail_of_current = chunks[i].page_content[-30:]
        head_of_next = chunks[i + 1].page_content[:60]
        overlap_tokens = set(tail_of_current.split()) & set(head_of_next.split())
        assert len(overlap_tokens) >= 1


def test_chunk_transactions_sparse_dto() -> None:
    """Verify chunking succeeds on sparse DTOs with empty optional fields."""
    dto = TransactionDto(
        record_id=VALID_OBJECT_ID,
        amount=10.0,
        posting_date=date(2025, 1, 1),
        description="Minimal",
        details=None,
        check_num=None,
    )
    chunks = chunk_transactions([dto], collection_name="col")
    assert len(chunks) == 1
    assert "Minimal" in chunks[0].page_content


def test_chunk_transactions_empty_input() -> None:
    """Verify empty transactions iterable returns an empty list."""
    assert not chunk_transactions([], collection_name="test_col")
