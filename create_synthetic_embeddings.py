"""
This script creates synthetic embeddings and stores them in ChromaDB.
It does not connect to the MongoDB datalake.
"""
from langchain_core.documents import Document
from features_pipeline.vectorstore import ChromaVectorStore
from features_pipeline.logger import get_logger

# Use default configuration from daemon.py
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_EMBEDDINGS_COLLECTION_CHROMA = "babylon_vectors_synthetic"
DEFAULT_CHROMA_HOST = 'localhost'
DEFAULT_CHROMA_PORT = 8003

_LOGGER = get_logger()

def create_synthetic_embeddings():
    """
    Creates synthetic embeddings and stores them in ChromaDB.
    """
    _LOGGER.info("Starting synthetic embedding creation.")

    # 1. Create mock documents
    mock_documents = [
        Document(page_content="Transaction: Credit card payment for $250.34 at 'ONLINE STORE' on 2024-07-20."),
        Document(page_content="Transaction: ATM withdrawal of $100.00 at 'DOWNTOWN BANK' on 2024-07-20."),
        Document(page_content="Transaction: Direct deposit of $1500.00 from 'ACME CORP' on 2024-07-19."),
        Document(page_content="Transaction: Venmo payment of $25.50 to 'John Doe' for 'Lunch' on 2024-07-19."),
        Document(page_content="Transaction: Zelle payment of $120.00 from 'Jane Smith' for 'Rent' on 2024-07-18."),
    ]
    _LOGGER.info(f"Created {len(mock_documents)} mock documents.")

    try:
        # 2. Instantiate ChromaVectorStore to get the native client and delete the collection
        _LOGGER.info("Connecting to ChromaDB to clear any existing collection.")
        vector_store_for_delete = ChromaVectorStore(
            model=DEFAULT_EMBEDDING_MODEL,
            collection=DEFAULT_EMBEDDINGS_COLLECTION_CHROMA,
            host=DEFAULT_CHROMA_HOST,
            port=DEFAULT_CHROMA_PORT,
            sqlite_dir=None
        )

        try:
            vector_store_for_delete.native_client.delete_collection(name=DEFAULT_EMBEDDINGS_COLLECTION_CHROMA)
            _LOGGER.info(f"Cleared existing collection '{DEFAULT_EMBEDDINGS_COLLECTION_CHROMA}'.")
        except Exception:
            _LOGGER.info(f"Collection '{DEFAULT_EMBEDDINGS_COLLECTION_CHROMA}' did not exist, so no need to clear.")

        # 3. Re-initialize the VectorStore to ensure a fresh collection is created
        _LOGGER.info("Initializing a new vector store for adding documents.")
        vector_store = ChromaVectorStore(
            model=DEFAULT_EMBEDDING_MODEL,
            collection=DEFAULT_EMBEDDINGS_COLLECTION_CHROMA,
            host=DEFAULT_CHROMA_HOST,
            port=DEFAULT_CHROMA_PORT,
            sqlite_dir=None
        )
        _LOGGER.info(f"Initialized ChromaVectorStore with collection '{DEFAULT_EMBEDDINGS_COLLECTION_CHROMA}'.")


        # 4. Add documents to ChromaVectorStore
        _LOGGER.info("Adding documents to ChromaDB...")
        vector_store.add_documents(mock_documents)
        _LOGGER.info(f"Successfully added {len(mock_documents)} documents to ChromaDB.")

        # 5. Verification step
        _LOGGER.info("Verifying embeddings...")
        retrieved_docs = vector_store.db_client.similarity_search(query="Show me all transactions", k=5)
        _LOGGER.info(f"Found {len(retrieved_docs)} documents in collection.")
        for i, doc in enumerate(retrieved_docs):
            _LOGGER.info(f"  {i+1}. {doc.page_content}")
            
    except Exception as e:
        _LOGGER.error(f"An error occurred: {e}", exc_info=True)
        _LOGGER.info("Please ensure ChromaDB is running and accessible.")

if __name__ == "__main__":
    create_synthetic_embeddings()
