import abc
import uuid

import numpy as np
from pydantic import BaseModel, UUID4, Field
from typing import Any, Callable, Dict, Generic, Type, TypeVar
from qdrant_client.models import CollectionInfo, PointStruct, Record

from features.logger import get_logger
from features.vector_store.vectorstore import VectorStore

BABYLON_VECTOR_DOCUMENT = TypeVar("BABYLON_VECTOR_DOCUMENT", bound="VectorBaseDocument")

_LOGGER = get_logger()


class BabylonVectorBasedDocument(BaseModel, Generic[BABYLON_VECTOR_DOCUMENT], abc.ABC):
    _collection = "babylon_vectors"

    _id: UUID4 = Field(default_factory=uuid.uuid4)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self._id == other.id

    def __hash__(self) -> int:
        return hash(self._id)

    @classmethod
    def document_id(cls) -> UUID4:
        return cls._id

    @classmethod
    def from_record(
        cls: Type[BABYLON_VECTOR_DOCUMENT], point: Record
    ) -> BABYLON_VECTOR_DOCUMENT:
        _point_id = UUID4(point.id, version=4)
        payload = point.payload or {}

        attrs = {"id": _point_id, **payload}

        # Update internal embeddings.
        if cls._has_class_attrs("embedding"):
            attrs["embedding"] = point.vector or None

        return cls(**attrs)

    @classmethod
    def search(
        cls: Type[BABYLON_VECTOR_DOCUMENT],
        vector_store: VectorStore,
        query_vector: list,
        limit: int = 10,
        **kwargs,
    ) -> list[BABYLON_VECTOR_DOCUMENT]:
        """Execute a search query against the vector db."""
        try:
            documents = cls._search(query_vector=query_vector, limit=limit, **kwargs)
        except Exception as e:
            _LOGGER.debug(f"Error while searching documents: {e}")
            _LOGGER.info(
                f"Failed to search documents in '{cls.get_collection_name()}'."
            )
            documents = []

        return documents

    @classmethod
    def bulk_find(
        cls: Type[BABYLON_VECTOR_DOCUMENT],
        vectorstore: VectorStore,
        limit: int = 10,
        **kwargs,
    ) -> tuple[list[BABYLON_VECTOR_DOCUMENT], uuid.UUID | None]:
        """Execute a bulk find of vector documents."""
        try:
            documents, next_offset = cls._bulk_find(
                vectorstore=vectorstore, limit=limit, **kwargs
            )
        except Exception as e:
            message = f"Failed to search documents in '{cls.get_collection_name()}'."
            _LOGGER.debug(message + f"\nError: {e}")
            _LOGGER.info(message)
            documents, next_offset = [], None

        return documents, next_offset

    @classmethod
    def get_collection_name(cls) -> str:
        return cls._collection

    @classmethod
    def _bulk_find(
        cls: Type[BABYLON_VECTOR_DOCUMENT],
        vectorstore: VectorStore,
        limit: int = 10,
        **kwargs,
    ) -> tuple[list[BABYLON_VECTOR_DOCUMENT], uuid.UUID | None]:
        collection_name = cls.get_collection_name()

        offset = kwargs.pop("offset", None)
        offset = str(offset) if offset else None

        records, next_offset = vectorstore.bulk_find(
            collection_name=collection_name, offset=offset, limit=limit, **kwargs
        )

        documents = [cls.from_record(record) for record in records]

        if next_offset is not None:
            next_offset = uuid.UUID(next_offset, version=4)

        return documents, next_offset

    @classmethod
    def _search(
        cls: Type[BABYLON_VECTOR_DOCUMENT],
        vector_store: VectorStore,
        query_vector: list,
        limit: int = 10,
        with_payload: bool = True,
        with_vectors: bool = True,
        **kwargs,
    ) -> list[BABYLON_VECTOR_DOCUMENT]:
        collection_name = cls.get_collection_name()
        records: list[Record] = vector_store.search_collection(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            with_payload=with_payload,
            with_vectors=with_vectors,
            **kwargs,
        )
        return [cls.from_record(record) for record in records]

    def to_point(self: BABYLON_VECTOR_DOCUMENT, **kwargs) -> PointStruct:
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

    def model_dump(self: BABYLON_VECTOR_DOCUMENT, **kwargs) -> dict:
        """Return the dictionary representation of this model."""
        dict_ = super().model_dump(**kwargs)

        dict_ = self._uuid_to_str(dict_)

        return dict_
