"""Unit tests for collection processor and chunk_transactions."""

from datetime import date
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from features.datalake.repository import TransactionDto
from features.processor import CollectionProcessor, chunk_transactions

VALID_OBJECT_ID = "507f1f77bcf86cd799439011"


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

    mock_build_doc.side_effect = [Exception("error"), Document(page_content="success")]

    processor.process(mock_repository)

    assert mock_vector_store.add_documents.called
    added_docs = mock_vector_store.add_documents.call_args[0][0]
    assert len(added_docs) > 0
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
    assert len(added_chunks) >= 1
    chunk = added_chunks[0]
    assert "Weekly grocery shopping at local market" in chunk.page_content
    assert chunk.metadata["source_collection"] == "test_collection"
    assert "start_index" in chunk.metadata
    assert processor.batch_number == 1


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

    assert len(chunks) >= 1
    for chunk in chunks:
        assert "start_index" in chunk.metadata
        assert isinstance(chunk.metadata["start_index"], int)


@patch("features.processor.build_langchain_document")
def test_chunk_transactions_skips_failing_record(mock_build_doc: MagicMock) -> None:
    """Verify failing record is skipped while subsequent valid records are chunked."""
    dto_failing = new_valid_dto(record_id="failing-tx")
    dto_ok = new_valid_dto(record_id="valid-tx")

    mock_doc = Document(
        page_content="Valid transaction content", metadata={"id": "valid-tx"}
    )
    mock_build_doc.side_effect = [ValueError("Document build error"), mock_doc]

    chunks = chunk_transactions([dto_failing, dto_ok], collection_name="test_col")

    assert len(chunks) >= 1
    assert any("Valid transaction content" in c.page_content for c in chunks)


def test_chunk_transactions_empty_input() -> None:
    """Verify empty transactions iterable returns an empty list."""
    assert chunk_transactions([], collection_name="test_col") == []
