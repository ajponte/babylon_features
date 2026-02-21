"""DAOs for vectorized documents."""

import abc
import uuid

from typing_extensions import Generic, Type, TypeVar
import numpy as np
from pydantic import BaseModel, UUID4, Field
from qdrant_client.models import PointStruct, Record

from features.logger import get_logger
from features.vectorstore.vectorstore import VectorStore

BabylonVectorDocument = TypeVar(
    "BabylonVectorDocument", bound="BabylonVectorBasedDocument"
)

_LOGGER = get_logger()


class BabylonVectorBasedDocument(BaseModel, Generic[BabylonVectorDocument], abc.ABC):
    """Represents a Vectorized document in the Babylon domain."""

    _collection = "babylon_vectors"

    _id: UUID4 = Field(default_factory=uuid.uuid4)

    @property
    def id(self) -> UUID4:
        """Return the document ID."""
        return self._id

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self._id == other.id

    def __hash__(self) -> int:
        return hash(self._id)

    @classmethod
    def document_id(cls) -> UUID4:
        """Return the document ID."""
        return cls._id

    @classmethod
    def from_record(
        cls: Type[BabylonVectorDocument], point: Record
    ) -> BabylonVectorDocument:
        """Convert a Qdrant Record to a compatible Babylon vectorized document."""
        # Ensure point.id is a string for UUID conversion
        point_id_str = str(point.id)
        # pylint: disable=unexpected-keyword-arg
        _point_id = UUID4(
            point_id_str,
            version=4
        )
        payload = point.payload or {}

        attrs = {"id": _point_id, **payload}

        # Update internal embeddings.
        if cls._has_class_attrs("embedding"):  # type: ignore
            attrs["embedding"] = point.vector or None

        return cls(**attrs)

    @classmethod
    def search(
        cls: Type[BabylonVectorDocument],
        vector_store: VectorStore,
        query_vector: list,
        limit: int = 10,
        **kwargs,
    ) -> list[BabylonVectorDocument]:
        """Execute a search query against the vector db."""
        try:
            documents = cls._search(
                query_vector=query_vector,
                vector_store=vector_store,
                imit=limit,
                **kwargs,
            )
        except Exception as e:
            _LOGGER.debug(f"Error while searching documents: {e}")
            _LOGGER.info(
                f"Failed to search documents in '{cls.get_collection_name()}'."
            )
            documents = []

        return documents

    @classmethod
    def bulk_find(
        cls: Type[BabylonVectorDocument],
        vectorstore: VectorStore,
        limit: int = 10,
        **kwargs,
    ) -> tuple[list[BabylonVectorDocument], uuid.UUID | None]:
        """Execute a bulk find of vector documents."""
        offset = kwargs.pop("offset", None)
        offset = str(offset) if offset else None
        try:
            documents, next_offset = cls._bulk_find(
                vectorstore=vectorstore, limit=limit, offset=offset
            )
        except Exception as e:
            message = f"Failed to search documents in '{cls.get_collection_name()}'."
            _LOGGER.debug(f"{message}\nError: {e}")
            _LOGGER.info(message)
            documents, next_offset = [], None

        return documents, next_offset

    @classmethod
    def get_collection_name(cls) -> str:
        """Return the name of the collection this document points to."""
        return cls._collection

    @classmethod
    def _bulk_find(
        cls: Type[BabylonVectorDocument],
        vectorstore: VectorStore,
        offset: str | None = None,
        limit: int = 10,
        **kwargs,
    ) -> tuple[list[BabylonVectorDocument], uuid.UUID | None]:
        collection_name = cls.get_collection_name()

        records, next_offset = vectorstore.bulk_find(
            collection_name=collection_name, offset=offset, limit=limit, **kwargs
        )

        documents = [cls.from_record(record) for record in records]  # type: ignore

        if next_offset is not None:
            next_offset = uuid.UUID(next_offset, version=4)

        return documents, next_offset

    @classmethod
    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-positional-arguments
    def _search(
        cls: Type[BabylonVectorDocument],
        vector_store: VectorStore,
        query_vector: list,
        limit: int = 10,
        with_payload: bool = True,
        with_vectors: bool = True,
        **kwargs,
    ) -> list[BabylonVectorDocument]:
        """Execute a search query on the vector DB."""
        collection_name = cls.get_collection_name()
        records: list[Record] = vector_store.search_collection(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            with_payload=with_payload,
            with_vectors=with_vectors,
            **kwargs,
        )
        return [cls.from_record(record) for record in records]  # type: ignore

    def to_point(self: BabylonVectorDocument, **kwargs) -> PointStruct:
        """Convert a vector document to an embedded point."""
        exclude_unset = kwargs.pop("exclude_unset", False)
        by_alias = kwargs.pop("by_alias", True)

        payload = self.model_dump(
            exclude_unset=exclude_unset, by_alias=by_alias, **kwargs
        )

        _embedded_vector_id = str(payload.pop("id"))
        vector = payload.pop("embedding", {})

        if vector and isinstance(vector, np.ndarray):
            vector = vector.tolist()

        return PointStruct(id=_embedded_vector_id, vector=vector, payload=payload)

    def model_dump(self: BabylonVectorDocument, **kwargs) -> dict:
        """Return the dictionary representation of this model."""
        dict_ = super().model_dump(**kwargs)

        dict_ = self._uuid_to_str(dict_)  # type: ignore

        return dict_
