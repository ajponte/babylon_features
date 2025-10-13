"""
ADT for representing a collection of mongo db records.
https://refactoring.guru/design-patterns/iterator/python/example#example-0
"""
import logging
from collections.abc import Iterator, Iterable
from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document

from features_pipeline.datalake import Datalake
from features_pipeline.error import DocumentsCollectionError
from features_pipeline.utils import create_random_uuid_hex

logging.basicConfig(level='DEBUG')

_LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True)
class ProcessedRecordMetaData:
    """Represents a processed langchain document metadata."""
    metadata: dict[str, str]

class DocumentsCollection(Iterable):
    def __init__(
        self, db_cursor
    ):
        self._records: list[ProcessedRecordMetaData] = []
        # Assign a random UUID if the collection is unnamed.
        self._collection_id = None or create_random_uuid_hex()
        self._db_cursor = db_cursor

    def __getitem__(self, index: int) -> Any:
        """Return the metadata record previously processed."""
        return self._db_cursor

    def __iter__(self) -> 'DocumentsIter':
        """
        The __iter__() method returns the iterator object itself.
        """
        return DocumentsIter(self)

    def add_record(self, record: Any) -> None:
        self._records.append(record)

    def is_empty(self) -> bool:
        """Return True only if there are no more mongo records to process."""
        return self._db_cursor.count() == 0

    @property
    def id(self) -> str:
        """
        Return unique identifier.

        :return: Collection unique identifier.
        """
        return self._collection_id

    @property
    def size(self) -> int:
        """
        Return the number of records are cached in this collection.

        :return: Number of records.
        """
        return len(self._records)

    @property
    def purge(self) -> None:
        """
        Purge all internal records.
        """
        try:
            del self._records
            self._records = []
        except Exception as e:
            message = f'Error purging documents: {e}'
            raise DocumentsCollectionError(message=message, cause=e) from e

        if len(self._records) > 0:
            raise DocumentsCollectionError(message='No records were purged!')

class DocumentsIter(Iterator):
    """
    Concrete Iterators implement various traversal algorithms. These classes
    store the current traversal position at all times.
    """

    """
    `_position` attribute stores the current traversal position. An iterator may
    have a lot of other fields for storing iteration state, especially when it
    is supposed to work with a particular kind of collection.
    """
    _position: int = None

    def __init__(self, collection: DocumentsCollection) -> None:
        self._collection = collection
        self._collection_id = collection.id
        self._position = 0

    def __next__(self) -> Document:
        """
        The __next__() method must return the next item in the sequence. On
        reaching the end, and in subsequent calls, it must raise StopIteration.
        """
        if self._collection.is_empty():
            raise StopIteration("No more records to process")
        source_data = self._collection[self._position]
        self._position += 1
        doc = self.build_langchain_document(source_data)
        return doc

    def build_langchain_document(self, source) -> Document:
        """
        Build and return a langchain document.

        :param source: Source data mapping record.
        :return: The document.
        """
        # The ID of the source record. We remove this
        # so that it's not part of the new doc content.
        # However, we will add it to metadata.
        source_id = source.pop('_id', None)
        return Document(
            page_content=self.build_document_content(source),
            metadata=self.build_document_metadata(
                source=source, source_id=source_id),
            id=create_random_uuid_hex()
        )

    def build_document_content(self, source: dict) -> str:
        """
        Convert transaction data into a concise, readable text chunk.
        The structure of the text content is crucial for RAG performance.

        :param source: Source data mapping.
        :return: Formatted content for RAG.
        """
        _LOGGER.info(f'Building RAG document for collection {self._collection}')
        content = (
            f"On {source.get('PostingDate', 'N/A')}, a transaction occurred with details: "
            f"Description: {source.get('Description', 'N/A')}. "
            f"Amount: ${source.get('Amount', 0.0):.2f}. "
            f"Type: {source.get('Type', 'N/A')}."
        )

        return content

    def build_document_metadata(self, source: dict, source_id: str | None = None) -> dict[str, str]:
        """
        Build metadata for a LangChain document.

        :param source: Data source mapping.
        :param source_id: Id of the source data record.
        :return: Metadata as a dict.
        """
        # The metadata retains useful filtering info (like the source collection/date)
        _LOGGER.info(f'Building RAG metadata for collection {self._collection.id}')
        metadata = {
            "source_collection": self._collection.id,
            "source_document_id": source_id,
            "transaction_date": source.get("PostingDate"),
            "amount": source.get("Amount"),
            "type": source.get("Type"),
            # Add all other fields as metadata for advanced filtering
            **source
        }
        return metadata
