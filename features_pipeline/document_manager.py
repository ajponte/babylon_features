"""Service object for building a vectorized document."""
import logging

from langchain_core.documents import Document

from features_pipeline.error import RAGError

logging.basicConfig(level='DEBUG')

_LOGGER = logging.getLogger(__name__)


class BabylonDocumentManager:
    __slots__ = ('_collection', '_datalake_document')

    def __init__(self, collection: str, datalake_document):
        self._collection = collection
        self._datalake_document = datalake_document

    def build_langchain_document(self) -> Document:
        """
        Build and return a langchain document.

        :return: The document.
        """
        try:
            return Document(
                page_content=self.build_document_content(),
                metadata=self.build_document_metadata()
            )
        except Exception as e:
            message = f'Error building langchain doc. Err: {e}'
            raise RAGError(message=message, cause=e) from e

    def build_document_content(self) -> str:
        """
        Convert transaction data into a concise, readable text chunk.
        The structure of the text content is crucial for RAG performance.

        :return: Formatted content for RAG.
        """
        _LOGGER.info(f'Building RAG document for collection {self._collection}')
        content = (
            f"On {self._datalake_document.get('PostingDate', 'N/A')}, a transaction occurred with details: "
            f"Description: {self._datalake_document.get('Description', 'N/A')}. "
            f"Amount: ${self._datalake_document.get('Amount', 0.0):.2f}. "
            f"Type: {self._datalake_document.get('Type', 'N/A')}."
        )

        return content

    def build_document_metadata(self) -> dict[str, str]:
        """
        Build metadata for a LangChain document.

        :return: Metadata as a dict.
        """
        # The metadata retains useful filtering info (like the source collection/date)
        _LOGGER.info(f'Building RAG metadata for collection {self._collection}')
        metadata = {
            "source_collection": self._collection,
            "transaction_date": self._datalake_document.get("PostingDate"),
            "amount": self._datalake_document.get("Amount"),
            "type": self._datalake_document.get("Type"),
            # Add all other fields as metadata for advanced filtering
            **self._datalake_document
        }
        return metadata
