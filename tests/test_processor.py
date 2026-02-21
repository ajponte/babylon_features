import pytest
from unittest.mock import MagicMock, patch
from langchain_core.documents import Document
from features.processor import CollectionProcessor

@pytest.fixture
def mock_vector_store():
    return MagicMock()

@pytest.fixture
def mock_repository():
    repo = MagicMock()
    repo.collection.name = "test_collection"
    return repo

def test_collection_processor_batch_number(mock_vector_store):
    processor = CollectionProcessor(mock_vector_store)
    assert processor.batch_number == 0
    
    # We need a mock repo that returns empty list to just test batch increment
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
    mock_splitter_class, 
    mock_build_doc, 
    mock_vector_store, 
    mock_repository
):
    # Setup
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
    
    # Act
    processor.process(mock_repository)
    
    # Assert
    mock_repository.get_by_filter.assert_called_once_with({})
    mock_build_doc.assert_called_once_with(source=mock_transaction, collection="test_collection")
    mock_splitter.split_documents.assert_called_once_with([mock_doc])
    mock_vector_store.add_documents.assert_called_once_with([mock_chunk])
    assert processor.batch_number == 1

@patch("features.processor.build_langchain_document")
def test_collection_processor_process_skip_error(
    mock_build_doc, 
    mock_vector_store, 
    mock_repository
):
    # Setup
    processor = CollectionProcessor(mock_vector_store)
    mock_transaction_1 = MagicMock()
    mock_transaction_1.id = "1"
    mock_transaction_2 = MagicMock()
    mock_transaction_2.id = "2"
    mock_repository.get_by_filter.return_value = [mock_transaction_1, mock_transaction_2]
    
    # Fail first, succeed second
    mock_build_doc.side_effect = [Exception("error"), Document(page_content="success")]
    
    # Act
    processor.process(mock_repository)
    
    # Assert
    # Should still call add_documents with the successful one
    assert mock_vector_store.add_documents.called
    added_docs = mock_vector_store.add_documents.call_args[0][0]
    assert len(added_docs) > 0
    assert processor.batch_number == 1

def test_collection_processor_no_docs(mock_vector_store, mock_repository):
    processor = CollectionProcessor(mock_vector_store)
    mock_repository.get_by_filter.return_value = []
    
    processor.process(mock_repository)
    
    mock_vector_store.add_documents.assert_not_called()
    assert processor.batch_number == 1
