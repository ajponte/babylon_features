"""Test script for chroma vectors."""

import logging
from langchain_core.documents import Document

from features_pipeline.rag.vectorstore import ChromaVectorStore

logging.basicConfig(level='DEBUG')

_LOGGER = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = 'BAAI/bge-small-en-v1.5'
DEFAULT_CHROMA_SQLITE_DIR = './chromadb'
DEFAULT_EMBEDDINGS_COLLECTION_CHROMA = 'babylon_vector_collection'


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
