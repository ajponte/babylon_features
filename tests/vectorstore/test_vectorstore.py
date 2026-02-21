import pytest
from unittest.mock import patch
from langchain_core.documents import Document
from features.vectorstore.vectorstore import (
    ChromaVectorStore,
    QdrantVectorStore,
    vector_store_factory
)

@pytest.fixture
def mock_embeddings():
    with patch("features.vectorstore.vectorstore.embeddings") as mock:
        yield mock

@pytest.fixture
def mock_chroma():
    with patch("features.vectorstore.vectorstore.Chroma") as mock:
        yield mock

@pytest.fixture
def mock_qdrant():
    with patch("features.vectorstore.vectorstore.LangchainQdrant") as mock_lq, \
         patch("features.vectorstore.vectorstore.QdrantClient") as mock_qc:
        yield mock_lq, mock_qc

def test_chroma_vector_store_add_documents(mock_embeddings, mock_chroma):
    store = ChromaVectorStore(model="BAAI/bge-small-en-v1.5", sqlite_dir="./tmp", collection="test")
    docs = [Document(page_content="hello")]
    store.add_documents(docs)
    store.db_client.add_documents.assert_called_once_with(docs)

def test_chroma_vector_store_similarity_search(mock_embeddings, mock_chroma):
    store = ChromaVectorStore(model="BAAI/bge-small-en-v1.5", sqlite_dir="./tmp", collection="test")
    mock_chroma.return_value.similarity_search_with_score.return_value = [ (Document(page_content="hi"), 0.1) ]
    
    results = store.similarity_search("hello")
    assert len(results) == 1
    assert results[0][0].page_content == "hi"

def test_qdrant_vector_store_add_documents(mock_embeddings, mock_qdrant):
    mock_lq, mock_qc = mock_qdrant
    store = QdrantVectorStore(model="BAAI/bge-small-en-v1.5", host="localhost", port=6333, collection="test")
    docs = [Document(page_content="hello")]
    store.add_documents(docs)
    mock_lq.return_value.add_documents.assert_called_once_with(docs)

def test_qdrant_vector_store_similarity_search(mock_embeddings, mock_qdrant):
    mock_lq, mock_qc = mock_qdrant
    store = QdrantVectorStore(model="BAAI/bge-small-en-v1.5", host="localhost", port=6333, collection="test")
    mock_lq.return_value.similarity_search_with_score.return_value = [ (Document(page_content="hi"), 0.1) ]
    
    results = store.similarity_search("hello")
    assert len(results) == 1
    assert results[0][0].page_content == "hi"

def test_vector_store_factory_chroma(mock_embeddings, mock_chroma):
    config = {
        "VECTOR_DB_TYPE": "chroma",
        "EMBEDDING_MODEL": "BAAI/bge-small-en-v1.5",
        "CHROMA_SQLITE_DIR": "./tmp",
        "EMBEDDINGS_COLLECTION_CHROMA": "test"
    }
    store = vector_store_factory(config)
    assert isinstance(store, ChromaVectorStore)

def test_vector_store_factory_qdrant(mock_embeddings, mock_qdrant):
    mock_lq, mock_qc = mock_qdrant
    config = {
        "VECTOR_DB_TYPE": "qdrant",
        "EMBEDDING_MODEL": "BAAI/bge-small-en-v1.5",
        "QDRANT_HOST": "localhost",
        "QDRANT_PORT": 6333,
        "QDRANT_COLLECTION": "test"
    }
    store = vector_store_factory(config)
    assert isinstance(store, QdrantVectorStore)

def test_vector_store_factory_invalid(mock_embeddings):
    config = {
        "VECTOR_DB_TYPE": "invalid",
        "EMBEDDING_MODEL": "BAAI/bge-small-en-v1.5"
    }
    with pytest.raises(ValueError, match="Unknown Vector DB type: invalid"):
        vector_store_factory(config)
