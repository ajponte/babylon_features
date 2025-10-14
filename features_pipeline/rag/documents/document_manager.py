# pylint: disable=no-member
"""Service object for building a vectorized document."""

import os
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone

from typing import Any

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from features_pipeline.datalake import Datalake
from features_pipeline.error import RAGError
from features_pipeline.logger import get_logger
from features_pipeline.rag.documents.document_builder import build_langchain_document

logging.basicConfig(level="DEBUG")

_LOGGER = get_logger(__name__)

# Two minutes. Since this flag is set *only* if
# no value is present, we want it to be as small
# as possible. In a production cloud environment,
# this can be bumped up much higher.
DEFAULT_DOC_PROCESSING_TIMEOUT_SECONDS = 180


# The max number of RAG documents to store in memory
# for any given python process.
PROCESS_MAX_RAG_DOCUMENTS = 500


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

    def __add__(self, other):
        """
        Add a new langchain `Document` to the list in an instantiated `RAGCollection`.

        :param other: langchain `Document` to add.
        :return:
        """
        self._check_max_size(1)
        self.documents.append(other)
        return self

    def clear_documents(self) -> None:
        """Remove all documents from the internal collection."""
        self.documents = []

    def vectorize(self, model: str, persist_directory: str = "./chromadb") -> None:
        """
        Vectorize and persist the documents in the vectorStore.
        """
        embeddings = HuggingFaceEmbeddings(
            model=model,
            model_kwargs={"device": "cpu"},  # Use 'cuda' or 'mps' for GPU if available
            encode_kwargs={"normalize_embeddings": True},
        )
        # Initialize Chroma, specifying a collection name and persistence directory if needed
        vector_store = Chroma(
            # Todo: move to constants
            collection_name="my_document_collection",
            embedding_function=embeddings,
            persist_directory=persist_directory,
        )

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

    def __init__(self, doc_processing_timeout_seconds: int):
        """
        Constructor.

        :param doc_processing_timeout_seconds: The number of seconds which can elapse
                                               while an instance of this DocumentManager
                                               is processing documents.
        """
        self._timeout_seconds = doc_processing_timeout_seconds

    @abstractmethod
    def build_documents(self) -> None:
        """
        Builds and returns parsed documents from the data lake.
        """


class BabylonDocumentsManager(DocumentsManager):
    """Documents manager for Babylon-domain RAG documents."""

    _timeout_seconds: int = DEFAULT_DOC_PROCESSING_TIMEOUT_SECONDS

    _instance: Datalake | None = None

    _collection: str | None = None

    # The model to use for embeddings.
    _model: str | None = None

    # pylint: disable=unused-argument
    def __new__(cls, config: dict[str, Any]):
        if cls._instance is None:
            # Cache this instance.
            cls._instance = super(BabylonDocumentsManager, cls).__new__(cls)  # type: ignore
            # Cache a MongoDB API client for the datalake.
            try:
                cls._instance.datalake_client = cls.__configure_datalake(config)  # type: ignore
            except Exception as e:
                message = "Unexpected exception while instantiating MongoDB client."
                _LOGGER.exception(message, exc_info=e)
                raise RAGError(message=message, cause=e) from e

        else:
            _LOGGER.info("Instance already exists. Returning cached.")
        # Set the model
        cls._model = config["EMBEDDING_MODEL"]
        return cls._instance

    @classmethod
    def __configure_datalake(cls, config: dict) -> Datalake:
        try:
            return Datalake(
                host=config["MONGO_DB_HOST"],
                port=config["MONGO_DB_PORT"],
                username=config["MONGO_DB_USER"],
                password=config["MONGO_DB_PASSWORD"],
                connection_timeout_seconds=config["MONGO_CONNECTION_TIMEOUT_SECONDS"],
            )
        except Exception as e:
            message = "Unexpected exception while instantiating MongoDB client."
            _LOGGER.exception(message, exc_info=e)
            raise RAGError(message=message, cause=e) from e

    @property
    def data_lake(self) -> Datalake:
        """Return the instance's datalake object."""
        return self._instance.datalake_client  # type: ignore

    def build_documents(self) -> None:
        """Build Documents from the mongo data lake collections."""
        try:
            self._build_collection_documents()
        except Exception as e:
            raise RAGError(
                message="Error building vectorized documents", cause=e
            ) from e

    def _build_collection_documents(self) -> None:
        """
        Build a list of RAG documents from a mongo datalake collection.

        :return: The documents. The return type of this method is a `RAGCollection`.
        """
        _LOGGER.info(f"Fetching documents from collection {self._collection}")
        collections = self.data_lake.list_collections()

        # Set PID, start_ts, etc for current rag/python process.
        # rag_documents_collection.set_rag_process()
        rag_collection = self.__build_rag_collection()
        for datalake_collection in collections:
            _LOGGER.info(
                f"Adding new RAG document to RagCollection {rag_collection.pid}"
            )
            rag_collection.add_documents(
                self.build_documents_for_collection(datalake_collection)
            )
        _LOGGER.debug("Finished looping through all collections")
        _LOGGER.info("Persisting vectorized documents to the vector store")
        if not self._model:
            raise ValueError("No model set for this instance")
        rag_collection.vectorize(model=self._model)

    def __build_rag_collection(self) -> RagCollection:
        """
        Return a new `RagCollection` object. This method should be called when a new
        document parsing process is needed. The intention of this interface is to manage
        the start of a new document parsing process, which is compute-intensive. As such,
        The PID and start time as a UTC int is recorded in the instantiation of the object.

        :return: A new `RagCollection`.
        """

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

            _LOGGER.debug(f"Starting RAG process: {pid} at {now}")
            return RagCollection(pid=pid, _start_ts=start_ts, documents=documents)

        # Create new `RagCollection` for this python process.
        now = datetime.now().astimezone(timezone.utc)
        return set_rag_process(pid=os.getpid(), start_ts=now.timestamp(), documents=[])

    def build_documents_for_collection(
        self, datalake_collection: str
    ) -> list[Document]:
        """
        Build and return a list langchain documents, which were parsed from a MongoDB collection.

        :param datalake_collection: Collection name.
        :return: List of `langchain` ADT `Document`. Todo: Generalize `Document`.
        """
        documents = []
        _LOGGER.debug(f"Fetching documents from collection {datalake_collection}")
        db_cursor = self.datalake_client.find(  # type: ignore
            {}, collection=datalake_collection
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

    def build_document_metadata(self, source: dict) -> dict[str, str]:
        """
        Build metadata for a LangChain document.

        :param source: Data source mapping.
        :return: Metadata as a dict.
        """
        # The metadata retains useful filtering info (like the source collection/date)
        _LOGGER.info(f"Building RAG metadata for collection {self._collection}")
        metadata = {
            "source_collection": self._collection,
            "transaction_date": source.get("PostingDate"),
            "amount": source.get("Amount"),
            "type": source.get("Type"),
            # Add all other fields as metadata for advanced filtering
            **source,
        }
        return metadata
