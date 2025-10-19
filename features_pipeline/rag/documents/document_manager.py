# pylint: disable=no-member
"""Service object for building a vectorized document."""

import os
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone

from typing import Any

from langchain_core.documents import Document

from features_pipeline.datalake import Datalake
from features_pipeline.error import RAGError
from features_pipeline.logger import get_logger
from features_pipeline.rag.documents.document_builder import build_langchain_document
from features_pipeline.rag.vectorstore import ChromaVectorStore

logging.basicConfig(level="DEBUG")

_LOGGER = get_logger()

# Two minutes. Since this flag is set *only* if
# no value is present, we want it to be as small
# as possible. In a production cloud environment,
# this can be bumped up much higher.
DEFAULT_DOC_PROCESSING_TIMEOUT_SECONDS = 180


# The max number of RAG documents to store in memory
# for any given python process.
PROCESS_MAX_RAG_DOCUMENTS = 500

# The max number of datalake records for any cursor to point to.
DEFAULT_DATA_LAKE_MAX_RECORDS = 500


@dataclass
class RagCollection:
    """
    Encapsulates RAG documents for a set of collections.
    """

    # Python process ID.
    pid: int
    documents: list[Document]
    _max_size = PROCESS_MAX_RAG_DOCUMENTS
    _start_ts: float

    def add_documents(self, documents: list[Document]):
        """Add a list of documents to the current collection."""
        self._check_max_size(len(documents))
        self.documents.extend(documents)

    def _check_max_size(self, num_added: int = 0) -> None:
        """
        Check if the max size limit has been breached.

        :param num_added: The number of new documents to be added.
        :raise ValueError - If the max limit is reached.
        """
        if self.documents is None:
            raise ValueError("No documents initialized")
        if len(self.documents) + num_added >= PROCESS_MAX_RAG_DOCUMENTS:
            raise ValueError(
                f"`PROCESS_MAX_RAG_DOCUMENTS` limit reached of {PROCESS_MAX_RAG_DOCUMENTS}"
            )

    # def __add__(self, other):
    #     """
    #     Add a new langchain `Document` to the list in an instantiated `RAGCollection`.
    #
    #     :param other: langchain `Document` to add.
    #     :return:
    #     """
    #     self._check_max_size(1)
    #     self.documents.append(other)
    #     return self

    def clear_documents(self) -> None:
        """Remove all documents from the internal collection."""
        self.documents = []

    def vectorize(self, model: str, model_config: dict[str, Any]) -> None:
        """
        Vectorize and persist the documents in the vectorStore.
        """
        vector_store = ChromaVectorStore(model=model, config=model_config)

        if not self.documents:
            _LOGGER.warning(
                f"Warning: No documents found in RAGCollection for PID: {self.pid} "
                "Skipping vectorization."
            )
            return
        _LOGGER.debug(f"Vectoring documents for `RAGCollection`. PID: {self.pid}")

        vector_store.add_documents(documents=self.documents)

        _LOGGER.debug(
            f"Finished vectoring documents for `RAGCollection`. PID: {self.pid}"
        )


# pylint: disable=too-few-public-methods
class DocumentsManager(ABC):
    """Abstract parent class for Building and returning parsed documents from the data lake."""

    def __init__(self, doc_processing_timeout_seconds: int, datalake: Datalake):
        """
        Constructor.

        :param doc_processing_timeout_seconds: The number of seconds which can elapse
                                               while an instance of this DocumentManager
                                               is processing documents.
        """
        self._datalake = datalake
        self._timeout_seconds = doc_processing_timeout_seconds

    @abstractmethod
    def build_documents(self, collection: str | None = None) -> None:
        """
        Builds and returns parsed documents from the data lake.

        :param collection: Optional datalake collection to target. If no value
                           is present, the method will attempt to loop through
                           as many collections as possible.
        """


class BabylonDocumentsManager(DocumentsManager):
    """Documents manager for Babylon-domain RAG documents."""

    _instance: Datalake | None = None

    _collection: str | None = None

    # The model to use for embeddings.
    _model: str | None = None

    _datalake: Datalake | None = None

    # pylint: disable=unused-argument
    def __new__(cls, config: dict[str, Any], datalake: Datalake):
        cls._max_records: int = config.get(
            "MAX_DATA_LAKE_RECORDS", DEFAULT_DATA_LAKE_MAX_RECORDS
        )
        if cls._instance is None:
            # Cache this instance.
            cls._instance = super(BabylonDocumentsManager, cls).__new__(cls)  # type: ignore
            # Cache a MongoDB API client for the datalake.
            try:
                cls._instance.datalake = datalake  # type: ignore
            except Exception as e:
                message = "Unexpected exception while instantiating MongoDB client."
                _LOGGER.exception(message, exc_info=e)
                raise RAGError(message=message, cause=e) from e

        else:
            _LOGGER.info("Instance already exists. Returning cached.")
        # Set the model
        cls._model = config["EMBEDDING_MODEL"]
        cls._model_config = config
        return cls._instance

    @property
    def data_lake(self) -> Datalake:
        """Return the instance's datalake object."""
        return self._instance.datalake  # type: ignore

    def build_documents(self, collection: str | None = None) -> None:
        """Build Documents from the mongo data lake collections."""
        try:
            self._build_collection_documents(collection)
        except Exception as e:
            raise RAGError(
                message="Error building vectorized documents", cause=e
            ) from e

    def _build_collection_documents(self, collection: str | None = None) -> None:
        """
        Build a list of RAG documents from a mongo datalake collection.

        :param collection: Optional datalake collection to target. If no value
                           is present, the method will attempt to loop through
                           as many collections as possible.
        :return: The documents. The return type of this method is a `RAGCollection`.
        """
        _LOGGER.info(f"Fetching documents from collection {self._collection}")
        collections = [collection] if collection else self.data_lake.list_collections()

        # Set PID, start_ts, etc for current rag/python process.
        # rag_documents_collection.set_rag_process()
        rag_collection = self.__build_rag_collection()
        _LOGGER.info(f"Adding new RAG document to RagCollection {rag_collection.pid}")
        rag_collection.add_documents(
            self.build_documents_for_collection(collections[0])
        )
        _LOGGER.info("Persisting vectorized documents to the vector store")
        if not self._model:
            raise ValueError("No model set for this instance")
        rag_collection.vectorize(model=self._model, model_config=self._model_config)

    def __build_rag_collection(self) -> RagCollection:
        """
        Return a new `RagCollection` object. This method should be called when a new
        document parsing process is needed. The intention of this interface is to manage
        the start of a new document parsing process, which is compute-intensive. As such,
        The PID and start time as a UTC int is recorded in the instantiation of the object.

        :return: A new `RagCollection`.
        """

        # Create new `RagCollection` for this python process.
        now = datetime.now().astimezone(timezone.utc)
        return set_rag_process(pid=os.getpid(), start_ts=now.timestamp(), documents=[])

    def build_documents_for_collection(
        self,
        datalake_collection: str,
    ) -> list[Document]:
        """
        Build and return a list langchain documents, which were parsed from a MongoDB collection.

        :param datalake_collection: Collection name.
        :return: List of `langchain` ADT `Document`. Todo: Generalize `Document`.
        """
        documents = []
        _LOGGER.debug(f"Fetching documents from collection {datalake_collection}")
        db_cursor = get_mongo_db_cursor(
            max_records=self._max_records, collection=self._collection
        )
        for datalake_record in db_cursor:
            _LOGGER.debug(f"Looking at mongo record for cursor: {db_cursor}")
            documents.append(
                build_langchain_document(
                    source=datalake_record, collection=datalake_collection
                )
            )
        _LOGGER.info("Closing open DB Cursor")
        db_cursor.close()
        return documents


def set_rag_process(pid: int, start_ts: float, documents: list) -> RagCollection:
    """
    Set the start time and current PID for a RAG process.


    :param pid: Current python PID.
    :param start_ts: PID ts start.
    :param documents: Documents to vectorize.
    """
    if len(documents) > 0:
        raise ValueError(
            f"Documents must be empty to create a new RAGCollection: {len(documents)}"
        )

    _LOGGER.debug(f"Starting RAG process: {pid} at {start_ts}")
    return RagCollection(pid=pid, _start_ts=start_ts, documents=documents)


def __configure_datalake(config: dict) -> Datalake:
    """
    Return a configured datalake instance.

    :param config: datalake connection config.
    :return: Configured datalake instance.
    """
    try:
        return Datalake(
            host=config["MONGO_DB_HOST"],
            port=config["MONGO_DB_PORT"],
            username=config["MONGO_DB_USER"],
            password=config["MONGO_DB_PASSWORD"],
            connection_timeout_seconds=config["MONGO_CONNECTION_TIMEOUT_SECONDS"],
        )
    except Exception as e:
        message = "Unexpected exception while instantiating MongoDB client"
        _LOGGER.exception(message, exc_info=e)
        raise RAGError(message=message, cause=e) from e


def get_mongo_db_cursor(max_records: int, collection: str):
    """
    Open new cursor.
    :return: Cursor.
    """
    _LOGGER.info(f"Opening mongo cursor for {collection}")
    db_cursor = self.datalake_client.find(  # type: ignore
        {}, collection=collection
    ).limit(max_records)
    return db_cursor
