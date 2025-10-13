import logging

from langchain_core.documents import Document

from features_pipeline.utils import create_random_uuid_hex

logging.basicConfig(level='DEBUG')

_LOGGER = logging.getLogger(__name__)

def build_langchain_document(source, collection: str) -> Document:
    """
    Build and return a langchain document.

    :param source: Source data mapping record.
    :param collection: Name of collection.
    :return: The document.
    """
    # The ID of the source record. We remove this
    # so that it's not part of the new doc content.
    # However, we will add it to metadata.
    source_id = source.pop('_id', None)
    return Document(
        page_content=build_document_content(source, collection=collection),
        metadata=build_document_metadata(
            source=source,
            source_id=source_id,
            collection=collection
        ),
        id=create_random_uuid_hex()
    )

def build_document_content(source: dict, collection: str) -> str:
    """
    Convert transaction data into a concise, readable text chunk.
    The structure of the text content is crucial for RAG performance.

    :param source: Source data mapping.
    :param collection: Collection name.
    :return: Formatted content for RAG.
    """
    _LOGGER.info(f'Building RAG document for collection {collection}')
    content = (
        f"On {source.get('PostingDate', 'N/A')}, a transaction occurred with details: "
        f"Description: {source.get('Description', 'N/A')}. "
        f"Amount: ${source.get('Amount', 0.0):.2f}. "
        f"Type: {source.get('Type', 'N/A')}."
    )

    return content

def build_document_metadata(
        source: dict,
        collection: str,
        source_id: str | None = None,
) -> dict[str, str]:
    """
    Build metadata for a LangChain document.

    :param source: Data source mapping.
    :param collection: Name of collection.
    :param source_id: Id of the source data record.
    :return: Metadata as a dict.
    """
    # The metadata retains useful filtering info (like the source collection/date)
    _LOGGER.info(f'Building RAG metadata for collection {collection}')
    metadata = {
        "source_collection": collection,
        "source_document_id": source_id,
        "transaction_date": source.get("PostingDate"),
        "amount": source.get("Amount"),
        "type": source.get("Type"),
        # Add all other fields as metadata for advanced filtering
        **source
    }
    return metadata
