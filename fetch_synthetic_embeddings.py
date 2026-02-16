"""
This script fetches synthetic embeddings from ChromaDB.
It validates that `create_synthetic_embeddings.py` is working as intended.
"""
from features_pipeline.vectorstore import ChromaVectorStore
from features_pipeline.logger import get_logger

# Use default configuration from create_synthetic_embeddings.py
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_EMBEDDINGS_COLLECTION_CHROMA = "babylon_vectors_synthetic"
DEFAULT_CHROMA_HOST = 'localhost'
DEFAULT_CHROMA_PORT = 8003

_LOGGER = get_logger()

def fetch_synthetic_embeddings():
    """
    Fetches synthetic embeddings from ChromaDB and displays them.
    """
    _LOGGER.info("Starting to fetch synthetic embeddings.")

    try:
        # 1. Instantiate ChromaVectorStore
        vector_store = ChromaVectorStore(
            model=DEFAULT_EMBEDDING_MODEL,
            collection=DEFAULT_EMBEDDINGS_COLLECTION_CHROMA,
            host=DEFAULT_CHROMA_HOST,
            port=DEFAULT_CHROMA_PORT,
            sqlite_dir=None
        )
        _LOGGER.info(f"Initialized ChromaVectorStore for collection '{DEFAULT_EMBEDDINGS_COLLECTION_CHROMA}'.")

        # 2. Fetch and display documents
        _LOGGER.info("Checking the number of items in the collection...")
        collection_count = vector_store.db_client._collection.count()
        _LOGGER.info(f"Collection '{DEFAULT_EMBEDDINGS_COLLECTION_CHROMA}' contains {collection_count} documents.")

        if collection_count > 0:
            _LOGGER.info("Fetching documents from ChromaDB using a similarity search...")
            
            # A generic query to retrieve all (or most) documents
            query_text = "Show me all transactions" 
            retrieved_docs = vector_store.db_client.similarity_search(query=query_text, k=10) # Fetch up to 10 documents

            if retrieved_docs:
                _LOGGER.info(f"Successfully fetched {len(retrieved_docs)} documents:")
                for i, doc in enumerate(retrieved_docs):
                    _LOGGER.info(f"  {i+1}. Content: {doc.page_content}")
                    if doc.metadata:
                        _LOGGER.info(f"     Metadata: {doc.metadata}")
            else:
                _LOGGER.warning(f"Could not retrieve documents with query '{query_text}', even though the collection is not empty.")
        else:
            _LOGGER.warning("The collection is empty. Please ensure `create_synthetic_embeddings.py` has been run successfully.")

    except Exception as e:
        _LOGGER.error(f"An error occurred: {e}", exc_info=True)
        _LOGGER.info("Please ensure ChromaDB is running and accessible.")

if __name__ == "__main__":
    fetch_synthetic_embeddings()
