"""Test script for chroma vectors."""

import logging
from typing import Optional
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from features_pipeline.rag.vectorstore import ChromaVectorStore

logging.basicConfig(level='DEBUG')

_LOGGER = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = 'BAAI/bge-small-en-v1.5'
DEFAULT_CHROMA_SQLITE_DIR = './chromadb'
DEFAULT_EMBEDDINGS_COLLECTION_CHROMA = "my_document_collection"

def load_chroma_db(
        model_name: str,
        persist_directory: str = "./chromadb",
        collection_name: str = "my_document_collection",
        device: str = "cpu"
) -> Optional[Chroma]:
    """
    Loads a persisted Chroma vector store from disk.

    The model_name and device MUST match the parameters used during vectorization.

    :param model_name: The name of the HuggingFace model used for embeddings (e.g., 'BAAI/bge-small-en-v1.5').
    :param persist_directory: The local directory where the Chroma store files were saved.
    :param collection_name: The name of the collection to load.
    :param device: The computation device to use ('cpu', 'cuda', or 'mps').
    :return: The loaded Chroma vector store instance, or None if loading fails.
    """
    try:
        # Re-initialize the exact same embedding function
        embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={'device': device},
            encode_kwargs={'normalize_embeddings': True}
        )

        _LOGGER.info(f"Attempting to load Chroma DB from {persist_directory} using model {model_name}.")

        # Load the Chroma vector store by pointing to the directory and providing the embedding function
        vector_db = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=persist_directory,
        )

        # Optional: Check if the collection has documents to confirm successful load
        collection = vector_db._collection
        count = collection.count()

        if count == 0:
            _LOGGER.warning(f"Successfully connected to Chroma, but collection '{collection_name}' is empty.")
            return None

        _LOGGER.info(f"Successfully loaded Chroma DB. Collection '{collection_name}' contains {count} documents.")
        return vector_db

    except Exception as e:
        _LOGGER.error(f"Failed to load Chroma DB from disk: {e}")
        return None


def run_test_query(
        vector_db: ChromaVectorStore,
        query_text: str,
        k: int = 5
) -> list[tuple[Document, float]]:
    """
    Runs a similarity search against the loaded vector database and returns results
    with their relevance scores.

    :param vector_db: The initialized Chroma vector store.
    :param query_text: The text query to search for.
    :param k: The number of top relevant documents to retrieve.
    :return: A list of (Document, score) tuples.
    """
    if not vector_db:
        _LOGGER.error("Cannot run query: Vector database is not initialized or failed to load.")
        return []

    _LOGGER.info(f"Running similarity search for query: '{query_text}' (k={k})")

    # Use similarity_search_with_score to get both the document and the relevance score
    # Chroma scores are typically L2 distance or cosine similarity measures.
    results = vector_db.similarity_search(query_text=query_text, top_k=k)

    # Log the results for inspection
    for doc, score in results:
        _LOGGER.debug(f"Retrieved Document (Score: {score:.4f}): {doc.page_content[:80]}...")

    return results

def main():
    _LOGGER.info('testing chroma db')
    # vector_db = load_chroma_db(model_name=DEFAULT_EMBEDDING_MODEL)
    config = {
        'EMBEDDINGS_MODEL': DEFAULT_EMBEDDING_MODEL,
        'CHROMA_SQLITE_DIR': DEFAULT_CHROMA_SQLITE_DIR,
        'EMBEDDINGS_COLLECTION_CHROMA': DEFAULT_EMBEDDINGS_COLLECTION_CHROMA
    }

    vector_db = ChromaVectorStore(model=DEFAULT_EMBEDDING_MODEL, config=config)
    query = 'wholefoods'
    _LOGGER.info(f'Testing the query: {query}')
    results = run_test_query(vector_db=vector_db, query_text=query)
    _LOGGER.info(f'results: {results}')

if __name__ == '__main__':
    main()
