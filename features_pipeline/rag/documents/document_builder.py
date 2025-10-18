"""Methods for building RAG documents."""

from langchain_core.documents import Document

from features_pipeline.logger import get_logger
from features_pipeline.utils import create_random_uuid_hex


_LOGGER = get_logger()


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
    source_id = source.pop("_id", None)
    langchain_id = None
    if source_id is not None:
        # Crucial fix: convert the ObjectId (or any non-string ID) to a string
        langchain_id = str(source_id)

        # 3. Handle missing ID (use a random one if source_id was None)
    if not langchain_id:
        langchain_id = create_random_uuid_hex()
        _LOGGER.info(f"Creating random ID: {langchain_id} for document")

    return Document(
        page_content=build_document_content(source, collection=collection),
        metadata=build_document_metadata(
            source=source, source_id=str(source_id), collection=collection
        ),
        id=langchain_id,
    )


def build_document_content(source: dict, collection: str) -> str:
    """
    Convert transaction data into a concise, readable text chunk.
    (Function content remains as you provided)
    """
    _LOGGER.info(f"Building RAG document for collection {collection}")
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
) -> dict[str, str | float | int | bool]:
    """
    Build metadata for a LangChain document, ensuring all values are simple types.

    :param source: Data source mapping (Note: '_id' has already been popped).
    :param collection: Name of collection.
    :param source_id: Id of the source data record (must be a str).
    :return: Metadata as a dict of simple types.
    """
    _LOGGER.info(f"Building RAG metadata for collection {collection}")

    # 1. Start with explicit metadata fields
    metadata = {
        "source_collection": collection,
        "source_document_id": source_id,
        "transaction_date": source.get("PostingDate"),
        "amount": source.get("Amount"),
        "type": source.get("Type"),
    }

    # 2. Safely add all other fields from the source dictionary
    for k, v in source.items():
        if k not in metadata:  # Avoid overriding explicit fields
            # Check for known complex types and convert to string
            if isinstance(v, (list, dict)):
                # If the value is a list or dict, skip it or convert it to a JSON string
                # Sticking to the error message's accepted types: str, int, float, bool.
                # For this fix, we'll convert simple non-serializable objects (like ObjectIds)
                # to str. If the value is another database ID/complex object, converting to str
                # should fix it.
                _LOGGER.warning(
                    f"Skipping complex metadata field '{k}' of type {type(v)}."
                    f"Use filter_complex_metadata for arrays/dicts."
                )
                continue  # Skip complex types like arrays/dicts unless you JSON encode them

            # Convert any custom non-serializable object (like ObjectId) to string
            if not isinstance(v, (str, int, float, bool, type(None))):
                metadata[k] = str(v)
            else:
                metadata[k] = v

    # 3. Clean up None values and return
    return {k: v for k, v in metadata.items() if v is not None}
